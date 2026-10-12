"""학습/시험 분리: 같은 사람이 양쪽에 들어가지 않는지, 중복을 찾는지."""
import csv
import json
import os

from split_check import find_duplicates, make_test_split, read_labels, shingles, text_sha


def _corp(tmp_path, n=60, reps=2):
    d = tmp_path / "all"; d.mkdir()
    rows = []
    for i in range(n):
        for k in range(reps if i % 3 == 0 else 1):        # 일부는 여러 번 등장
            pid = f"p{i:03d}_{k}"
            (d / pid).mkdir()
            (d / pid / "transcript.txt").write_text(
                f"## 머리말\n참가자: 사람 {i} 의 고유한 이야기입니다 " * 6 + f"\n참가자: 끝 {i}\n", encoding="utf-8")
            rows.append({"participant_id": pid, "user_id": f"u{i:03d}",
                         "sex": "female" if i % 2 == 0 else "male", "role": "a" if i % 4 < 2 else "b"})
    with open(d / "labels.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    return str(d), rows


def test_test_split_never_reuses_a_dev_person(tmp_path):
    alld, rows = _corp(tmp_path, n=60)
    dev = tmp_path / "dev"; dev.mkdir()
    dev_rows = rows[:40]
    with open(dev / "labels.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(rows[0].keys())); w.writeheader(); w.writerows(dev_rows)
    out = str(tmp_path / "test")
    s = make_test_split(alld, str(dev), out, "participant_id", "user_id", ["sex", "role"], per_cell=5, seed=1)
    assert s["overlap_with_dev"] == []                       # 핵심: dev 사람은 한 명도 없다
    dev_users = {r["user_id"] for r in dev_rows}
    test_users = {r["user_id"] for r in read_labels(out)}
    assert not (dev_users & test_users)
    assert len(test_users) == s["n_test_rows"]               # 시험 안에서도 한 사람당 한 행
    assert os.path.exists(os.path.join(out, read_labels(out)[0]["participant_id"], "transcript.txt"))


def test_duplicate_detection_finds_exact_and_near(tmp_path):
    d = tmp_path / "all"; d.mkdir()
    # 5-그램이 충분히 나오도록 긴 글로 만든다(짧은 글은 탐지기가 아예 보지 않는다 — 최소 20개)
    base = "참가자: " + " ".join(f"문장{i} 저는 대구에서 자랐고 데이터 분석가로 일하며 주말에는 책을 읽습니다" for i in range(8))
    texts = {"a": base, "b": base, "c": base + " 가끔은 영화도 보고 산책도 합니다",
             "d": "참가자: " + " ".join(f"완전히 다른 이야기{i} 입니다 여기에는 겹치는 표현이 없습니다" for i in range(8))}
    rows = []
    for pid, t in texts.items():
        (d / pid).mkdir(); (d / pid / "transcript.txt").write_text(t + "\n", encoding="utf-8")
        rows.append({"participant_id": pid, "user_id": pid})
    with open(d / "labels.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ["participant_id", "user_id"]); w.writeheader(); w.writerows(rows)
    dup = find_duplicates(str(d), rows, "participant_id", "user_id")
    assert dup["n_exact_duplicate_groups"] == 1
    assert set(list(dup["exact_duplicate_texts"].values())[0]) == {"a", "b"}
    pairs = {frozenset(p[:2]) for p in dup["near_duplicate_pairs"]}
    assert frozenset({"a", "c"}) in pairs or frozenset({"b", "c"}) in pairs      # 거의 같은 글도 잡는다
    assert all("d" not in p for p in pairs)


def test_text_sha_ignores_speaker_prefix_and_header(tmp_path):
    a = "## 머리말 다름\n참가자: 같은 내용입니다 정말로\n"
    b = "## 아주 다른 머리말\n[T01] 참가자: 같은 내용입니다 정말로\n"
    assert text_sha(a) == text_sha(b)
    assert len(shingles("참가자: " + "말 " * 20)) > 0


def test_cluster_counts_are_reported(tmp_path):
    alld, rows = _corp(tmp_path, n=30, reps=3)
    dup = find_duplicates(alld, rows, "participant_id", "user_id", near=False)
    assert dup["max_rows_per_cluster"] == 3 and dup["clusters_with_multiple_rows"] == 10


def test_extra_unique_prevents_partner_pairs(tmp_path):
    """PFG 처럼 한 대화에 두 사람이 있고 전사록이 같은 본문이면, 짝꿍이 함께 뽑히면 안 된다."""
    d = tmp_path / "all"; d.mkdir()
    rows = []
    for g in range(20):
        for role in ("a", "b"):
            pid = f"d{g:02d}{role}"
            (d / pid).mkdir(); (d / pid / "transcript.txt").write_text(f"참가자: 대화 {g} 본문\n", encoding="utf-8")
            rows.append({"participant_id": pid, "user_id": f"u{g:02d}{role}", "dialogue_id": f"d{g:02d}",
                         "sex": "female" if g % 2 == 0 else "male"})
    with open(d / "labels.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    dev = tmp_path / "dev"; dev.mkdir()
    with open(dev / "labels.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(rows[0].keys())); w.writeheader(); w.writerows([])
    out = str(tmp_path / "t")
    s = make_test_split(str(d), str(dev), out, "participant_id", "user_id", ["sex"], per_cell=10, seed=0,
                        extra_unique=["dialogue_id"])
    picked = read_labels(out)
    dlgs = [r["dialogue_id"] for r in picked]
    assert len(dlgs) == len(set(dlgs)), "같은 대화에서 두 명이 뽑혔다"
    assert s["extra_unique"]["dialogue_id"] == len(picked)
