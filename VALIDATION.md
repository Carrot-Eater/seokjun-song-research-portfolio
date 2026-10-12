# Snapshot validation

Checked on 12 October 2026.

- Python 3.12.3; NumPy 2.4.4; pytest 7.4.4.
- `python -m pytest -q -p no:cacheprovider`: **36 passed** (existing tests, with only export/import adjustments and a selection of three telemetry-free mission-ledger unit tests).
- Fault-injection import and a synthetic clock/virtual-stack smoke check passed.
- The publication candidate was scanned for private keys, common credential tokens, private IPv4 addresses, absolute home paths and email strings. No secrets or device addresses were found. The retained OCLO license contains its existing project copyright contact.
- Historical research results, live robot operation and full original repositories were not rerun by these checks.

Original working repositories were not changed. Tests write synthetic temporary data only.

## Expanded catalog checks

The same-day catalog update adds eight field indexes and 36 work-item pages, excluding coursework and including PersonTwin applications. Checked 52 Markdown files and 300 relative links: no broken targets. A scan of the publication candidate found no private-key blocks, common credential-token patterns, private IPv4 addresses or absolute home paths.

All seven exported Python implementation/test files are byte-for-byte unchanged from the initial release. The earlier 36-test result therefore remains the source-snapshot validation record; tests and historical experiments were not rerun for this documentation-only expansion. The checks validate navigation and publication hygiene, not every project's research claims.
