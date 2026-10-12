# Evidence and claim boundaries

This portfolio is an engineering/research snapshot, not a publication list. Research manuscripts are in preparation. Project descriptions are based on local code, presentations and experiment reports; historical experiments were not all rerun for publication of this repository.

| Statement | What supports it | What it does not establish |
|---|---|---|
| Go2 navigation/patrol integration exists | Source, robot-operation notes and mission-log analyses | Robust industrial deployment or fully onboard VLM inference |
| Gas localization was studied | Simulation harnesses, evaluation artifacts and presentation material | Successful physical gas localization on the robot |
| MOX transfer and drift were studied | Source and manuscript-preparation artifacts | A published paper or validated safety detector |
| Data-quality faults can be simulated | Included source generates clock/tactile/audio corruptions | Validation of all hardware modalities |
| Person-level splits and duplicate audits exist | Included source and synthetic tests | A general-purpose digital copy of a person |
| Personalization showed historical correlation | Corrected local report and later baseline comparison | Incremental benefit over direct answer extraction |

The raw robot telemetry, participant transcripts, API credentials, device addresses, unreleased manuscripts and private academic documents are excluded. The source snapshots are illustrative research modules, not a safety-rated controller or a full deployment distribution.

## Reproducibility notes

`SOURCE_PROVENANCE.json` records source hashes and changes for exported files. Original working repositories are unchanged. Test imports are adapted for a flat, easily browsable export. Three original mission-ledger unit cases are selected because they do not require private robot logs. PersonTwin tests create synthetic transcripts.

The PersonTwin near-duplicate checker uses Python's built-in shingle hashes within each process; it is not a portable persisted hash signature across processes. The drift module uses heuristic alert thresholds and a sample-count-based confidence category. These limits should inform any reuse.

## Expanded catalog maturity

The [36-item catalog](ALL_WORK.md) includes software components, related experimental studies, service prototypes and design/planning work. Counts do not represent papers or independently completed systems. Each card identifies whether selected source or documentation alone is public.

Flight simulation is distinguished from physical X650 flight; stationary/synthetic map registration from aerial-to-ground transfer; fabrication files from manufactured hardware; simulator telemetry from live device operations; application code from validated behavioural prediction or clinical efficacy. Mining and solar are proposed applications.

The catalog is based on inspected local documents/source layouts. Original authorship, licensing and experimental validity of every full repository have not been independently audited. Upstream-dependent reproduction work is explicitly attributed, and unresolved forks are excluded from the authored-project list. See [coverage](COVERAGE.md).
