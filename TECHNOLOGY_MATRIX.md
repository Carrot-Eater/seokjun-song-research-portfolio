# Technology and evidence matrix

Entries describe technologies present in the inspected projects. They are not certifications or a claim of equal proficiency in every library.

| Area | Technologies / methods | Evidence and level |
|---|---|---|
| Robotics integration | Python, ROS 2, Nav2, SLAM integration, LiDAR, occupancy maps, state machines | Go2 prototype integration and local source/log artifacts |
| Edge computing | NVIDIA Jetson Orin NX, Linux, process/latency/thermal observations | Onboard navigation experiments; server-side VLM remains part of the architecture |
| Operator interfaces | JavaScript, browser dashboards, structured event/mission data | Prototype supervision console and mission ledger |
| Chemical sensing | MOX arrays, calibration metadata, drift, transfer evaluation | Sensor software and public-data experiments |
| Data interfaces | JSON/JSONL, CSV, MQTT, TLS configuration, Python SDK patterns | Local EcoRobotics source; no claim of independently audited security |
| Numerical / ML work | NumPy, pandas, scikit-learn, PyTorch, OpenCV | Project code and experimental dependencies |
| Robot-learning data | LeRobot-related formats, episode integrity, timing synchronization, fault injection | OCLO software and public-benchmark evaluation |
| Personalization | LLM evaluation, retrieval/memory prototypes, person-disjoint splits, bootstrap intervals, ablations | PersonTwin development and corrected evaluation reports |
| Research practice | Baselines, failure attribution, paired comparisons, regression tests, evidence traceability | Local reports, source and selected exported checks |
| Application development goals | Mine/solar inspection, uncertainty-aware active sensing, long-term human adaptation | Proposed research; not completed industry experience |

## Skills to deepen for doctoral research

- Probabilistic inference and planning under partial observability for active gas-source localization.
- Quantitative field validation: repeated physical trials, calibration, controlled failures and intervention accounting.
- Thermal/PV diagnostics for solar inspection and mining-specific sensing constraints.
- Statistical validity and human-subject study design for PersonTwin and human-robot adaptation.
- Clear authorship/contribution statements, thesis assessment and completed peer-reviewed research outputs.

Rust planning documents are not counted as demonstrated Rust implementation expertise. Using Nav2 or an upstream SLAM stack is not equivalent to implementing those algorithms from scratch.
