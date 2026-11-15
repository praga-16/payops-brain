import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from backend.ledger import initialize,connect
from backend.simulator import seed
from backend.reconciliation import analyze
from backend.fraud import analyze as fraud, persist_alerts
from backend.review import persist,queue,review_case,kill_switch
from backend.feedback import recalibrate
from backend import audit


@pytest.fixture
def populated(tmp_path,monkeypatch):
    path=tmp_path/'ledger.db';monkeypatch.setenv('PAYOPS_DB',str(path))
    seed(32,42,path);persist(analyze(path),path)
    return path


def test_review_preserves_original_and_correction(populated):
    path=populated
    case=next(c for c in queue(path) if c['status']=='OPEN')
    cid=case['decision']['case_id']
    with pytest.raises(ValueError):review_case(cid,'EDIT',version=1,path=path)
    result=review_case(cid,'EDIT',version=1,comment='Evidence needs further review',corrected_action='NO_ACTION',path=path)
    assert result['status']=='EDITED'
    saved=next(c for c in queue(path) if c['decision']['case_id']==cid)
    assert saved['decision']==case['decision']
    assert saved['effective_decision']['action']=='NO_ACTION'
    with pytest.raises(ValueError):review_case(cid,'APPROVE',version=1,path=path)
    with connect(path) as conn:
        row=conn.execute('SELECT * FROM human_feedback').fetchone()
        assert json.loads(row['original'])==case['decision'] and row['reason']
        assert audit.verify(conn)['valid']


def test_calibration_measures_holdout_and_review_estimates(populated):
    path=populated
    assert not recalibrate(path)['trained']
    for case in [c for c in queue(path) if c['status']=='OPEN'][:3]:
        review_case(case['decision']['case_id'],'EDIT',version=1,comment='Synthetic analyst correction',
                    corrected_action='NO_ACTION',path=path)
    result=recalibrate(path)
    assert result['trained'] and result['feedback_count']==3
    assert 0<=result['brier_before']<=1 and 0<=result['brier_after']<=1
    assert result['estimate_case_count']==32


def test_simultaneous_review_only_one_succeeds(populated):
    cid=next(c for c in queue(populated) if c['status']=='OPEN')['decision']['case_id']
    def approve():
        try:return review_case(cid,'APPROVE',version=1,path=populated)['status']
        except ValueError:return 'CONFLICT'
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _:approve(),range(2)))==['APPROVED','CONFLICT']


def test_kill_switch_explicit_approval_only(populated):
    alerts=fraud(populated);persist_alerts(alerts,populated)
    cid=alerts[0]['decision']['case_id']
    with pytest.raises(ValueError):kill_switch(cid,approve=True,confirmed=True,path=populated)
    suggestion=kill_switch(cid,approve=False,path=populated)
    assert not suggestion['approved']
    with pytest.raises(ValueError):kill_switch(cid,approve=True,path=populated)
    approved=kill_switch(cid,approve=True,confirmed=True,path=populated)
    assert approved['approved'] and not approved['processing_disabled']


def test_review_routes(populated):
    from backend.main import app
    with TestClient(app) as client:
        rows=client.get('/api/review-queue').json()
        case=next(r for r in rows if r['status']=='OPEN');cid=case['decision']['case_id']
        assert client.get('/api/review-queue/'+cid).status_code==200
        assert client.post('/api/review-queue/'+cid+'/reject',json={'version':1}).status_code==200
        assert client.post('/api/review-queue/'+cid+'/approve',json={'version':1}).status_code==409
        assert client.get('/api/review-queue/missing').status_code==404
        assert client.get('/api/audit').json()['integrity']['valid']
