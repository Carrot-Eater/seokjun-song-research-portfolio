# MapFuse cross-platform map registration

MapFuse 지도 정합

[Area index](../../areas/aerial-mapping/README.md) · [All work](../../ALL_WORK.md) · [Claim boundaries](../../EVIDENCE.md)

**Status:** Synthetic and limited scan-pair checks

**Catalog reviewed:** 12 October 2026

Standardize maps from different SLAM pipelines and decide when registration is acceptable or ambiguous.

## Work represented

- Common bundle contracts for FAST-LIO2 and RTAB-Map outputs.
- Floor/gravity alignment and yaw-plus-translation registration.
- Accept, reject and ambiguous decisions followed by occupancy-map export.

## Technical stack and methods

PCD / metadata / TUM bundles; gravity alignment; FPFH; RANSAC; ICP; 4-DoF registration; Nav2 map export.

## Evidence inspected

mapfuse README, synthetic-test descriptions and stationary Mid-360 repeat-pair report. Historical evidence is described; full original experiments were not rerun for this catalog.

## Public material

This card publishes an implementation/research summary. The complete source tree, runtime data and original local evidence are not part of this release.

## Current limits

A real drone-to-Go2 viewpoint-transfer experiment is not established. Synthetic tests and repeated stationary scans cover narrower conditions.

## Contribution and upstream scope

Uses upstream registration and SLAM methods; represented work is workflow integration and decision criteria.
