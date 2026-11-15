import pytest
from fastapi.testclient import TestClient
from backend.simulator import seed
from backend.ledger import initialize,connect
from backend.moneyflow import flow,flow_summary


@pytest.fixture
def ledger(tmp_path,monkeypatch):
    p=tmp_path/'ledger.db';monkeypatch.setenv('PAYOPS_DB',str(p));seed(32,72,p)
    return p


def test_lifecycle_clean_and_injected_gaps(ledger):
    clean=flow('SIM-72-32-T00009',ledger)
    assert clean['clearing_settlement_gap_paise']==0
    assert [s['stage'] for s in clean['stages']]==['AUTHORIZATION','CLEARING','SETTLEMENT']
    missing=flow('SIM-72-32-T00000',ledger)
    assert missing['stuck_paise']>0 and missing['likely_cause']=='MISSING_SETTLEMENT'
    assert flow('SIM-72-32-T00001',ledger)['stuck_paise']>0
    assert flow('SIM-72-32-T00002',ledger)['excess_settlement_paise']>0
    with connect(ledger) as c:
        c.execute("UPDATE lifecycle_events SET amount_paise=amount_paise-100 WHERE transaction_id='SIM-72-32-T00009' AND stage='CLEARING'")
    assert flow('SIM-72-32-T00009',ledger)['authorization_clearing_gap_paise']==100


def test_migration_idempotent_and_api(ledger):
    initialize(ledger);initialize(ledger)
    with connect(ledger) as c:
        assert c.execute('SELECT COUNT(*) FROM lifecycle_events').fetchone()[0]==64
    summary=flow_summary(ledger)
    assert summary['stuck_paise']==sum(r['stuck_paise'] for r in summary['by_rail'])
    from backend.main import app
    with TestClient(app) as c:
        assert c.get('/api/money-flow/summary').status_code==200
        assert c.get('/api/money-flow/SIM-72-32-T00009').json()['synthetic']
        assert c.get('/api/money-flow/missing').status_code==404
