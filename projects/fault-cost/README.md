# Fault injection and downstream cost

결함 주입·학습 성능 영향

[Area index](../../areas/robot-learning-data/README.md) · [All work](../../ALL_WORK.md) · [Claim boundaries](../../EVIDENCE.md)

**Status:** Published source / experiment analyses

**Catalog reviewed:** 12 October 2026

Study how timing and modality faults affect downstream learning rather than relying only on fault-detection accuracy.

## Work represented

- Deterministic synthetic clock and virtual-modality fault generators.
- Downstream policy and tactile contact-phase corruption studies in local research artifacts.

## Technical stack and methods

Python; NumPy; seeded synthetic faults; clock jitter/drift; dropped/duplicate samples; tactile/audio corruption.

## Evidence inspected

Exported fault_injection.py and OCLO research inventory. Historical evidence is described; full original experiments were not rerun for this catalog.

## Public material

- [fault_injection.py](../../fault_injection.py)
- [LICENSE-OCLO-APACHE-2.0.txt](../../LICENSE-OCLO-APACHE-2.0.txt)

See [snapshot validation](../../VALIDATION.md) and [source provenance](../../SOURCE_PROVENANCE.json). The selected module is not the complete parent system.

## Current limits

Included source is a fault generator, not the complete downstream benchmark. Results depend on data, corruption type and seeds; no universal robustness claim is made.

## Contribution and upstream scope

OCLO export retains its Apache-2.0 license and original attribution.
