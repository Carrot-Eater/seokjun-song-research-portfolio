# EcoHub cloud-protocol services

EcoHub 드론 프로토콜 서비스

[Area index](../../areas/operations/README.md) · [All work](../../ALL_WORK.md) · [Claim boundaries](../../EVIDENCE.md)

**Status:** Software implementation

**Catalog reviewed:** 12 October 2026

Implement device messaging and operator-facing services around a DJI Cloud API-compatible protocol surface.

## Work represented

- Message envelopes, device shadows/topology and correlated command timeouts.
- Flight-task state, mission-file handling, media callbacks and health events.
- Streaming/operator-console paths and specification/evidence tracking.

## Technical stack and methods

TypeScript; Node.js; MQTT; HTTPS; WebSocket; WPML/KMZ; RTMP/HTTP-FLV; journal/snapshot persistence.

## Evidence inspected

ecohub README, package metadata and source/test organization. Historical evidence is described; full original experiments were not rerun for this catalog.

## Public material

This card publishes an implementation/research summary. The complete source tree, runtime data and original local evidence are not part of this release.

## Current limits

Protocol compatibility is a software objective, not DJI certification or verified parity with every hardware/firmware combination. No full hardware fleet test is claimed.

## Contribution and upstream scope

Implementation uses external protocol specifications and libraries; DJI products and protocol ownership remain third party.
