"""Persist agent predictions and queue tiers in the same transaction as audit."""
from __future__ import annotations

import json
from backend import audit
from backend.decision import Decision, Policy
from backend.ledger import connect, utcnow


def save_result(conn, result: dict) -> bool:
    decision=Decision.model_validate(result['decision'])
    # All agents must cite real operational rows; no opaque model citations.
    available={result['transaction_id']}
    for table in ('transactions','settlements','refunds','fees','disputes'):
        if table=='transactions':continue
        available.update(row[0] for row in conn.execute(f'SELECT id FROM {table} WHERE transaction_id=?',
                                                       (result['transaction_id'],)))
    # Reference-only settlements have no FK yet; verify them using the matcher.
    from backend.reconciliation import match
    tx_row=conn.execute('SELECT * FROM transactions WHERE id=?',(result['transaction_id'],)).fetchone()
    if tx_row:
        matched,_,_=match(dict(tx_row),[dict(r) for r in conn.execute('SELECT * FROM settlements')])
        available.update(r['id'] for r in matched)
    if (not set(decision.evidence)<=available or result['transaction_id'] not in decision.evidence or
            len(set(decision.evidence))!=len(decision.evidence)):
        raise ValueError('Agent cited nonexistent, unrelated or duplicate evidence')
    tx=conn.execute('SELECT amount_paise FROM transactions WHERE id=?',(result['transaction_id'],)).fetchone()
    if not tx or decision.amount*100 != tx[0]:
        raise ValueError('Decision amount must equal ledger transaction amount')
    if conn.execute('SELECT 1 FROM agent_decisions WHERE case_id=?',(decision.case_id,)).fetchone():
        return False
    from backend.feedback import latest, calibrated
    model=latest(conn)
    result=dict(result)
    if model:
        result['raw_confidence']=decision.confidence
        decision=decision.model_copy(update={'confidence':calibrated(decision.confidence,model)})
        result['decision']=decision.model_dump(mode='json')
        result['calibration_feedback_count']=model['feedback_count']
    tier=Policy.configured().gate(decision)
    policy=Policy.configured()
    snapshot={'auto':policy.auto,'review':policy.review,'high_value':str(policy.high_value),'write_off':str(policy.write_off)}
    previous=conn.execute("SELECT payload FROM model_registry WHERE name='review_policy' ORDER BY id DESC LIMIT 1").fetchone()
    if previous is None or json.loads(previous[0])!=snapshot:
        conn.execute('INSERT INTO model_registry(name,payload,created_at) VALUES(?,?,?)',
                     ('review_policy',json.dumps(snapshot),utcnow()))
        audit.append(conn,'POLICY_SNAPSHOT','review_policy',{'policy':snapshot,
                     'source':'operator environment configuration; application cannot auto-change policy'})
    now=utcnow()
    conn.execute('INSERT INTO agent_decisions VALUES(?,?,?,?,?)',
                 (decision.case_id,result['agent'],result['transaction_id'],json.dumps(result),now))
    conn.execute('INSERT INTO review_queue VALUES(?,?,?,?,?)',
                 (decision.case_id,tier,'AUTO_RESOLVED' if tier=='AUTO_RESOLVED' else 'OPEN',1,now))
    audit.append(conn,'AGENT_DECISION',decision.case_id,{**result,'tier':tier})
    return True


def persist(results: list[dict], path=None) -> int:
    with connect(path) as conn:
        conn.execute('BEGIN IMMEDIATE')
        return sum(save_result(conn,r) for r in results)


def queue(path=None) -> list[dict]:
    with connect(path) as conn:
        rows=conn.execute('SELECT d.*,q.tier,q.status,q.version,q.updated_at FROM agent_decisions d '
                          'JOIN review_queue q USING(case_id) ORDER BY d.created_at,d.case_id').fetchall()
        results=[]
        for r in rows:
            result=json.loads(r['payload'])|{k:r[k] for k in ('tier','status','version','created_at','updated_at')}
            correction=conn.execute('SELECT corrected FROM human_feedback WHERE case_id=? ORDER BY id DESC LIMIT 1',
                                    (r['case_id'],)).fetchone()
            result['effective_decision']=json.loads(correction[0]) if correction else result['decision']
            restriction=conn.execute('SELECT suggested,approved FROM fraud_alerts WHERE case_id=?',(r['case_id'],)).fetchone()
            if restriction:result['restriction']=dict(restriction)
            results.append(result)
        return results


def review_case(case_id: str, action: str, *, version: int, comment: str = '',
                corrected_action: str | None = None, path=None) -> dict:
    if action not in {'APPROVE','REJECT','EDIT'}:
        raise ValueError('Unsupported review action')
    with connect(path) as conn:
        conn.execute('BEGIN IMMEDIATE')
        row=conn.execute('SELECT d.payload,q.status,q.version FROM agent_decisions d '
                         'JOIN review_queue q USING(case_id) WHERE case_id=?',(case_id,)).fetchone()
        if not row:
            raise LookupError('Case not found')
        if row['status']!='OPEN' or row['version']!=version:
            raise ValueError('Case already reviewed or stale version')
        original=json.loads(row['payload'])
        corrected=None
        if action=='EDIT':
            if not comment.strip() or not corrected_action:
                raise ValueError('Correction action and reason are required')
            corrected=Decision.model_validate(original['decision']|{'action':corrected_action}).model_dump(mode='json')
            conn.execute('INSERT INTO human_feedback(case_id,original,corrected,reason,features,created_at) VALUES(?,?,?,?,?,?)',
                         (case_id,json.dumps(original['decision']),json.dumps(corrected),comment,
                          json.dumps(original.get('features',[])),utcnow()))
        conn.execute('INSERT INTO human_approvals(case_id,decision,comment,created_at) VALUES(?,?,?,?)',
                     (case_id,action,comment,utcnow()))
        status={'APPROVE':'APPROVED','REJECT':'REJECTED','EDIT':'EDITED'}[action]
        if original['agent']=='dispute':
            conn.execute('UPDATE disputes SET status=? WHERE transaction_id=?',('REVIEWED',original['transaction_id']))
        conn.execute('UPDATE review_queue SET status=?,version=version+1,updated_at=? WHERE case_id=?',
                     (status,utcnow(),case_id))
        audit.append(conn,'HUMAN_'+action,case_id,{'original_prediction':original['decision'],
                     'corrected_decision':corrected,'comment':comment,'payment_executed':False})
        return {'case_id':case_id,'status':status,'version':version+1,'payment_executed':False}


def kill_switch(case_id: str, *, approve: bool, confirmed: bool = False, path=None) -> dict:
    with connect(path) as conn:
        conn.execute('BEGIN IMMEDIATE')
        row=conn.execute('SELECT * FROM fraud_alerts WHERE case_id=?',(case_id,)).fetchone()
        if not row:
            raise LookupError('Fraud alert not found')
        if approve:
            if not confirmed or not row['suggested'] or row['approved']:
                raise ValueError('Explicit human confirmation of a pending suggestion is required')
            conn.execute('UPDATE fraud_alerts SET approved=1 WHERE case_id=?',(case_id,))
        else:
            if row['suggested']:
                raise ValueError('Kill-switch suggestion already exists')
            conn.execute('UPDATE fraud_alerts SET suggested=1 WHERE case_id=?',(case_id,))
        audit.append(conn,'KILL_SWITCH_APPROVED' if approve else 'KILL_SWITCH_SUGGESTED',case_id,
                     {'human_confirmed':confirmed if approve else False,'processing_disabled':False,
                      'note':'Approval records a recommendation only; no payment-network connector exists.'})
        return {'case_id':case_id,'suggested':True,'approved':approve,'processing_disabled':False}
