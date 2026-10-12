"""Baseline drift tracking — 사이트별 / federated 시간축 drift 추적 (2026-05-29).

federated_baseline.py는 단일 시점 multi-site distribution을 만든다.
이 모듈은 그 위에 **시간축**을 얹는다:

  1. 단일 사이트의 baseline mean이 월별로 어떻게 변하는지 (단일-site drift)
     - sensor degradation / 운영 변화 / 계절 영향 추적
     - drift_pct = (latest_month_mean - overall_mean) / overall_mean × 100
  2. 같은 env_type의 multi-site population baseline이 시간 축으로 어떻게 변하는지
     - 산업 전체 trend (계절 / 정책 영향) 추적
  3. EMA (exponential moving average) baseline — online 운영 시 사용
     - 매 sample마다 ema_value = α × new + (1-α) × old

운영 원칙:
  - advisory_only=True sample은 drift 계산에서 제외 (legal_report와 일관)
  - min_samples_per_month, min_sites_per_month 미충족 월은 산출 안 함
  - drift_alert는 advisory_only=True 기본 (자동 KOSHA 보고 안 박힘)
  - drift 임계 default ±20% — 운영자 override 가능

cross_modal_anchor와 federated_baseline의 정합:
  - federated_baseline = 한 시점 cross-site distribution
  - baseline_drift  = 시간축 가로지르는 drift trajectory
  - cross_modal_anchor = 후각 cluster + 청각 anomaly 동시성

예시:
  from modalities.integration.baseline_drift import (
      compute_site_drift_trajectory,
      compute_federated_drift,
      compute_ema_baseline,
      site_drift_alert,
  )

  # 단일 사이트 12개월 trajectory
  trajectory = compute_site_drift_trajectory(
      samples, site_id="wastewater_seoul_A",
      species="H2S", unit="ppm",
  )
  if trajectory.is_drift_significant:
      alert = site_drift_alert(trajectory)
"""
from __future__ import annotations

import math
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


BASELINE_DRIFT_VERSION = "v0.1"
DEFAULT_DRIFT_THRESHOLD_PCT = 20.0
DEFAULT_EMA_ALPHA = 0.2
MIN_SAMPLES_PER_MONTH = 5
MIN_SITES_PER_MONTH = 3


# ── Helpers ─────────────────────────────────────────────────────────


def timestamp_to_month_bucket(ts: float) -> int:
    """epoch seconds → YYYYMM integer (e.g. 1717200000 → 202606)."""
    tm = time.gmtime(float(ts))
    return tm.tm_year * 100 + tm.tm_mon


def _percentile(values: Sequence[float], p: float) -> float:
    if not values:
        return 0.0
    sorted_v = sorted(values)
    idx = max(0, min(len(sorted_v) - 1, int(p * (len(sorted_v) - 1))))
    return float(sorted_v[idx])


# ── Data classes ────────────────────────────────────────────────────


@dataclass
class MonthlyBaseline:
    """단일 month의 site-level baseline 1점."""
    month_bucket: int           # YYYYMM
    mean: float
    n_samples: int
    std: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "month_bucket": int(self.month_bucket),
            "mean": float(self.mean),
            "n_samples": int(self.n_samples),
            "std": float(self.std),
        }


@dataclass
class SiteDriftTrajectory:
    """단일 사이트의 monthly baseline trajectory."""
    site_id: str
    species: str
    unit: str
    env_type: str
    monthly_baselines: List[MonthlyBaseline] = field(default_factory=list)
    overall_mean: float = 0.0
    overall_std: float = 0.0
    n_months_tracked: int = 0
    n_samples_total: int = 0
    latest_month: Optional[int] = None
    oldest_month: Optional[int] = None
    drift_pct_latest_vs_overall: float = 0.0   # (latest - overall) / overall × 100
    drift_pct_latest_vs_oldest: float = 0.0    # (latest - oldest) / oldest × 100
    drift_direction: str = "stable"            # increasing / decreasing / stable
    is_drift_significant: bool = False
    confidence: str = "low"                    # low / medium / high

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": BASELINE_DRIFT_VERSION,
            "site_id": self.site_id,
            "species": self.species,
            "unit": self.unit,
            "env_type": self.env_type,
            "n_months_tracked": self.n_months_tracked,
            "n_samples_total": self.n_samples_total,
            "latest_month": self.latest_month,
            "oldest_month": self.oldest_month,
            "overall_mean": round(self.overall_mean, 4),
            "overall_std": round(self.overall_std, 4),
            "drift_pct_latest_vs_overall": round(self.drift_pct_latest_vs_overall, 2),
            "drift_pct_latest_vs_oldest": round(self.drift_pct_latest_vs_oldest, 2),
            "drift_direction": self.drift_direction,
            "is_drift_significant": self.is_drift_significant,
            "confidence": self.confidence,
            "monthly_baselines": [m.to_dict() for m in self.monthly_baselines],
        }


@dataclass
class FederatedMonthlyBaseline:
    """단일 month의 population (multi-site) baseline."""
    month_bucket: int
    population_mean: float        # cross-site mean of site-means
    n_sites: int
    n_samples: int
    std_across_sites: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "month_bucket": int(self.month_bucket),
            "population_mean": float(self.population_mean),
            "n_sites": int(self.n_sites),
            "n_samples": int(self.n_samples),
            "std_across_sites": float(self.std_across_sites),
        }


@dataclass
class FederatedDriftReport:
    """env_type 의 multi-site population drift over time."""
    env_type: str
    species: str
    unit: str
    monthly_population_baselines: List[FederatedMonthlyBaseline] = field(default_factory=list)
    n_months_tracked: int = 0
    oldest_month: Optional[int] = None
    latest_month: Optional[int] = None
    drift_pct_latest_vs_oldest: float = 0.0
    drift_direction: str = "stable"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": BASELINE_DRIFT_VERSION,
            "env_type": self.env_type,
            "species": self.species,
            "unit": self.unit,
            "n_months_tracked": self.n_months_tracked,
            "oldest_month": self.oldest_month,
            "latest_month": self.latest_month,
            "drift_pct_latest_vs_oldest": round(self.drift_pct_latest_vs_oldest, 2),
            "drift_direction": self.drift_direction,
            "monthly_population_baselines": [
                m.to_dict() for m in self.monthly_population_baselines
            ],
        }


# ── Core: single-site drift trajectory ──────────────────────────────


def compute_site_drift_trajectory(
    samples: Iterable[Mapping[str, Any]],
    *,
    site_id: str,
    species: str,
    unit: str = "ppm",
    env_type: str = "",
    min_samples_per_month: int = MIN_SAMPLES_PER_MONTH,
    drift_threshold_pct: float = DEFAULT_DRIFT_THRESHOLD_PCT,
) -> SiteDriftTrajectory:
    """단일 사이트의 monthly baseline trajectory.

    samples = [{site_id, species, value, unit, timestamp, advisory_only, weight, env_type}, ...]

    advisory_only=True 자동 제외.
    min_samples_per_month 미만 월은 산출 안 함.

    drift_direction:
      - latest_vs_overall > +threshold_pct → "increasing"
      - latest_vs_overall < -threshold_pct → "decreasing"
      - 그 외 → "stable"

    confidence:
      - n_months >= 6 → "high"
      - n_months >= 3 → "medium"
      - 그 외 → "low"
    """
    species_u = str(species).upper()
    unit_l = str(unit).lower()

    # Per-month grouping: month → list[(value, weight)]
    by_month: Dict[int, List[Tuple[float, float]]] = defaultdict(list)
    detected_env_type = env_type

    for s in samples:
        if not isinstance(s, Mapping):
            continue
        if bool(s.get("advisory_only", False)):
            continue
        if str(s.get("site_id") or "") != site_id:
            continue
        if str(s.get("species", "")).upper() != species_u:
            continue
        if str(s.get("unit", "ppm")).lower() != unit_l:
            continue
        try:
            v = float(s.get("value", 0.0))
        except (TypeError, ValueError):
            continue
        if math.isnan(v) or math.isinf(v):
            continue
        try:
            ts = float(s.get("timestamp", 0.0))
        except (TypeError, ValueError):
            continue
        if ts <= 0.0:
            continue
        try:
            w = float(s.get("weight", 1.0))
        except (TypeError, ValueError):
            w = 1.0
        if w <= 0.0:
            continue

        if not detected_env_type:
            detected_env_type = str(s.get("env_type", ""))

        month = timestamp_to_month_bucket(ts)
        by_month[month].append((v, w))

    # Build monthly baselines (sufficient samples)
    monthly_baselines: List[MonthlyBaseline] = []
    all_values_flat: List[float] = []

    for month in sorted(by_month.keys()):
        readings = by_month[month]
        if len(readings) < min_samples_per_month:
            continue
        total_w = sum(w for _, w in readings)
        if total_w <= 0.0:
            continue
        weighted_mean = sum(v * w for v, w in readings) / total_w
        values = [v for v, _ in readings]
        std = float(statistics.pstdev(values)) if len(values) > 1 else 0.0
        monthly_baselines.append(MonthlyBaseline(
            month_bucket=month,
            mean=float(weighted_mean),
            n_samples=len(readings),
            std=std,
        ))
        all_values_flat.extend(values)

    trajectory = SiteDriftTrajectory(
        site_id=site_id,
        species=species_u,
        unit=unit_l,
        env_type=detected_env_type,
    )

    if not monthly_baselines:
        return trajectory

    # Compute overall + drift
    trajectory.monthly_baselines = monthly_baselines
    trajectory.n_months_tracked = len(monthly_baselines)
    trajectory.n_samples_total = sum(m.n_samples for m in monthly_baselines)
    trajectory.latest_month = monthly_baselines[-1].month_bucket
    trajectory.oldest_month = monthly_baselines[0].month_bucket
    trajectory.overall_mean = float(statistics.fmean(all_values_flat))
    trajectory.overall_std = (
        float(statistics.pstdev(all_values_flat)) if len(all_values_flat) > 1 else 0.0
    )

    latest_mean = monthly_baselines[-1].mean
    oldest_mean = monthly_baselines[0].mean

    if abs(trajectory.overall_mean) > 1e-9:
        trajectory.drift_pct_latest_vs_overall = (
            (latest_mean - trajectory.overall_mean) / trajectory.overall_mean * 100.0
        )
    if abs(oldest_mean) > 1e-9 and len(monthly_baselines) >= 2:
        trajectory.drift_pct_latest_vs_oldest = (
            (latest_mean - oldest_mean) / oldest_mean * 100.0
        )

    if trajectory.drift_pct_latest_vs_overall > drift_threshold_pct:
        trajectory.drift_direction = "increasing"
        trajectory.is_drift_significant = True
    elif trajectory.drift_pct_latest_vs_overall < -drift_threshold_pct:
        trajectory.drift_direction = "decreasing"
        trajectory.is_drift_significant = True
    else:
        trajectory.drift_direction = "stable"
        trajectory.is_drift_significant = False

    if trajectory.n_months_tracked >= 6:
        trajectory.confidence = "high"
    elif trajectory.n_months_tracked >= 3:
        trajectory.confidence = "medium"
    else:
        trajectory.confidence = "low"

    return trajectory


# ── Core: federated (multi-site) drift over time ────────────────────


def compute_federated_drift(
    samples: Iterable[Mapping[str, Any]],
    *,
    env_type: str,
    species: str,
    unit: str = "ppm",
    min_sites_per_month: int = MIN_SITES_PER_MONTH,
    min_samples_per_site_per_month: int = MIN_SAMPLES_PER_MONTH,
    drift_threshold_pct: float = DEFAULT_DRIFT_THRESHOLD_PCT,
) -> FederatedDriftReport:
    """같은 env_type / species / unit 의 cross-site population baseline trajectory."""
    species_u = str(species).upper()
    unit_l = str(unit).lower()

    # month → site → list[(value, weight)]
    by_month_site: Dict[int, Dict[str, List[Tuple[float, float]]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for s in samples:
        if not isinstance(s, Mapping):
            continue
        if bool(s.get("advisory_only", False)):
            continue
        if str(s.get("env_type", "")) != env_type:
            continue
        if str(s.get("species", "")).upper() != species_u:
            continue
        if str(s.get("unit", "ppm")).lower() != unit_l:
            continue
        try:
            v = float(s.get("value", 0.0))
        except (TypeError, ValueError):
            continue
        if math.isnan(v) or math.isinf(v):
            continue
        try:
            ts = float(s.get("timestamp", 0.0))
        except (TypeError, ValueError):
            continue
        if ts <= 0.0:
            continue
        site = str(s.get("site_id") or "")
        if not site:
            continue
        try:
            w = float(s.get("weight", 1.0))
        except (TypeError, ValueError):
            w = 1.0
        if w <= 0.0:
            continue

        month = timestamp_to_month_bucket(ts)
        by_month_site[month][site].append((v, w))

    monthly_population: List[FederatedMonthlyBaseline] = []
    for month in sorted(by_month_site.keys()):
        site_means: List[float] = []
        n_samples_total = 0
        for site, readings in by_month_site[month].items():
            if len(readings) < min_samples_per_site_per_month:
                continue
            total_w = sum(w for _, w in readings)
            if total_w <= 0.0:
                continue
            site_mean = sum(v * w for v, w in readings) / total_w
            site_means.append(site_mean)
            n_samples_total += len(readings)

        if len(site_means) < min_sites_per_month:
            continue

        monthly_population.append(FederatedMonthlyBaseline(
            month_bucket=month,
            population_mean=float(statistics.fmean(site_means)),
            n_sites=len(site_means),
            n_samples=n_samples_total,
            std_across_sites=(
                float(statistics.pstdev(site_means)) if len(site_means) > 1 else 0.0
            ),
        ))

    report = FederatedDriftReport(
        env_type=env_type,
        species=species_u,
        unit=unit_l,
        monthly_population_baselines=monthly_population,
        n_months_tracked=len(monthly_population),
    )

    if not monthly_population:
        return report

    report.oldest_month = monthly_population[0].month_bucket
    report.latest_month = monthly_population[-1].month_bucket
    oldest_mean = monthly_population[0].population_mean
    latest_mean = monthly_population[-1].population_mean

    if abs(oldest_mean) > 1e-9 and len(monthly_population) >= 2:
        report.drift_pct_latest_vs_oldest = (
            (latest_mean - oldest_mean) / oldest_mean * 100.0
        )

    if report.drift_pct_latest_vs_oldest > drift_threshold_pct:
        report.drift_direction = "increasing"
    elif report.drift_pct_latest_vs_oldest < -drift_threshold_pct:
        report.drift_direction = "decreasing"
    else:
        report.drift_direction = "stable"

    return report


# ── EMA baseline (online running estimate) ──────────────────────────


@dataclass
class EMABaseline:
    """단일 사이트의 online EMA baseline."""
    site_id: str
    species: str
    unit: str
    alpha: float
    ema_value: float = 0.0
    n_samples_seen: int = 0

    def update(self, value: float, *, weight: float = 1.0) -> float:
        """새 sample 흡수. Returns new ema_value."""
        if not (0.0 < self.alpha <= 1.0):
            raise ValueError(f"alpha must be in (0, 1], got {self.alpha}")
        if weight <= 0.0:
            return self.ema_value
        if self.n_samples_seen == 0:
            self.ema_value = float(value)
        else:
            effective_alpha = min(1.0, self.alpha * weight)
            self.ema_value = (
                effective_alpha * float(value)
                + (1.0 - effective_alpha) * self.ema_value
            )
        self.n_samples_seen += 1
        return self.ema_value


def compute_ema_baseline(
    samples: Iterable[Mapping[str, Any]],
    *,
    site_id: str,
    species: str,
    unit: str = "ppm",
    alpha: float = DEFAULT_EMA_ALPHA,
) -> EMABaseline:
    """sample stream (timestamp 순) → EMA baseline.

    advisory_only=True 자동 제외.
    """
    species_u = str(species).upper()
    unit_l = str(unit).lower()
    ema = EMABaseline(
        site_id=site_id, species=species_u, unit=unit_l, alpha=alpha,
    )
    filtered: List[Tuple[float, float, float]] = []
    for s in samples:
        if not isinstance(s, Mapping):
            continue
        if bool(s.get("advisory_only", False)):
            continue
        if str(s.get("site_id") or "") != site_id:
            continue
        if str(s.get("species", "")).upper() != species_u:
            continue
        if str(s.get("unit", "ppm")).lower() != unit_l:
            continue
        try:
            v = float(s.get("value", 0.0))
        except (TypeError, ValueError):
            continue
        if math.isnan(v) or math.isinf(v):
            continue
        try:
            ts = float(s.get("timestamp", 0.0))
        except (TypeError, ValueError):
            continue
        if ts <= 0.0:
            continue
        try:
            w = float(s.get("weight", 1.0))
        except (TypeError, ValueError):
            w = 1.0
        if w <= 0.0:
            continue
        filtered.append((ts, v, w))

    filtered.sort(key=lambda x: x[0])
    for _, v, w in filtered:
        ema.update(v, weight=w)
    return ema


# ── Drift alert (advisory) ──────────────────────────────────────────


def site_drift_alert(
    trajectory: SiteDriftTrajectory,
    *,
    advisory_only: bool = True,
) -> Optional[Dict[str, Any]]:
    """drift_significant → advisory alert payload.

    HAL legal_report 차단 (advisory_only=True default).
    significant 아니면 None 반환.
    """
    if not trajectory.is_drift_significant:
        return None
    if trajectory.confidence == "low":
        # 1~2개월만으론 alert 발송 안 함 (false positive 방지)
        return None

    return {
        "version": BASELINE_DRIFT_VERSION,
        "alert_type": "baseline_drift",
        "site_id": trajectory.site_id,
        "species": trajectory.species,
        "unit": trajectory.unit,
        "env_type": trajectory.env_type,
        "drift_pct_latest_vs_overall": round(trajectory.drift_pct_latest_vs_overall, 2),
        "drift_direction": trajectory.drift_direction,
        "n_months_tracked": trajectory.n_months_tracked,
        "confidence": trajectory.confidence,
        "advisory_only": bool(advisory_only),
        "latest_month": trajectory.latest_month,
        "overall_mean": round(trajectory.overall_mean, 4),
        "latest_month_mean": round(trajectory.monthly_baselines[-1].mean, 4),
        "recommended_action": (
            "sensor_recalibration_check" if trajectory.confidence == "high"
            else "monitor_2_more_months"
        ),
    }


__all__ = [
    "BASELINE_DRIFT_VERSION",
    "DEFAULT_DRIFT_THRESHOLD_PCT",
    "DEFAULT_EMA_ALPHA",
    "MIN_SAMPLES_PER_MONTH",
    "MIN_SITES_PER_MONTH",
    "timestamp_to_month_bucket",
    "MonthlyBaseline",
    "SiteDriftTrajectory",
    "FederatedMonthlyBaseline",
    "FederatedDriftReport",
    "EMABaseline",
    "compute_site_drift_trajectory",
    "compute_federated_drift",
    "compute_ema_baseline",
    "site_drift_alert",
]
