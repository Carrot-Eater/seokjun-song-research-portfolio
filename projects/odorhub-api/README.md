# OdorHub API and deployment packaging

OdorHub API·배포 패키징

[Area index](../../areas/operations/README.md) · [All work](../../ALL_WORK.md) · [Claim boundaries](../../EVIDENCE.md)

**Status:** Application / deployment tooling

**Catalog reviewed:** 12 October 2026

Extract a deployable sensing application from a larger research monorepo.

## Work represented

- API, connector and sensing-service packaging.
- Generated deployment tree and repeatable synchronization from the source monorepo.
- Persistent-state configuration and documentation of ephemeral SQLite limitations.

## Technical stack and methods

Python; API/services; Docker; Render configuration; Supabase state; deployment sync scripts.

## Evidence inspected

odorhub-deploy README/tree and EcoRobotics deployment tooling. Historical evidence is described; full original experiments were not rerun for this catalog.

## Public material

This card publishes an implementation/research summary. The complete source tree, runtime data and original local evidence are not part of this release.

## Current limits

The deployment tree is a generated slice of the monorepo, not another independent platform invention. No current uptime, customer count or production security claim is made.

## Contribution and upstream scope

Project application packaging integrates third-party hosting and storage services.
