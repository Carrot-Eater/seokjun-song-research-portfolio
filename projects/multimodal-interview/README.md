# Multimodal interview measurements

인터뷰 음성·얼굴·비언어 측정

[Area index](../../areas/persontwin/README.md) · [All work](../../ALL_WORK.md) · [Claim boundaries](../../EVIDENCE.md)

**Status:** Measurement software prototype

**Catalog reviewed:** 12 October 2026

Summarize bounded interview signals with explicit timing, quality and missingness.

## Work represented

- Per-session signal summaries with sampling denominators and quality markers.
- Within-person baseline comparisons and nonverbal feature/cluster investigations.
- Voice-interface, browser-extension and local TTS integration artifacts.

## Technical stack and methods

Audio/face capture; shared clock; speech onset; pause/pitch summaries; head motion; aggregate feature records.

## Evidence inspected

PersonTwin video_twin/multimodal README, chrome_ext files and voice interface modules. Historical evidence is described; full original experiments were not rerun for this catalog.

## Public material

This card publishes an implementation/research summary. The complete source tree, runtime data and original local evidence are not part of this release.

## Current limits

Measurements are not diagnoses or validated emotion/personality labels. Feature stability does not prove reproducible behavioural types. Raw audio/face records are not included.

## Contribution and upstream scope

Capture and application integration rely on external models and browser/media facilities.
