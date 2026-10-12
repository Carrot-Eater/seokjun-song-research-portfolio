# Snapshot validation

Checked on 12 October 2026.

- Python 3.12.3; NumPy 2.4.4; pytest 7.4.4.
- `python -m pytest -q -p no:cacheprovider`: **36 passed** (existing tests, with only export/import adjustments and a selection of three telemetry-free mission-ledger unit tests).
- Fault-injection import and a synthetic clock/virtual-stack smoke check passed.
- The publication candidate was scanned for private keys, common credential tokens, private IPv4 addresses, absolute home paths and email strings. No secrets or device addresses were found. The retained OCLO license contains its existing project copyright contact.
- Historical research results, live robot operation and full original repositories were not rerun by these checks.

Original working repositories were not changed. Tests write synthetic temporary data only.
