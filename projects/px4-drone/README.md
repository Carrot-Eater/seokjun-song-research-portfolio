# PX4 / X650 integration and SITL

PX4 드론 통합·SITL

[Area index](../../areas/aerial-mapping/README.md) · [All work](../../ALL_WORK.md) · [Claim boundaries](../../EVIDENCE.md)

**Status:** SITL plus hardware connection checks

**Catalog reviewed:** 12 October 2026

Build a reproducible flight-stack integration and diagnosis workflow around an X650 / Pixhawk 6X setup.

## Work represented

- Flight-controller connection and diagnostic tooling.
- Reported generic x500 SITL offboard arm, takeoff, landing and disarm sequence.
- Separate airframe identity, software versions and step-level evidence.

## Technical stack and methods

PX4; Pixhawk 6X; MAVLink; ROS 2 message compatibility; Gazebo SITL; version locking.

## Evidence inspected

ecorobotics_drone README, locked dependencies and local integration reports. Historical evidence is described; full original experiments were not rerun for this catalog.

## Public material

This card publishes an implementation/research summary. The complete source tree, runtime data and original local evidence are not part of this release.

## Current limits

The SITL x500 is not the physical X650. Actual X650 field flight, full avionics installation and autonomous industrial inspection are not established.

## Contribution and upstream scope

PX4 and Gazebo are upstream projects; represented work is integration, diagnosis and experiment traceability.
