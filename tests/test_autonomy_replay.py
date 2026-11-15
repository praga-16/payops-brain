import os
import pytest
from fastapi.testclient import TestClient
from backend.autonomy_replay import replay,holdout
from backend.decision import Decision,Policy
from backend.simulator import seed
from backend.ledger import connect


def test_replay_is_read_only_and_restricted_actions_never_auto(tmp_path,monkeypatch):
    p=tmp_path/'db';monkeypatch.setenv('PAYOPS_DB',str(p));seed(16,50,p)
    with connect(p) as c:before=[tuple(r) for r in c.execute('SELECT * FROM audit_events')]
    result=replay(.70)
    assert result['case_count']==608 and result['transaction_count']==512
    assert not result['stored_thresholds_changed']
    with connect(p) as c:assert before==[tuple(r) for r in c.execute('SELECT * FROM audit_events')]
    assert all(r['false_auto_resolutions']==0 for r in result['curve'])
    assert result['curve'][0]['auto_resolved']>=result['curve'][-1]['auto_resolved']
    for action in ('KILL_SWITCH','ARBITRATION','RAISE_CLAIM','WRITE_OFF','REFUND_REVIEW','POLICY_CHANGE'):
        d=Decision(action=action,confidence=1,reasoning='test',evidence=['t'],amount='100',case_id='c')
        assert Policy(auto=.7).gate(d)!='AUTO_RESOLVED'
    from backend.main import app
    with TestClient(app) as c:
        assert c.get('/api/autonomy/replay?threshold=.83').json()['selected']['threshold']==.83
        assert c.get('/api/autonomy/replay?threshold=.69').status_code==422
