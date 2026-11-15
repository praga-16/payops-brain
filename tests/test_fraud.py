from backend.fraud import analyze, persist_alerts
from backend.simulator import seed
from backend.ledger import connect
from backend import audit


def test_burst_refund_and_device_alerts(tmp_path):
    path=tmp_path/'ledger.db';seed(160,42,path)
    alerts=analyze(path)
    assert any(a['velocity_60s']>=5 for a in alerts)
    assert any(a['refund_ratio']>1 for a in alerts)
    assert all(0<=a['risk_score']<=1 for a in alerts)
    assert all(not a['processing_disabled'] for a in alerts)
    assert persist_alerts(alerts,path)==len(alerts)
    assert persist_alerts(alerts,path)==0
    with connect(path) as conn:
        assert not conn.execute('SELECT 1 FROM fraud_alerts WHERE approved=1').fetchone()
        assert audit.verify(conn)['valid']


def test_calm_merchant_has_no_false_burst(tmp_path):
    path=tmp_path/'ledger.db';seed(32,43,path)
    with connect(path) as conn:
        conn.execute('UPDATE transactions SET device_risk=.05')
        conn.execute('DELETE FROM refunds')
    assert not any(a['velocity_60s']>=5 for a in analyze(path))
