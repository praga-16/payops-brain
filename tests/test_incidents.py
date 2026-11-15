import pytest
from fastapi.testclient import TestClient
from backend.simulator import seed,INCIDENTS
from backend.ledger import records
from backend.reconciliation import analyze
from backend.incidents import trigger
from backend.review import queue


@pytest.mark.parametrize('scenario',list(INCIDENTS))
def test_incident_injects_expected_breaks(tmp_path,monkeypatch,scenario):
    p=tmp_path/'db';monkeypatch.setenv('PAYOPS_DB',str(p));seed(16,42,p,scenario=scenario)
    assert {r['break_type'] for r in analyze(p)}=={INCIDENTS[scenario]}
    if scenario=='upi-bank-outage':assert {t['rail'] for t in records('transactions',p)}=={'UPI'}
    if scenario=='card-fraud-burst':assert {t['rail'] for t in records('transactions',p)}=={'CARD'}
    from backend.main import app
    with TestClient(app) as c:
        result=c.post('/api/incidents/'+scenario,json={'count':16,'seed':43}).json()
        assert not result['restricted_action_executed']
        assert c.get('/api/incidents').json()['runs']
    assert all(r['tier']!='AUTO_RESOLVED' for r in queue(p))
