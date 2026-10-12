"""Baseline drift tests — site / federated monthly trajectory + EMA + alert.

검증 항목:
  - timestamp_to_month_bucket: epoch → YYYYMM 변환
  - compute_site_drift_trajectory:
      • advisory_only / site/species/unit 필터
      • min_samples_per_month 미만 월 skip
      • drift_pct_latest_vs_overall / drift_pct_latest_vs_oldest
      • drift_direction (increasing/decreasing/stable)
      • confidence (low/medium/high)
  - compute_federated_drift: env_type/species/unit cross-site monthly population
  - compute_ema_baseline + EMABaseline.update
  - site_drift_alert: low confidence → None / significant → payload + advisory_only=True 강제
"""
from __future__ import annotations

import time

import pytest

from baseline_drift import (
    BASELINE_DRIFT_VERSION,
    EMABaseline,
    FederatedDriftReport,
    SiteDriftTrajectory,
    compute_ema_baseline,
    compute_federated_drift,
    compute_site_drift_trajectory,
    site_drift_alert,
    timestamp_to_month_bucket,
)


def _ts_for(year: int, month: int, day: int = 15) -> float:
    """년/월/일 → epoch seconds (UTC)."""
    return float(time.mktime(time.gmtime(0)) + 0) + float(
        # use calendar.timegm-like via time.mktime with gmtime offset
        # simpler: compute directly via time.mktime with utc tuple
        0
    ) or time.mktime((year, month, day, 12, 0, 0, 0, 0, 0))


def _ts(year: int, month: int, day: int = 15, hour: int = 12) -> float:
    """년/월/일/시 → epoch seconds (UTC, calendar.timegm)."""
    import calendar
    return float(calendar.timegm((year, month, day, hour, 0, 0, 0, 0, 0)))


# ── timestamp_to_month_bucket ───────────────────────────────────────


def test_timestamp_to_month_bucket():
    ts = _ts(2026, 5, 15)
    assert timestamp_to_month_bucket(ts) == 202605
    ts2 = _ts(2026, 12, 1)
    assert timestamp_to_month_bucket(ts2) == 202612


# ── compute_site_drift_trajectory ───────────────────────────────────


def _make_site_samples(
    site_id, species, unit, values_by_month, *, env_type="wastewater"
):
    """{month: [v1, v2, ...]} → sample list."""
    samples = []
    for month, values in values_by_month.items():
        for v in values:
            samples.append({
                "site_id": site_id,
                "species": species,
                "unit": unit,
                "env_type": env_type,
                "value": v,
                "timestamp": _ts(2026, month, 15),
                "weight": 1.0,
                "advisory_only": False,
            })
    return samples


def test_site_trajectory_basic_3_months():
    samples = _make_site_samples(
        "site_a", "H2S", "ppm",
        {1: [1.0] * 10, 2: [1.5] * 10, 3: [2.0] * 10},
    )
    traj = compute_site_drift_trajectory(
        samples, site_id="site_a", species="H2S", unit="ppm",
    )
    assert traj.n_months_tracked == 3
    assert traj.n_samples_total == 30
    assert traj.oldest_month == 202601
    assert traj.latest_month == 202603
    assert traj.confidence == "medium"  # 3 months
    # latest=2.0, oldest=1.0 → +100%
    assert traj.drift_pct_latest_vs_oldest == pytest.approx(100.0, abs=0.5)
    # overall mean = 1.5, latest=2.0 → +33%
    assert traj.drift_pct_latest_vs_overall == pytest.approx(33.33, abs=0.5)
    assert traj.drift_direction == "increasing"
    assert traj.is_drift_significant is True


def test_site_trajectory_stable():
    samples = _make_site_samples(
        "site_a", "H2S", "ppm",
        {1: [1.0] * 10, 2: [1.05] * 10, 3: [0.98] * 10},
    )
    traj = compute_site_drift_trajectory(
        samples, site_id="site_a", species="H2S", unit="ppm",
    )
    assert traj.drift_direction == "stable"
    assert traj.is_drift_significant is False


def test_site_trajectory_decreasing():
    samples = _make_site_samples(
        "site_a", "H2S", "ppm",
        {1: [2.0] * 10, 2: [1.5] * 10, 3: [1.0] * 10},
    )
    traj = compute_site_drift_trajectory(
        samples, site_id="site_a", species="H2S", unit="ppm",
    )
    assert traj.drift_direction == "decreasing"
    assert traj.drift_pct_latest_vs_oldest == pytest.approx(-50.0, abs=0.5)
    assert traj.is_drift_significant is True


def test_site_trajectory_filters_advisory_only():
    samples = _make_site_samples(
        "site_a", "H2S", "ppm", {1: [1.0] * 10, 2: [2.0] * 10},
    )
    # advisory_only sample 추가
    samples.append({
        "site_id": "site_a", "species": "H2S", "unit": "ppm",
        "value": 999.0, "timestamp": _ts(2026, 3, 15),
        "weight": 1.0, "advisory_only": True,
    })
    traj = compute_site_drift_trajectory(
        samples, site_id="site_a", species="H2S", unit="ppm",
    )
    assert traj.n_months_tracked == 2  # advisory month 제외
    assert traj.latest_month == 202602


def test_site_trajectory_filters_other_sites():
    samples = _make_site_samples("site_a", "H2S", "ppm", {1: [1.0] * 10})
    samples.extend(_make_site_samples("site_b", "H2S", "ppm", {1: [99.0] * 10}))
    traj = compute_site_drift_trajectory(
        samples, site_id="site_a", species="H2S", unit="ppm",
    )
    assert traj.monthly_baselines[0].mean == pytest.approx(1.0, abs=0.01)


def test_site_trajectory_filters_other_species():
    samples = _make_site_samples("site_a", "H2S", "ppm", {1: [1.0] * 10})
    samples.extend(_make_site_samples("site_a", "NH3", "ppm", {1: [99.0] * 10}))
    traj = compute_site_drift_trajectory(
        samples, site_id="site_a", species="H2S", unit="ppm",
    )
    assert traj.monthly_baselines[0].mean == pytest.approx(1.0, abs=0.01)


def test_site_trajectory_skips_low_sample_months():
    """min_samples_per_month 미만 월 → skip."""
    samples = _make_site_samples(
        "site_a", "H2S", "ppm",
        {1: [1.0] * 10, 2: [1.5] * 2, 3: [2.0] * 10},   # month 2 low
    )
    traj = compute_site_drift_trajectory(
        samples, site_id="site_a", species="H2S", unit="ppm",
        min_samples_per_month=5,
    )
    assert traj.n_months_tracked == 2   # 1 + 3
    months = [m.month_bucket for m in traj.monthly_baselines]
    assert 202602 not in months


def test_site_trajectory_high_confidence_6_months():
    samples = _make_site_samples(
        "site_a", "H2S", "ppm",
        {m: [1.0 + m * 0.1] * 10 for m in range(1, 7)},
    )
    traj = compute_site_drift_trajectory(
        samples, site_id="site_a", species="H2S", unit="ppm",
    )
    assert traj.n_months_tracked == 6
    assert traj.confidence == "high"


def test_site_trajectory_empty():
    traj = compute_site_drift_trajectory(
        [], site_id="site_a", species="H2S", unit="ppm",
    )
    assert traj.n_months_tracked == 0
    assert traj.is_drift_significant is False
    assert traj.confidence == "low"


def test_site_trajectory_to_dict():
    samples = _make_site_samples("site_a", "H2S", "ppm", {1: [1.0] * 10, 2: [1.5] * 10})
    traj = compute_site_drift_trajectory(
        samples, site_id="site_a", species="H2S", unit="ppm",
    )
    d = traj.to_dict()
    assert d["version"] == BASELINE_DRIFT_VERSION
    assert d["site_id"] == "site_a"
    assert d["n_months_tracked"] == 2
    assert len(d["monthly_baselines"]) == 2


# ── compute_federated_drift ─────────────────────────────────────────


def test_federated_drift_basic():
    """5 사이트가 같은 env_type/species 에서 월별 increasing pattern."""
    samples = []
    for site_idx in range(5):
        site = f"site_{site_idx}"
        for month in (1, 2, 3):
            base = 1.0 + (month - 1) * 0.5  # 1.0, 1.5, 2.0
            for v in [base + 0.05 * site_idx] * 10:
                samples.append({
                    "site_id": site,
                    "env_type": "wastewater",
                    "species": "H2S",
                    "unit": "ppm",
                    "value": v,
                    "timestamp": _ts(2026, month, 15),
                    "weight": 1.0,
                })

    report = compute_federated_drift(
        samples,
        env_type="wastewater", species="H2S", unit="ppm",
        min_sites_per_month=3,
    )
    assert report.n_months_tracked == 3
    assert all(m.n_sites == 5 for m in report.monthly_population_baselines)
    assert report.drift_direction == "increasing"
    # population means: month1=1.10, month2=1.60, month3=2.10 → (2.10-1.10)/1.10×100 ≈ 90.9%
    assert report.drift_pct_latest_vs_oldest == pytest.approx(90.9, abs=1.0)


def test_federated_drift_filters_advisory():
    samples = []
    for site_idx in range(5):
        for month in (1, 2):
            for _ in range(10):
                samples.append({
                    "site_id": f"site_{site_idx}",
                    "env_type": "wastewater",
                    "species": "H2S",
                    "unit": "ppm",
                    "value": 1.0,
                    "timestamp": _ts(2026, month, 15),
                    "advisory_only": True,   # all advisory
                })
    report = compute_federated_drift(
        samples,
        env_type="wastewater", species="H2S", unit="ppm",
    )
    assert report.n_months_tracked == 0


def test_federated_drift_min_sites_enforced():
    """min_sites_per_month 미만 월 → skip."""
    samples = []
    # month 1: 5 sites, month 2: 2 sites only → month 2 skipped
    for site_idx in range(5):
        for _ in range(10):
            samples.append({
                "site_id": f"site_{site_idx}",
                "env_type": "wastewater", "species": "H2S", "unit": "ppm",
                "value": 1.0, "timestamp": _ts(2026, 1, 15),
            })
    for site_idx in range(2):
        for _ in range(10):
            samples.append({
                "site_id": f"site_{site_idx}",
                "env_type": "wastewater", "species": "H2S", "unit": "ppm",
                "value": 2.0, "timestamp": _ts(2026, 2, 15),
            })
    report = compute_federated_drift(
        samples,
        env_type="wastewater", species="H2S", unit="ppm",
        min_sites_per_month=3,
    )
    assert report.n_months_tracked == 1
    assert report.monthly_population_baselines[0].month_bucket == 202601


def test_federated_drift_filters_other_env_type():
    samples = []
    for site_idx in range(5):
        for _ in range(10):
            samples.append({
                "site_id": f"site_{site_idx}",
                "env_type": "wastewater", "species": "H2S", "unit": "ppm",
                "value": 1.0, "timestamp": _ts(2026, 1, 15),
            })
            samples.append({
                "site_id": f"site_{site_idx}",
                "env_type": "fab", "species": "H2S", "unit": "ppm",
                "value": 99.0, "timestamp": _ts(2026, 1, 15),
            })
    report = compute_federated_drift(
        samples,
        env_type="wastewater", species="H2S", unit="ppm",
    )
    assert report.monthly_population_baselines[0].population_mean == pytest.approx(1.0, abs=0.01)


def test_federated_drift_empty():
    report = compute_federated_drift(
        [], env_type="wastewater", species="H2S", unit="ppm",
    )
    assert report.n_months_tracked == 0
    assert report.drift_direction == "stable"


def test_federated_drift_to_dict():
    samples = []
    for site_idx in range(3):
        for month in (1, 2):
            for v in [1.0 + month * 0.5] * 10:
                samples.append({
                    "site_id": f"s{site_idx}",
                    "env_type": "wastewater", "species": "H2S", "unit": "ppm",
                    "value": v, "timestamp": _ts(2026, month, 15),
                })
    report = compute_federated_drift(
        samples, env_type="wastewater", species="H2S", unit="ppm",
        min_sites_per_month=3,
    )
    d = report.to_dict()
    assert d["version"] == BASELINE_DRIFT_VERSION
    assert d["env_type"] == "wastewater"
    assert "monthly_population_baselines" in d


# ── EMA baseline ────────────────────────────────────────────────────


def test_ema_baseline_first_sample_becomes_init():
    ema = EMABaseline(site_id="s", species="H2S", unit="ppm", alpha=0.2)
    ema.update(5.0)
    assert ema.ema_value == 5.0
    assert ema.n_samples_seen == 1


def test_ema_baseline_decay():
    """α=0.5 → 새 sample이 절반 영향."""
    ema = EMABaseline(site_id="s", species="H2S", unit="ppm", alpha=0.5)
    ema.update(0.0)   # init = 0
    ema.update(10.0)  # 0.5 * 10 + 0.5 * 0 = 5
    assert ema.ema_value == pytest.approx(5.0, abs=0.01)
    ema.update(10.0)  # 0.5 * 10 + 0.5 * 5 = 7.5
    assert ema.ema_value == pytest.approx(7.5, abs=0.01)


def test_ema_baseline_invalid_alpha():
    ema = EMABaseline(site_id="s", species="H2S", unit="ppm", alpha=0.0)
    with pytest.raises(ValueError):
        ema.update(1.0)


def test_ema_baseline_ignores_zero_weight():
    ema = EMABaseline(site_id="s", species="H2S", unit="ppm", alpha=0.5)
    ema.update(5.0)
    pre = ema.ema_value
    ema.update(100.0, weight=0.0)
    assert ema.ema_value == pre


def test_compute_ema_baseline_from_stream():
    samples = []
    for month, v in [(1, 1.0), (2, 2.0), (3, 3.0)]:
        samples.append({
            "site_id": "s", "species": "H2S", "unit": "ppm",
            "value": v, "timestamp": _ts(2026, month, 15),
        })
    ema = compute_ema_baseline(
        samples, site_id="s", species="H2S", unit="ppm", alpha=0.5,
    )
    # init=1, next: 0.5*2+0.5*1=1.5, next: 0.5*3+0.5*1.5=2.25
    assert ema.ema_value == pytest.approx(2.25, abs=0.01)
    assert ema.n_samples_seen == 3


def test_compute_ema_baseline_sorts_by_timestamp():
    """timestamp 순으로 자동 정렬되어 흡수."""
    samples = [
        {"site_id": "s", "species": "H2S", "unit": "ppm",
         "value": 3.0, "timestamp": _ts(2026, 3, 15)},
        {"site_id": "s", "species": "H2S", "unit": "ppm",
         "value": 1.0, "timestamp": _ts(2026, 1, 15)},
        {"site_id": "s", "species": "H2S", "unit": "ppm",
         "value": 2.0, "timestamp": _ts(2026, 2, 15)},
    ]
    ema = compute_ema_baseline(
        samples, site_id="s", species="H2S", unit="ppm", alpha=0.5,
    )
    # 정렬 후: 1.0 → 2.0 → 3.0 → 동일한 결과
    assert ema.ema_value == pytest.approx(2.25, abs=0.01)


# ── site_drift_alert ────────────────────────────────────────────────


def test_alert_none_when_not_significant():
    traj = SiteDriftTrajectory(site_id="s", species="H2S", unit="ppm", env_type="wastewater")
    traj.is_drift_significant = False
    assert site_drift_alert(traj) is None


def test_alert_none_when_low_confidence():
    """low confidence (≤2 months) → alert 발송 안 함 (false positive 방지)."""
    samples = _make_site_samples("s", "H2S", "ppm", {1: [1.0] * 10, 2: [10.0] * 10})
    traj = compute_site_drift_trajectory(samples, site_id="s", species="H2S", unit="ppm")
    # 2 months → confidence=low
    assert traj.confidence == "low"
    assert site_drift_alert(traj) is None


def test_alert_significant_drift_payload():
    samples = _make_site_samples(
        "site_x", "H2S", "ppm",
        {m: [1.0 + m * 0.3] * 10 for m in range(1, 7)},
    )
    traj = compute_site_drift_trajectory(samples, site_id="site_x", species="H2S", unit="ppm")
    assert traj.confidence == "high"
    assert traj.is_drift_significant is True

    alert = site_drift_alert(traj)
    assert alert is not None
    assert alert["alert_type"] == "baseline_drift"
    assert alert["site_id"] == "site_x"
    assert alert["species"] == "H2S"
    assert alert["advisory_only"] is True   # HAL legal_report 차단
    assert alert["recommended_action"] == "sensor_recalibration_check"


def test_alert_medium_confidence_recommends_monitor():
    samples = _make_site_samples(
        "site_x", "H2S", "ppm",
        {1: [1.0] * 10, 2: [1.5] * 10, 3: [2.0] * 10},
    )
    traj = compute_site_drift_trajectory(samples, site_id="site_x", species="H2S", unit="ppm")
    assert traj.confidence == "medium"

    alert = site_drift_alert(traj)
    assert alert is not None
    assert alert["recommended_action"] == "monitor_2_more_months"


def test_alert_advisory_only_explicit_false():
    """advisory_only=False 명시 시 그대로 박힘 (운영자 명시 권한)."""
    samples = _make_site_samples(
        "site_x", "H2S", "ppm",
        {m: [1.0 + m * 0.3] * 10 for m in range(1, 7)},
    )
    traj = compute_site_drift_trajectory(samples, site_id="site_x", species="H2S", unit="ppm")
    alert = site_drift_alert(traj, advisory_only=False)
    assert alert is not None
    assert alert["advisory_only"] is False
