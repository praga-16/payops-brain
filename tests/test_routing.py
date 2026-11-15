from fastapi.testclient import TestClient
from backend.simulator import seed
from backend.routing import routing_report,bin_report
from backend.review import persist,queue,review_case
from backend.ledger import connect
from backend import audit


def test_outage_bandit_has_bounded_human_only_uplift(tmp_path,monkeypatch):
    p=tmp_path/'db';monkeypatch.setenv('PAYOPS_DB',str(p));seed(32,80,p,scenario='upi-bank-outage')
    result=routing_report(p)
    proposals=[r for r in result['proposals'] if r['context']['outage']]
    assert proposals and all(0<r['maximum_shift']<=.10 and r['simulated_success_uplift']>0 for r in proposals)
    assert all(min(r['sample_sizes'].values())>=30 for r in proposals)
    persist(proposals,p)
    assert all(r['tier']=='EXPERT_QUEUE' and not r['routing_executed'] for r in queue(p))
    review_case(proposals[0]['decision']['case_id'],'APPROVE',version=1,path=p)
    assert routing_report(p)['contexts']==result['contexts']
    with connect(p) as c:assert audit.verify(c)['valid']
    from backend.main import app
    with TestClient(app) as c:
        assert c.get('/api/bin-intelligence').json()['synthetic']
        assert c.get('/api/routing').json()['proposals']
        assert not c.post('/api/routing/suggest').json()['routing_executed']
    monkeypatch.setenv('ROUTING_MIN_SAMPLES','100000')
    assert not routing_report(p)['proposals']


def test_bin_outlier_test_shows_sample_size(tmp_path):
    p=tmp_path/'db';seed(512,81,p)
    with connect(p) as c:
        c.execute("UPDATE lifecycle_events SET status='DECLINED' WHERE stage='AUTHORIZATION' AND transaction_id IN (SELECT transaction_id FROM payment_details WHERE issuer='SYN-ISSUER-00')")
        c.execute("UPDATE payment_details SET decline_reason='SYN_BANK_TIMEOUT' WHERE issuer='SYN-ISSUER-00'")
    report=bin_report(p)
    assert all(r['sample_size']>0 for r in report['groups'])
    assert any(r['low_success_outlier'] for r in report['groups'])
    assert any(r['top_decline_reasons'].get('SYN_BANK_TIMEOUT') for r in report['groups'])
