# Seokjun Song | Environmental sensing & autonomous robotics

Environmental engineering undergraduate at **Seoul National University of Science and Technology (SeoulTech)**. I build research software around autonomous inspection, chemical sensing and evaluation of learning systems. I am interested in research degrees starting in the second half of 2027.

My main direction is an edge robot that patrols industrial environments, gathers useful measurements and investigates suspected leaks. Mining and solar infrastructure are application interests. A second direction, **PersonTwin**, studies when personalized models actually predict unseen human behaviour beyond simple baselines.

## Research projects

| Project | Work represented here | Current maturity |
|---|---|---|
| Go2 autonomous exploration and patrol | ROS 2 / Nav2 integration, Jetson operation, mission state machine, motion guards, browser supervision and operational evidence | Research robot prototype; field reliability remains under evaluation |
| Gas-source localization | Simulation comparisons, scorer consistency, failure attribution and evaluation protocols | Simulation research and manuscript preparation; no claim of deployed leak detection |
| Electronic nose and EcoRobotics sensing | MOX data pipelines, cross-array transfer, drift analysis, MQTT/schema integration | Software and dataset experiments; end-to-end industrial deployment not established |
| OCLO / robot learning data quality | Multimodal timing, fault injection, dataset integrity and downstream learning evaluation | Synthetic/public-data experiments and software tooling |
| PersonTwin | Person-disjoint evaluation, duplicate checks, personalized prediction and baseline controls | Research prototype; incremental predictive value remains an open question |
| Infrastructure digital twins | Connecting maps, sensor events and inspection workflows | Component prototypes and research planning |
| Solar / mining robotics | Reusing perception and navigation for inspection and monitoring | Proposed applications, not completed industry projects |

Read the [project dossier](PROJECTS.md), [technology matrix](TECHNOLOGY_MATRIX.md) and [evidence boundaries](EVIDENCE.md).

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
