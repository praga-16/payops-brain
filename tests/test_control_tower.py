from decimal import Decimal
import time

import pytest
from fastapi.testclient import TestClient
from backend.ledger import initialize,records
from backend.control_tower import summary,run_agents,SimulatorService
from backend.simulator import seed


@pytest.fixture
def local_db(tmp_path,monkeypatch):
    path=tmp_path/'db.sqlite3';monkeypatch.setenv('PAYOPS_DB',str(path));initialize(path)
    return path


def test_aggregations_are_ledger_computed(local_db):
    assert summary(local_db)['total_transactions']==0
    seed(32,42,local_db);run_agents(local_db)
    s=summary(local_db)
    assert s['total_transactions']==32 and s['missing_settlements']==2
    assert s['short_settlements']==2 and s['duplicate_settlements']==2
    assert Decimal(s['total_transaction_volume'])*100==sum(r['amount_paise'] for r in records('transactions',local_db))
    assert s['resolution_sample_count']==0 and s['average_resolution_seconds'] is None
    assert not s['payment_executed']


def test_simulator_start_stop(local_db):
    svc=SimulatorService()
    state=svc.start(count=16,seed_value=100,continuous=False,interval=2)
    assert not state['running'] and state['batches']==1 and not state['error']
    svc.start(count=16,seed_value=101,continuous=True,interval=2)
    with pytest.raises(ValueError):svc.start(count=16,seed_value=102,continuous=True,interval=2)
    svc.stop()
    assert not svc.status()['running']


def test_control_tower_endpoints(local_db):
    from backend.main import app
    with TestClient(app) as c:
        r=c.post('/api/simulator/start',json={'count':16,'seed':77})
        assert r.status_code==200 and not r.json()['error']
        for path in ('dashboard/summary','transactions','settlements','merchants','reconciliation',
                     'agents','agents/activity','simulator/status','configuration','evaluation','feedback'):
            assert c.get('/api/'+path).status_code==200,path
        case=c.get('/api/review-queue').json()[0]
        evidence=c.get('/api/review-queue/'+case['decision']['case_id']+'/evidence').json()
        assert set(case['decision']['evidence'])=={r['id'] for r in evidence}
        assert c.post('/api/simulator/start',json={'count':1}).status_code==422
        assistant=c.post('/api/merchant-assistant/chat',json={'merchant_id':'SYN-M001','question':'Why is settlement short?','language':'ta'})
        assert assistant.status_code==200
        assert 'api_key' not in str(c.get('/api/configuration').json()).lower()
