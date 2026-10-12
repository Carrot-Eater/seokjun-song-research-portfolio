# PersonTwin behavioural prediction

PersonTwin 행동 예측·기준선

[Area index](../../areas/persontwin/README.md) · [All work](../../ALL_WORK.md) · [Claim boundaries](../../EVIDENCE.md)

**Status:** Research prototype / public-data experiments

**Catalog reviewed:** 12 October 2026

Test whether a person-specific model predicts unseen behaviour better than simple alternatives.

## Work represented

- Interview/transcript-based prediction pipelines and memory/persona modules.
- Persuasion for Good and Twin-2K-style baseline and personalization comparisons.
- Checks for person overlap, transcript duplicates, answer leakage and wrong-person controls.

## Technical stack and methods

Python; LLM evaluation; memory/retrieval; person-disjoint splits; duplicate checks; ablations; bootstrap intervals.

## Evidence inspected

PersonTwin source/reports, corrected project dossier and exported split_check.py. Historical evidence is described; full original experiments were not rerun for this catalog.

## Public material

- [split_check.py](../../split_check.py)
- [test_split_check.py](../../test_split_check.py)

See [snapshot validation](../../VALIDATION.md) and [source provenance](../../SOURCE_PROVENANCE.json). The selected module is not the complete parent system.

## Current limits

Historical PFG correlation was approximately matched by a simple amount-extraction baseline. Incremental personalization benefit and a general digital copy of a person are not established.

## Contribution and upstream scope

Research uses public corpora; their participants were not recruited for this portfolio.
