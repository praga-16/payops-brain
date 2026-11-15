from fastapi.testclient import TestClient
from backend.simulator import seed
from backend.review import persist,review_case,queue
from backend.earned_autonomy import assess,history
from backend.ledger import connect,money,records
from backend import audit


def test_human_approval_and_safer_rollback(tmp_path,monkeypatch):
    p=tmp_path/'db';monkeypatch.setenv('PAYOPS_DB',str(p));monkeypatch.setenv('AUTONOMY_MIN_REVIEWS','4');monkeypatch.setenv('AUTONOMY_QUALITY_FLOOR','.5')
    seed(32,90,p);tx=records('transactions',p)[9]
    def reviewed(index,action):
        cid='QUALITY-'+str(index)
        persist([{'agent':'reconciliation','break_type':'CLEAN','transaction_id':tx['id'],'decision':{
            'case_id':cid,'action':'RECONCILE','confidence':.8,'reasoning':'synthetic analyst sample',
            'evidence':[tx['id']],'amount':money(tx['amount_paise'])}}],p)
        review_case(cid,action,version=1,path=p)
    for i in range(4):reviewed(i,'APPROVE')
    result=assess(p)
    proposal=next(r for r in queue(p) if r['agent']=='autonomy' and r['proposal']['case_type']=='CLEAN')
    assert proposal['tier']=='EXPERT_QUEUE'
    assert not history(p)['limits']
    review_case(proposal['decision']['case_id'],'APPROVE',version=1,path=p)
    assert next(r for r in history(p)['limits'] if r['case_type']=='CLEAN')['threshold']==.94
    for i in range(4,9):reviewed(i,'REJECT')
    assert next(r for r in history(p)['limits'] if r['case_type']=='CLEAN')['threshold']==.99
    assert any(r['event']=='AUTONOMY_ROLLBACK' for r in history(p)['history'])
    assert assess(p)['rollbacks']==0  # Already rolled back automatically by the review monitor.
    with connect(p) as c:assert audit.verify(c)['valid']
    from backend.main import app
    with TestClient(app) as c:
        assert c.get('/api/autonomy/ramp').json()['synthetic']
        assert c.post('/api/autonomy/assess').status_code==200
