# Project dossier

Snapshot: 12 October 2026. This document separates implemented software from the research questions it motivates.

## 1. Go2 exploration, patrol and inspection

**Problem.** A mobile robot must keep a usable map, choose where to move and recover from stale sensing or loss of motion authority. A successful command is not automatically a verified arrival.

**Work.** Integration of a Unitree Go2 with ROS 2 navigation, LiDAR-derived mapping, a Python patrol state machine, operator controls and mission/event analysis. Jetson Orin NX operation was investigated. A web console supports supervision; language/vision models can propose interpretations or plans. The documented VLM path includes server-side inference, so this is not presented as an entirely onboard VLM system.

**Evidence to inspect.** `mission_ledger.py` distinguishes active motion, human-wait states, safe holds, manual interventions, automatic restarts and incomplete records. Missing instrumentation is not silently treated as zero failure.

**Next research question.** How should inspection policies trade information gained against uncertainty in localization, sensor health and communication? Test mission completion, verified arrival, intervention rate and recovery time under controlled degradations.

## 2. Gas-source localization and evaluation

**Problem.** A search method can encounter gas yet fail to localize the source; differing success definitions can make comparisons misleading.

**Work.** Simulation evaluation of coverage, gradient and belief-based search, with analysis of independent scoring, sensor contact, localization error and failure attribution. Prepared research-presentation material in September 2026 and manuscript/evaluation artifacts.

**Boundary.** Simulation trajectories are not physical leak-localization trials. End-to-end gas-source localization on the mobile robot remains future validation. The full experimental harness and draft manuscript are not included in this selected-code release.

## 3. Electronic nose and environmental sensor infrastructure

**Problem.** Sensor arrays vary across devices and drift with time; apparently improved alignment need not improve prediction on unseen analytes.

**Work.** MOX-array data processing, transfer/evaluation experiments, drift analysis, sensor metadata and MQTT publishing/subscribing software. `baseline_drift.py` is a self-contained example of time-dependent baseline tracking, sample eligibility and advisory outputs.

**Draft focus.** Assessing whether alignment scores predict held-out-analyte retrieval across MOX arrays. A manuscript is in preparation, not accepted or published.

**Boundary.** Multi-site functions are software capabilities, not evidence of commercial deployment. Drift thresholds and confidence labels in the example module are heuristics, not calibrated safety guarantees or hypothesis-test significance.

## 4. OCLO: multimodal data quality for robot learning

**Problem.** Timing errors, missing frames and corrupted modalities can invalidate datasets or degrade downstream policies.

**Work.** Clock mapping/synchronization, episode/data integrity tooling, fault injection and downstream evaluations with public robot-learning data. The source snapshot generates deterministic synthetic clock, tactile and audio faults.

**Boundary.** A simulator for tactile faults does not establish that a tactile device was fabricated or validated. Results from a particular benchmark, corruption pattern or random seed do not establish universal robustness.

## 5. PersonTwin: evaluation of personalized behavioural prediction

**Problem.** Personalized language models can appear predictive because prompts contain answer-relevant clues, repeated people or duplicate conversations.

**Work.** Transcript-based prediction experiments, person-level development/test separation, exact and approximate duplicate checks, baseline comparisons and ablations. `split_check.py` implements grouped splits and reports overlap and duplicates.

**Existing result and caveat.** A local corrected report describes a held-out Persuasion for Good analysis with 413 people and correlation r=0.306 (reported 95% interval 0.223-0.388). A later simple amount-extraction baseline reached about r=0.304. This does not establish an advantage from personalization. A money-blind r=0.043 result is development evidence, not a new held-out confirmation. These historical results were reviewed from local reports, not recomputed for this release.

**Next research question.** Does a model improve on population, demographic, direct-extraction and wrong-person controls on genuinely unseen people and tasks? Separate prediction from explanation, uncertainty from confidence wording, and simulated responses from real participants.

## 6. Maps, digital twins and industrial workflows

Work includes map/inspection-event integration and plans for combining fixed sensors with mobile follow-up inspections. Solar fault diagnosis, mining deployment and autonomous closed-loop gas response are proposed application directions. The portfolio does not claim completed solar-farm, mine or industrial gas deployments.
