import sqlite3
from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend import audit
from backend.decision import Decision, Policy
from backend.ledger import connect, initialize, money, records
from backend.simulator import seed


def decision(**updates):
    return Decision(**({'action': 'RECONCILE', 'confidence': .95, 'reasoning': 'Matched evidence',
                        'evidence': ['T1'], 'amount': '100.00', 'case_id': 'C1'} | updates))


@pytest.mark.parametrize('score,tier', [(.6999,'EXPERT_QUEUE'),(.7,'ONE_CLICK_REVIEW'),
                                       (.9499,'ONE_CLICK_REVIEW'),(.95,'AUTO_RESOLVED'),(1,'AUTO_RESOLVED')])
def test_confidence_boundaries(score, tier):
    assert Policy().gate(decision(confidence=score)) == tier


@pytest.mark.parametrize('action', ['KILL_SWITCH','ARBITRATION','POLICY_CHANGE','RESTRICT_PAYMENTS'])
def test_mandatory_approval(action):
    assert Policy().gate(decision(action=action, confidence=1)) == 'EXPERT_QUEUE'


def test_high_value_and_write_off():
    assert Policy().gate(decision(amount='50000')) == 'EXPERT_QUEUE'
    assert Policy().gate(decision(action='WRITE_OFF',amount='5000')) == 'ONE_CLICK_REVIEW'
    assert Policy().gate(decision(action='WRITE_OFF',amount='5000.01')) == 'EXPERT_QUEUE'
    assert Policy().gate(decision(action='FIGHT', confidence=1)) == 'ONE_CLICK_REVIEW'


def test_contract_validation(monkeypatch):
    for update in ({'confidence': 1.01}, {'confidence': float('nan')}, {'amount':'-1'},
                   {'evidence':[]}, {'action':'EXECUTE_PAYMENT'}):
        with pytest.raises(ValidationError):
            decision(**update)
    monkeypatch.setenv('AUTO_RESOLVE_THRESHOLD','.99')
    assert Policy.configured().gate(decision()) == 'ONE_CLICK_REVIEW'
    with pytest.raises(ValueError):
        Policy(auto=.5, review=.7)
    assert money(31) == '0.31'


def test_audit_integrity_and_sql_guards(tmp_path):
    path = tmp_path/'ledger.db'
    initialize(path)
    with connect(path) as conn:
        audit.append(conn,'DECISION','C1',{'action':'FIGHT'})
        audit.append(conn,'APPROVAL','C1',{'approved':True})
        assert audit.verify(conn)['checked'] == 2
        for sql in ('UPDATE audit_events SET event="bad"','DELETE FROM audit_events'):
            with pytest.raises(sqlite3.IntegrityError, match='append-only'):
                conn.execute(sql)
        assert audit.verify(conn)['valid']
        conn.execute('DROP TRIGGER audit_no_update')
        conn.execute('UPDATE audit_events SET payload=? WHERE id=1', ('{}',))
        assert not audit.verify(conn)['valid']


def test_simulator_reproducible_and_labels_isolated(tmp_path):
    a,b=tmp_path/'a.db',tmp_path/'b.db'
    assert seed(160,42,a)['created']
    assert not seed(160,42,a)['created']
    seed(160,42,b)
    assert records('transactions',a) == records('transactions',b)
    assert len(records('transactions',a)) == 160
    assert {r['rail'] for r in records('transactions',a)} == {'CARD','UPI','NET_BANKING'}
    with pytest.raises(ValueError):
        records('ground_truth_labels',a)
    with connect(a) as conn:
        assert not conn.execute("SELECT name FROM sqlite_master WHERE name='ground_truth_labels'").fetchone()
        assert conn.execute('PRAGMA foreign_key_check').fetchall() == []
        assert audit.verify(conn)['valid']


@pytest.mark.parametrize('slot',range(7))
def test_each_injected_anomaly(tmp_path,slot):
    path=tmp_path/'ledger.db'
    seed(32,42,path)
    tid=f'SIM-42-32-T{slot:05}'
    with connect(path) as c:
        t=c.execute('SELECT * FROM transactions WHERE id=?',(tid,)).fetchone()
        settlements=c.execute('SELECT * FROM settlements WHERE transaction_id=? OR reference=?',(tid,tid.lower().replace('-',''))).fetchall()
        if slot==0: assert not settlements
        if slot==1: assert settlements[0]['amount_paise'] < t['amount_paise']-t['fee_paise']
        if slot==2: assert len(settlements)==2
        if slot==3: assert c.execute('SELECT amount_paise FROM refunds WHERE transaction_id=?',(tid,)).fetchone()[0]>t['amount_paise']
        if slot==4: assert c.execute('SELECT amount_paise FROM fees WHERE transaction_id=?',(tid,)).fetchone()[0]!=t['fee_paise']
        if slot==5: assert c.execute('SELECT reason_code FROM disputes WHERE transaction_id=?',(tid,)).fetchone()[0]=='UPI_UNAUTHORIZED'
        if slot==6: assert t['device_risk']>.85
