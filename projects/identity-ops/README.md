# Shared identity, TwinHub and operations

공통 계정·TwinHub·운영 관리

[Area index](../../areas/persontwin/README.md) · [All work](../../ALL_WORK.md) · [Claim boundaries](../../EVIDENCE.md)

**Status:** Supporting application services

**Catalog reviewed:** 12 October 2026

Coordinate identity and permitted material across PersonTwin applications.

## Work represented

- Shared-account interfaces and application-specific stores.
- TwinHub material aggregation using an explicit shared linking code.
- Operations/audit interfaces and handling paths for withdrawal or deletion.

## Technical stack and methods

Python; account router/store; operations routes; link-code matching; consent labels; withdrawal/deletion paths.

## Evidence inspected

PersonTwin video_twin/account, ops and twin_hub.py source inventory. Historical evidence is described; full original experiments were not rerun for this catalog.

## Public material

This card publishes an implementation/research summary. The complete source tree, runtime data and original local evidence are not part of this release.

## Current limits

Code paths are not an independent privacy/security audit. Runtime account databases, invitation/admin credentials and operational manifests are not included.

## Contribution and upstream scope

Supporting services are components of the same PersonTwin family, not independent research papers.
