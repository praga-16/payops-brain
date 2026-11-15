from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from backend.simulator import seed
from backend.ledger import connect,records
from backend.margins import profit_summary,fee_audit
from backend.review import persist,queue
from backend.merchant import chat


@pytest.fixture
def ledger(tmp_path,monkeypatch):
    p=tmp_path/'db';monkeypatch.setenv('PAYOPS_DB',str(p));seed(32,71,p);return p


def test_margin_arithmetic_snapshots_and_fee_gate(ledger,monkeypatch):
    report=profit_summary(ledger)
    assert report['totals']['fees_paid_paise']==sum(r['amount_paise'] for r in records('fees',ledger))
    assert report['totals']['net_margin_paise']==sum(r['net_margin_paise'] for r in report['by_bin'])
    monkeypatch.setenv('SYNTHETIC_EARNED_FEE_BPS','500')
    assert profit_summary(ledger)['totals']==report['totals']
    results=fee_audit(ledger)
    assert any(f['issue']=='SHORT_SETTLEMENT' for r in results for f in r['findings'])
    assert any(f['issue']=='FEE_MISMATCH' for r in results for f in r['findings'])
    persist(results,ledger)
    assert all(r['tier']=='EXPERT_QUEUE' and not r['claim_filed'] for r in queue(ledger))


@pytest.mark.parametrize('language',['en','hi','ta'])
def test_margin_explanation_uses_approved_facts(ledger,language):
    r=chat('SYN-M001','Explain profit margin fees',language,path=ledger)
    assert r['grounded']
    for value in r['facts'].values():assert str((Decimal(value)/100).quantize(Decimal('.01'))) in r['text']


def test_profit_and_agent_api(ledger):
    from backend.main import app
    with TestClient(app) as c:
        assert c.get('/api/profit').json()['synthetic']
        assert c.post('/api/fee-audit/run').json()['created']>0
