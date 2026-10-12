"""video_twin/split_check.py — 학습/시험 분리. 같은 사람이 양쪽에 들어가는 일을 막는다.

왜 필요한가 (2026-09-19 검토 지적 2)
  우리는 PFG 400명의 결과를 **이미 봤다**. 조건을 고르고 채점기를 고치는 데 그 결과를 썼다.
  그러면 그 400명은 더 이상 시험 자료가 아니다(개발 자료다). 같은 자료로 다시 "확인했다"고
  말하면 그건 확인이 아니다. 그리고 PFG 는 한 사람이 최대 25번 나오므로, 행을 아무렇게나
  나누면 같은 사람이 개발과 시험 양쪽에 들어간다 — **묶음(사람) 단위로** 갈라야 한다.

이 파일이 하는 일
  1. 이미 본 자료(dev)의 묶음 열쇠를 모은다.
  2. 남은 묶음에서만 시험(test) 표본을 만든다 — 층(성별·역할)을 맞춰서.
  3. 중복을 세 가지로 검사한다: 같은 묶음 열쇠 / 같은 전사록 해시 / 거의 같은 전사록(5-그램 자카드).
  4. `splits.json` 에 기록하고, 시험 자료 디렉터리를 만든다.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil

SHINGLE = 5
NEAR_DUP = 0.8


def _norm_words(t: str) -> list[str]:
    body = [l.split(":", 1)[1] if ":" in l else l for l in t.splitlines() if l.strip() and not l.startswith("##")]
    return re.sub(r"[^\w\s]", " ", " ".join(body).lower()).split()


def shingles(t: str, n: int = SHINGLE) -> set:
    w = _norm_words(t)
    return {hash(tuple(w[i:i + n])) for i in range(max(0, len(w) - n + 1))}


def text_sha(t: str) -> str:
    return hashlib.sha256(" ".join(_norm_words(t)).encode()).hexdigest()[:16]


def read_labels(d: str) -> list[dict]:
    with open(os.path.join(d, "labels.csv"), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def transcript(d: str, pid: str) -> str:
    p = os.path.join(d, pid, "transcript.txt")
    return open(p, encoding="utf-8").read() if os.path.exists(p) else ""


def find_duplicates(all_dir: str, rows: list[dict], id_col: str, cluster_col: str | None,
                    near: bool = True) -> dict:
    """같은 묶음 열쇠 / 같은 글 / 거의 같은 글. 세 번째는 비용이 커서 같은 글 해시가 다른 것들만 본다."""
    by_cluster: dict = {}
    if cluster_col:
        for r in rows:
            by_cluster.setdefault(r[cluster_col], []).append(r[id_col])
    by_text: dict = {}
    for r in rows:
        t = transcript(all_dir, r[id_col])
        if t:
            by_text.setdefault(text_sha(t), []).append(r[id_col])
    exact = {k: v for k, v in by_text.items() if len(v) > 1}
    near_pairs = []
    if near:
        reps = [(v[0], shingles(transcript(all_dir, v[0]))) for v in by_text.values()]
        reps = [(p, s) for p, s in reps if len(s) >= 20]
        for i in range(len(reps)):
            for j in range(i + 1, len(reps)):
                a, b = reps[i][1], reps[j][1]
                inter = len(a & b)
                if inter and inter / len(a | b) >= NEAR_DUP:
                    near_pairs.append([reps[i][0], reps[j][0], round(inter / len(a | b), 3)])
    return {"clusters_with_multiple_rows": sum(1 for v in by_cluster.values() if len(v) > 1),
            "max_rows_per_cluster": max((len(v) for v in by_cluster.values()), default=0),
            "exact_duplicate_texts": {k: v for k, v in list(exact.items())[:20]},
            "n_exact_duplicate_groups": len(exact),
            "near_duplicate_pairs": near_pairs[:20], "n_near_duplicate_pairs": len(near_pairs)}


def make_test_split(all_dir: str, dev_dir: str, out_dir: str, id_col: str, cluster_col: str,
                    strata: list[str], per_cell: int, seed: int = 0,
                    extra_unique: list[str] | None = None) -> dict:
    """dev 에 쓰인 묶음을 통째로 빼고, 남은 묶음에서만 층 균형 표본을 만든다.

    extra_unique: 추가로 유일해야 하는 열쇠들. PFG 는 한 대화에 두 사람이 있고 둘의 전사록이 같은
    본문이라, 사람(user_id)만 유일하게 하면 **짝꿍 둘이 같이 뽑혀** 시험 안에 의존이 생긴다.
    dialogue_id 를 여기 넣으면 한 대화에서 한 명만 뽑는다."""
    import numpy as np
    all_rows = read_labels(all_dir)
    dev_rows = read_labels(dev_dir) if os.path.exists(os.path.join(dev_dir, "labels.csv")) else []
    dev_clusters = {r[cluster_col] for r in dev_rows}
    pool = [r for r in all_rows if r[cluster_col] not in dev_clusters]
    rng = np.random.default_rng(seed)
    picks, used = [], set()
    used_extra: dict = {c: set() for c in (extra_unique or [])}
    # dev 가 쓴 추가 열쇠도 통째로 뺀다(예: dev 에 나온 대화는 시험에서 쓰지 않는다)
    dev_extra = {c: {r[c] for r in dev_rows if c in r} for c in (extra_unique or [])}
    cells: dict = {}
    for r in pool:
        cells.setdefault(tuple(r.get(s, "") for s in strata), []).append(r)
    for key, rs in sorted(cells.items()):
        rs = sorted(rs, key=lambda r: r[id_col])
        order = rng.permutation(len(rs))
        for i in order:
            if len([p for p in picks if tuple(p.get(s, "") for s in strata) == key]) >= per_cell:
                break
            r = rs[i]
            if r[cluster_col] in used:          # 한 묶음에서 한 행만 — 시험 안에서도 의존을 만들지 않는다
                continue
            if any(r.get(c) in used_extra[c] or r.get(c) in dev_extra.get(c, set()) for c in used_extra):
                continue                        # 짝꿍(같은 대화)·dev 가 쓴 대화는 뺀다
            picks.append(r); used.add(r[cluster_col])
            for c in used_extra:
                used_extra[c].add(r.get(c))
    os.makedirs(out_dir, exist_ok=True)
    for r in picks:
        src = os.path.join(all_dir, r[id_col])
        dst = os.path.join(out_dir, r[id_col])
        if os.path.isdir(src) and not os.path.exists(dst):
            shutil.copytree(src, dst)
    if picks:
        with open(os.path.join(out_dir, "labels.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, list(picks[0].keys())); w.writeheader(); w.writerows(picks)
    counts: dict = {}
    for r in picks:
        counts[" / ".join(r.get(s, "") for s in strata)] = counts.get(" / ".join(r.get(s, "") for s in strata), 0) + 1
    return {"n_all_rows": len(all_rows), "n_dev_clusters": len(dev_clusters), "n_pool_rows": len(pool),
            "n_test_rows": len(picks), "n_test_clusters": len(used), "cells": counts, "out_dir": out_dir,
            "extra_unique": {c: len(v) for c, v in used_extra.items()},
            "overlap_with_dev": sorted({r[cluster_col] for r in picks} & dev_clusters)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all-dir", required=True); ap.add_argument("--dev-dir", required=True)
    ap.add_argument("--out-dir", required=True); ap.add_argument("--cluster-col", required=True)
    ap.add_argument("--id-col", default="participant_id"); ap.add_argument("--strata", default="")
    ap.add_argument("--per-cell", type=int, default=100); ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--extra-unique", default="", help="추가로 유일해야 하는 열쇠(예: dialogue_id) — 짝꿍 동시 선택 방지")
    ap.add_argument("--no-near-dup", action="store_true"); ap.add_argument("--out", default="")
    a = ap.parse_args()
    A, D, O = (os.path.expanduser(x) for x in (a.all_dir, a.dev_dir, a.out_dir))
    rows = read_labels(A)
    dup = find_duplicates(A, rows, a.id_col, a.cluster_col, near=not a.no_near_dup)
    split = make_test_split(A, D, O, a.id_col, a.cluster_col, [s for s in a.strata.split(",") if s], a.per_cell, a.seed,
                            extra_unique=[c for c in a.extra_unique.split(",") if c])
    res = {"all_dir": A, "dev_dir": D, "cluster_col": a.cluster_col, "duplicates": dup, "split": split,
           "rule": "묶음(사람·대화·조) 단위로 가른다. dev 에 한 번이라도 쓰인 묶음은 test 에 넣지 않는다."}
    if a.out:
        json.dump(res, open(os.path.expanduser(a.out), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"[split] 전체 {dup['max_rows_per_cluster']}행/묶음 최대, 여러 행인 묶음 {dup['clusters_with_multiple_rows']}개")
    print(f"[split] 같은 글 {dup['n_exact_duplicate_groups']}쌍, 거의 같은 글 {dup['n_near_duplicate_pairs']}쌍")
    s = split
    print(f"[split] dev 묶음 {s['n_dev_clusters']}개 제외 → 남은 {s['n_pool_rows']}행에서 시험 {s['n_test_rows']}행/{s['n_test_clusters']}묶음")
    print(f"[split] 층 분포 {s['cells']}")
    print(f"[split] 추가 유일 열쇠: {s['extra_unique']}")
    print(f"[split] dev 와 겹침: {len(s['overlap_with_dev'])}개 (0 이어야 한다)")


if __name__ == "__main__":
    main()
