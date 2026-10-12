# Go2–drone mission orchestration

Go2·드론 미션 오케스트레이션

[Area index](../../areas/robotics/README.md) · [All work](../../ALL_WORK.md) · [Claim boundaries](../../EVIDENCE.md)

**Status:** Software / unit-level prototype

**Catalog reviewed:** 12 October 2026

Translate structured missions into ROS 2 actions spanning robot skills and station coordination.

## Work represented

- Mission validation and dispatch across Go2, drone and arm skill interfaces.
- Station queues, battery/docking state, latched STOP and geofence checks.
- Learning traces, variants and promotion scaffolding.

## Technical stack and methods

ROS 2 actions/messages; JSON schema; mission/skill servers; PX4 offboard interface; Gazebo scaffolding.

## Evidence inspected

eco_mission_ws README verification matrix and package layout. Historical evidence is described; full original experiments were not rerun for this catalog.

## Public material

This card publishes an implementation/research summary. The complete source tree, runtime data and original local evidence are not part of this release.

## Current limits

Drone patrol, sampling and docking tasks are planned interfaces, not verified flights. Battery swapping and event-triggered inspection remain blocked; collision-avoidance layers are unfinished.

## Contribution and upstream scope

Application orchestration built around ROS 2 and PX4; upstream flight control is not original work.
