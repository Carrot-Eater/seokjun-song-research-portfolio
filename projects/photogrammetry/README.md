# Photogrammetry and 3D inspection maps

사진측량·3D 지도 파이프라인

[Area index](../../areas/aerial-mapping/README.md) · [All work](../../ALL_WORK.md) · [Claim boundaries](../../EVIDENCE.md)

**Status:** Reconstruction / component prototype

**Catalog reviewed:** 12 October 2026

Connect image-collection manifests to reconstruction jobs and browser-based map inspection.

## Work represented

- Collection contracts, manifest handling and reconstruction orchestration.
- A locally reported NodeODM reconstruction using a public image dataset.
- 3D viewer and collector integration seams for aerial and ground platforms.

## Technical stack and methods

Python; FastAPI; NodeODM; MinIO; Docker; ROS 2 interfaces; Three.js; 3D Tiles / GLB.

## Evidence inspected

ecorobotics_mapping README, core/server layout and web dependencies. Historical evidence is described; full original experiments were not rerun for this catalog.

## Public material

This card publishes an implementation/research summary. The complete source tree, runtime data and original local evidence are not part of this release.

## Current limits

Public-dataset images are not original flight capture. Several collectors and the COLMAP path are incomplete; end-to-end airborne acquisition is not validated.

## Contribution and upstream scope

Builds on NodeODM and other reconstruction/storage/viewer libraries; no new photogrammetry algorithm is claimed.
