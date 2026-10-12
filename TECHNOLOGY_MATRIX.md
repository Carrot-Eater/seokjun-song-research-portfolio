# Technology and evidence matrix

[Home](README.md) · [All work](ALL_WORK.md)

Technologies below are present in the inspected project materials. This is not a certification or a claim of equal proficiency in every dependency. Open a work item for its evidence and limits.

| Work item | Stack / methods | Level |
|---|---|---|
| [Go2 exploration, patrol and navigation](projects/go2-autonomy/README.md) | Python; ROS 2; Nav2; LiDAR / Mid-360; SLAM integration; Jetson Orin NX; browser supervision | Robot prototype |
| [Mission and intervention accounting](projects/mission-accounting/README.md) | Python; JSON/JSONL; event-state analysis; pytest | Published source |
| [Go2–drone mission orchestration](projects/multi-robot-missions/README.md) | ROS 2 actions/messages; JSON schema; mission/skill servers; PX4 offboard interface; Gazebo scaffolding | Software / unit-level prototype |
| [Industrial autonomy platform](projects/industrial-autonomy/README.md) | ROS 2 Jazzy; HAL interfaces; sensor-validity checks; simulation; episode export; kinematics | Simulation / component prototype |
| [Isaac Lab navigation and exploration studies](projects/isaac-navigation/README.md) | Isaac Lab; Python; reinforcement learning; belief/heatmap representations; rollout visualization | Simulation experiments |
| [PX4 / X650 integration and SITL](projects/px4-drone/README.md) | PX4; Pixhawk 6X; MAVLink; ROS 2 message compatibility; Gazebo SITL; version locking | SITL plus hardware connection checks |
| [Photogrammetry and 3D inspection maps](projects/photogrammetry/README.md) | Python; FastAPI; NodeODM; MinIO; Docker; ROS 2 interfaces; Three.js; 3D Tiles / GLB | Reconstruction / component prototype |
| [MapFuse cross-platform map registration](projects/mapfuse/README.md) | PCD / metadata / TUM bundles; gravity alignment; FPFH; RANSAC; ICP; 4-DoF registration; Nav2 map export | Synthetic and limited scan-pair checks |
| [OdorCore sensing and drift infrastructure](projects/odorcore/README.md) | Python; NumPy; JSON schemas; MQTT; MOX metadata; baseline and EMA tracking | Software / public-data work |
| [Electronic-nose SDK and experiment tooling](projects/enose-sdk/README.md) | Python SDK; sensor schemas; data adapters; scripts; tests; firmware integration scaffolding | Software prototype |
| [MOX cross-array and cross-device transfer](projects/mox-transfer/README.md) | MOX time-series processing; direct / piecewise direct standardization; fine-tuning; retrieval evaluation; controls | Dataset experiments / manuscript preparation |
| [Gas-sensor data and metadata audits](projects/gas-data-quality/README.md) | Corpus/setup cards; metadata audits; response-curve extraction; time-series analysis; missingness analysis | Research analyses / candidate studies |
| [Environmental sensor PCB design](projects/sensor-pcb/README.md) | PCB CAD; Gerber; IPC-2581; BOM; pick-and-place; 3D mechanical exports | Design / fabrication exports |
| [Acoustic sensing and array studies](projects/acoustic-sensing/README.md) | Python; DCASE / IDMT datasets; acoustic-format conversion; training/evaluation scripts; array-processing studies | Public-data software / hardware concept |
| [Gas-source search and evaluation](projects/gsl-evaluation/README.md) | Python; simulation; GADEN integration; OFAT sensitivity; independent scoring; baseline comparisons | Simulation research / manuscript preparation |
| [Coded-tracer source identification](projects/coded-tracer/README.md) | Coded excitation; transfer-matrix identification; synthetic response models; candidate ranking; baseline comparison | Synthetic studies / experiment design |
| [Sensor-network scoring and AMC research](projects/sensor-network-methods/README.md) | Sensor placement; censored likelihood; abstention; source ranking; literature coding; response-kernel design | Methods / simulation / literature work |
| [OCLO timing and dataset integrity](projects/oclo-timing/README.md) | Python; clock mapping; episode writing; LeRobot-related formats; timestamp precision; metadata validation | Research software / public-data analyses |
| [Fault injection and downstream cost](projects/fault-cost/README.md) | Python; NumPy; seeded synthetic faults; clock jitter/drift; dropped/duplicate samples; tactile/audio corruption | Published source / experiment analyses |
| [Capture-engine quality checks](projects/capture-quality/README.md) | Python; dual timestamps; device sequence numbers; provenance; completeness; packet-gap / drift checks | Synthetic capture / software scaffold |
| [OCLO wearable and rig design work](projects/oclo-hardware/README.md) | Glove/rig design; sync-hub and microcontroller firmware scaffolding; PCB planning; interface/procurement studies | Hardware / firmware planning |
| [EcoHub cloud-protocol services](projects/ecohub-protocol/README.md) | TypeScript; Node.js; MQTT; HTTPS; WebSocket; WPML/KMZ; RTMP/HTTP-FLV; journal/snapshot persistence | Software implementation |
| [OdorHub Live Ops interface](projects/odorhub-live/README.md) | Next.js; React; Tailwind CSS; MapLibre; NestJS; Socket.IO; TypeScript | Simulator-backed web prototype |
| [OdorHub API and deployment packaging](projects/odorhub-api/README.md) | Python; API/services; Docker; Render configuration; Supabase state; deployment sync scripts | Application / deployment tooling |
| [PersonTwin behavioural prediction](projects/personalized-prediction/README.md) | Python; LLM evaluation; memory/retrieval; person-disjoint splits; duplicate checks; ablations; bootstrap intervals | Research prototype / public-data experiments |
| [Theory-informed comparison harness](projects/theory-evaluation/README.md) | Python; prompt adapters; input hashing; paired bootstrap; Holm correction; participant/group units | Evaluation software prototype |
| [Task-specific intuition priors](projects/intuition-priors/README.md) | Lexical priors; nested / out-of-fold evaluation; manifests and hashes; held-out prediction records; feedback logs | Development / evaluation prototype |
| [Multimodal interview measurements](projects/multimodal-interview/README.md) | Audio/face capture; shared clock; speech onset; pause/pitch summaries; head motion; aggregate feature records | Measurement software prototype |
| [Interview and retest collection protocol](projects/interview-protocol/README.md) | Country/language instrument versions; consent/checkpoints; withdrawal; frozen instruments; retest scheduling | Protocol / collection software draft |
| [P1 participant and research portal](projects/participant-portal/README.md) | Python router/services; SQLite store layer; consent/flow state; task modules; external-AI interfaces | Web application prototype |
| [PersonTwin Coach / Maeumgil](projects/coach-service/README.md) | Python; router/store modules; external-AI adapter; safety handling; scale interfaces | Application prototype |
| [TTONA interview-based characters](projects/character-service/README.md) | Python; router/service/store modules; interview-derived context; application state | Application prototype |
| [TwinChat and personal memory](projects/twinchat-memory/README.md) | Python; retrieval/memory; source tracking; conversation lenses; diary inputs; tool-history checks | Application prototype |
| [Shared identity, TwinHub and operations](projects/identity-ops/README.md) | Python; account router/store; operations routes; link-code matching; consent labels; withdrawal/deletion paths | Supporting application services |
| [Generative Agents reproduction](projects/generative-agents-reproduction/README.md) | Python; LLM-call adapters; headless simulation; patch-based changes; behavioural-log analysis | Upstream-based reproduction work |
| [Mining and solar inspection research planning](projects/mining-solar-research/README.md) | Research-roadmap design; edge inspection; fixed/mobile sensing; experiment and field-validation planning | Proposed applications |

## Research development priorities

- Repeated physical experiments, calibration and controlled failure tests for inspection and gas-source localization.
- Probabilistic inference and planning under partial observability for active sensing.
- Domain-specific field validation for proposed solar and mining applications.
- Statistical validity, human-subject study design and stronger baselines for PersonTwin.
- Clear contribution records and completed, independently reviewed research outputs.

Using Nav2, PX4, a SLAM library, a pretrained policy or an upstream agent simulator does not mean those algorithms were implemented from scratch. Rust design/skeleton work is not listed as demonstrated Rust implementation expertise.
