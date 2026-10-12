# Capture-engine quality checks

멀티모달 캡처·품질 검사

[Area index](../../areas/robot-learning-data/README.md) · [All work](../../ALL_WORK.md) · [Claim boundaries](../../EVIDENCE.md)

**Status:** Synthetic capture / software scaffold

**Catalog reviewed:** 12 October 2026

Track required streams and quality signals before treating a captured episode as usable training data.

## Work represented

- Required-stream and completeness checks with synchronization diagnostics.
- Taxel-health and calibration-gate concepts in the capture workflow.

## Technical stack and methods

Python; dual timestamps; device sequence numbers; provenance; completeness; packet-gap / drift checks.

## Evidence inspected

EcoRobotics tools/capture_engine README and software layout. Historical evidence is described; full original experiments were not rerun for this catalog.

## Public material

This card publishes an implementation/research summary. The complete source tree, runtime data and original local evidence are not part of this release.

## Current limits

The inspected workflow includes synthetic scaffolding. Its checks are not proof of a physically validated multimodal acquisition rig.

## Contribution and upstream scope

Capture/QC integration work is separate from upstream sensor drivers and learning frameworks.
