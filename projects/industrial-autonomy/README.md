# Industrial autonomy platform

산업 자율로봇 플랫폼

[Area index](../../areas/robotics/README.md) · [All work](../../ALL_WORK.md) · [Claim boundaries](../../EVIDENCE.md)

**Status:** Simulation / component prototype

**Catalog reviewed:** 12 October 2026

Organize sensing, mission logic, safety checks and hardware abstraction for inspection research.

## Work represented

- Single mission-to-safety-to-HAL command path with stop and geofence checks.
- Gas-search, shared-belief and task-allocation components, digital-twin interfaces and data export.
- Arm/controller and MoveIt configuration work at software level.

## Technical stack and methods

ROS 2 Jazzy; HAL interfaces; sensor-validity checks; simulation; episode export; kinematics.

## Evidence inspected

ecorobotics_platform_ws README and dated STATUS matrix. Historical evidence is described; full original experiments were not rerun for this catalog.

## Public material

This card publishes an implementation/research summary. The complete source tree, runtime data and original local evidence are not part of this release.

## Current limits

Arm hardware, force/torque sensing and physical calibration are not validated. Some MoveIt configuration was written without an installed/verified stack. Simulation results do not establish field performance.

## Contribution and upstream scope

Application interfaces and integration use upstream ROS/robotics tooling.
