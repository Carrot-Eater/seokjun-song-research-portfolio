"""Selected existing unit tests; no real robot telemetry is distributed."""
import mission_ledger as ml

def test_authority_cause_strips_nested_prefix():
    nested = 'automatic authority lost: ' * 17 + 'automatic mission stopped: permit_expired'
    assert ml.authority_cause(nested) == ('auto', 'permit_expired')
    assert ml.authority_cause('automatic authority lost: operator stop') == ('human', 'operator_stop')
    assert ml.authority_cause('manual takeover: automatic mission stopped') == ('human', 'manual_takeover')
    assert ml.authority_cause('connection lost: automatic mission stopped') == ('auto', 'connection_lost')
    assert ml.authority_cause('driver reconnected: automatic mission stopped') == ('auto', 'driver_reconnected')
    assert ml.authority_cause('stop_move') == ('auto', 'stop_move')

def test_split_by_day_at_kst_midnight():
    t0 = ml._epoch('2026-10-05T23:59:00+09:00')
    assert ml.split_by_day(t0, 120.0) == [('2026-10-05', 60.0), ('2026-10-06', 60.0)]

def test_hold_flags():
    assert ml.hold_flags('safety: loc_lost,scan_lost') == ['loc_lost', 'scan_lost']
