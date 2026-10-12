# Mission and intervention accounting

미션·개입·자율시간 분석

[Area index](../../areas/robotics/README.md) · [All work](../../ALL_WORK.md) · [Claim boundaries](../../EVIDENCE.md)

**Status:** Published source

**Catalog reviewed:** 12 October 2026

Convert robot event streams into explicit sessions, missions and bounded measures of autonomous activity.

## Work represented

- Distinguish active motion, human waiting, safe holds, manual interventions and automatic restarts.
- Keep incomplete records visible instead of treating missing instrumentation as successful autonomy.

## Technical stack and methods

Python; JSON/JSONL; event-state analysis; pytest.

## Evidence inspected

Exported mission_ledger.py, source provenance and three telemetry-free original unit cases. Historical evidence is described; full original experiments were not rerun for this catalog.

## Public material

- [mission_ledger.py](../../mission_ledger.py)
- [test_mission_ledger_units.py](../../test_mission_ledger_units.py)

See [snapshot validation](../../VALIDATION.md) and [source provenance](../../SOURCE_PROVENANCE.json). The selected module is not the complete parent system.

## Current limits

Private robot telemetry and the full integration test suite are not exported. Accounting rules depend on the quality of event instrumentation.

## Contribution and upstream scope

Project analysis module, with selected test imports adapted for this repository.
