# Seokjun Song | Research & engineering portfolio

Environmental engineering undergraduate at **Seoul National University of Science and Technology (SeoulTech)**. My main research direction is edge robotics for autonomous patrol, environmental sensing and leak investigation. **PersonTwin** is a second line of work on personalized behavioural prediction and its evaluation. I am interested in research degrees starting in the second half of 2027.

**Browse: [All 36 work items](ALL_WORK.md) · [한국어 안내](README.ko.md) · [Technical stack](TECHNOLOGY_MATRIX.md) · [Coverage and exclusions](COVERAGE.md)**

## Browse by field

This catalog organizes the inspected research and application work into **8 fields and 36 work items**. Items include components, related studies and design-stage work within larger project families. They are not 36 completed projects or publications. Coursework is excluded.

| Field / 분야 | Work items |
|---|---:|
| [Field robotics & autonomy · 로봇 자율주행·미션](areas/robotics/README.md) | 5 |
| [Drones & mapping · 드론·지도·3D 재구성](areas/aerial-mapping/README.md) | 3 |
| [Environmental sensing · 전자코·환경·청각 센싱](areas/environmental-sensing/README.md) | 6 |
| [Gas-source localization · 가스 누출원 탐색·평가](areas/gas-localization/README.md) | 3 |
| [Robot-learning data quality · 로봇 학습 데이터·OCLO](areas/robot-learning-data/README.md) | 4 |
| [Operations software · 관제·웹·배포](areas/operations/README.md) | 3 |
| [PersonTwin & human modelling · PersonTwin 연구·서비스](areas/persontwin/README.md) | 11 |
| [Research applications · 태양광·마이닝 연구 기획](areas/applications/README.md) | 1 |

Each item has its own page covering the problem, implementation, technologies, local evidence, current limits and upstream scope. The catalog includes the PersonTwin research pipeline and its participant, coaching, character, memory and operations applications.

## What is public here

All 36 cards and the area indexes are public. **Four selected implementation modules** and their associated tests/provenance are also published below. The full original project trees have not been released. Cards explicitly say when only documentation is public.

The [research dossier](PROJECTS.md) adds context for the core research lines. The [evidence guide](EVIDENCE.md) separates historical experiments, software prototypes, hardware designs and future applications. Research manuscripts remain in preparation.

## Inspect and run selected source

This repository publishes a focused, auditable selection from the projects above. It is not a backup of the full robot installation. The snapshots below contain real project code, with portable test imports documented in [source provenance](SOURCE_PROVENANCE.json).

| Source | Purpose |
|---|---|
| [mission_ledger.py](mission_ledger.py) | Turn robot event streams into sessions, missions, intervention counts and explicitly bounded autonomous time |
| [baseline_drift.py](baseline_drift.py) | Monthly site/population baselines, drift summaries and online EMA tracking |
| [fault_injection.py](fault_injection.py) | Seeded clock drift, jitter, dropped/duplicate samples and synthetic tactile/audio faults |
| [split_check.py](split_check.py) | Construct person-disjoint evaluation sets and detect exact/near duplicate transcripts |

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
python mission_ledger.py --help
python split_check.py --help
```

Tests use synthetic records. No robot, sensor, private dataset, API credential or GPU is needed. The original mission-ledger integration tests that rely on recorded robot telemetry are not part of this export. See [VALIDATION.md](VALIDATION.md) for the actual snapshot check results.

## Attribution and scope

My work uses established open-source components. The Go2 integration builds on `h-naderi/unitree-go2-slam-nav2` and the broader ROS 2, Nav2 and SLAM ecosystems; these algorithms are not claimed as my inventions. OCLO uses OpenGraph/LeRobot-related tooling and public robot-learning benchmarks. PersonTwin evaluates publicly available research corpora; these participants were not recruited by me.

The exported OCLO fault-injection module retains the project Apache-2.0 license in [LICENSE-OCLO-APACHE-2.0.txt](LICENSE-OCLO-APACHE-2.0.txt). That license is not a blanket relicensing of the other snapshots. Other code retains its existing rights; no new repository-wide license is asserted. No upstream source trees or third-party datasets are redistributed here.

Research drafts are in preparation. This portfolio does not claim accepted publications, certified gas-safety capability or autonomous industrial deployment.
