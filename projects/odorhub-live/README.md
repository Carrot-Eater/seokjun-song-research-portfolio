# OdorHub Live Ops interface

OdorHub Live Ops 관제 웹앱

[Area index](../../areas/operations/README.md) · [All work](../../ALL_WORK.md) · [Claim boundaries](../../EVIDENCE.md)

**Status:** Simulator-backed web prototype

**Catalog reviewed:** 12 October 2026

Provide a map-centred operations interface for drone and ground-robot mission supervision.

## Work represented

- Operations, liveview, missions, devices, callbacks, mapping, site operations and settings views.
- Virtual-drone and Go2 telemetry, simulated commands and synthetic camera paths.
- Deployable frontend/backend shape with documented demo-state limits.

## Technical stack and methods

Next.js; React; Tailwind CSS; MapLibre; NestJS; Socket.IO; TypeScript.

## Evidence inspected

arrayhub repository README and frontend/backend structure, titled OdorHub Live Ops. Historical evidence is described; full original experiments were not rerun for this catalog.

## Public material

This card publishes an implementation/research summary. The complete source tree, runtime data and original local evidence are not part of this release.

## Current limits

The inspected demo is simulator-backed. Virtual commands and video stubs do not constitute live hardware control.

## Contribution and upstream scope

Application development uses established UI, map and backend frameworks.
