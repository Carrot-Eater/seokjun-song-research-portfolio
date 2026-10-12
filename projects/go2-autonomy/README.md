# Go2 exploration, patrol and navigation

Go2 탐색·순찰·자율주행

[Area index](../../areas/robotics/README.md) · [All work](../../ALL_WORK.md) · [Claim boundaries](../../EVIDENCE.md)

**Status:** Robot prototype

**Catalog reviewed:** 12 October 2026

Integrate a quadruped navigation stack with mission logic and operator supervision for environmental inspection.

## Work represented

- Mapping and navigation integration, patrol states, motion guards and recovery handling.
- Incident-to-regression records, localization/pose-graph failure investigations and planner-proposal evaluation.
- Edge-compute operation and inspection interfaces; some language/vision inference uses a server.

## Technical stack and methods

Python; ROS 2; Nav2; LiDAR / Mid-360; SLAM integration; Jetson Orin NX; browser supervision.

## Evidence inspected

Go2 source workspace, deployment notes, incident records and the field-robotics inventory. Historical evidence is described; full original experiments were not rerun for this catalog.

## Public material

This card publishes an implementation/research summary. The complete source tree, runtime data and original local evidence are not part of this release.

## Current limits

Historical robot trials are not a measured industrial reliability guarantee. Full onboard VLM inference, physical gas localization and a completed Rust controller are not established here.

## Contribution and upstream scope

Builds on h-naderi/unitree-go2-slam-nav2, ROS 2, Nav2 and upstream SLAM components. Integration and evaluation are the represented work.
