# OdorCore sensing and drift infrastructure

OdorCore 센싱·드리프트

[Area index](../../areas/environmental-sensing/README.md) · [All work](../../ALL_WORK.md) · [Claim boundaries](../../EVIDENCE.md)

**Status:** Software / public-data work

**Catalog reviewed:** 12 October 2026

Organize chemical observations from fixed, cartridge, handheld and laboratory sensing paths.

## Work represented

- Sensor-data interfaces, observation storage and chemical representation/application-head prototypes.
- Monthly baseline, drift and sample-eligibility analysis.
- Separate fixed-sensing infrastructure from mobile source-search applications.

## Technical stack and methods

Python; NumPy; JSON schemas; MQTT; MOX metadata; baseline and EMA tracking.

## Evidence inspected

EcoRobotics monorepo README/source inventory and exported baseline_drift.py. Historical evidence is described; full original experiments were not rerun for this catalog.

## Public material

- [baseline_drift.py](../../baseline_drift.py)
- [test_baseline_drift.py](../../test_baseline_drift.py)

See [snapshot validation](../../VALIDATION.md) and [source provenance](../../SOURCE_PROVENANCE.json). The selected module is not the complete parent system.

## Current limits

Application heads are not all connected to a deployed runtime. Existing in-distribution models do not establish a general olfactory foundation model. Alert thresholds are heuristic.

## Contribution and upstream scope

Project integration and data-analysis work built with standard numerical and messaging libraries.
