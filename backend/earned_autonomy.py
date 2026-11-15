"""Measured type-level policy proposals; automatic changes only reduce autonomy."""
from __future__ import annotations

from collections import defaultdict
import json
import os

from backend import audit
from backend.decision import Decision,Policy
from backend.evaluation import wilson
from backend.ledger import connect,records,money,utcnow


def ensure(conn) -> None:
    conn.executescript('''CREATE TABLE IF NOT EXISTS autonomy_limits(
        case_type TEXT PRIMARY KEY,threshold REAL NOT NULL CHECK(threshold BETWEEN .70 AND .99),
        human_approved INTEGER NOT NULL,updated_at TEXT NOT NULL);
        INSERT OR IGNORE INTO schema_version VALUES(7);''')


def case_type(result: dict) -> str:
    return result.get('break_type') or {'dispute':'CHARGEBACK','fraud':'FRAUD_ALERT'}.get(result['agent'],result['agent'])


def threshold_for(conn,kind: str,default: float) -> float:
    row=conn.execute('SELECT threshold FROM autonomy_limits WHERE case_type=?',(kind,)).fetchone()
    return row[0] if row else default


def quality(path=None) -> list[dict]:
    from backend.autonomy_replay import holdout
    measured=defaultdict(lambda:{'holdout_correct':0,'holdout_samples':0,'review_correct':0,'review_samples':0})
    for _,kind,correct,_ in holdout():
        measured[kind]['holdout_samples']+=1;measured[kind]['holdout_correct']+=int(correct)
    with connect(path) as c:
        rows=c.execute('SELECT a.decision,d.payload,a.case_id FROM human_approvals a JOIN agent_decisions d USING(case_id) ORDER BY a.id').fetchall()
        latest={r['case_id']:r for r in rows}
        for row in latest.values():
            result=json.loads(row['payload']);kind=case_type(result)
            correct=row['decision']=='APPROVE'
            if row['decision']=='EDIT':
                corrected=c.execute('SELECT corrected FROM human_feedback WHERE case_id=? ORDER BY id DESC LIMIT 1',(row['case_id'],)).fetchone()
                correct=corrected is not None and json.loads(corrected[0])['action']==result['decision']['action']
            measured[kind]['review_samples']+=1;measured[kind]['review_correct']+=int(correct)
        for kind,r in measured.items():
            r.update(case_type=kind,current_threshold=threshold_for(c,kind,Policy.configured().auto))
            for scope in ('holdout','review'):
                n=r[scope+'_samples'];k=r[scope+'_correct']
                r[scope+'_accuracy']=k/n if n else None
                r[scope+'_95_wilson']=wilson(k,n)
    return list(measured.values())


def assess(path=None) -> dict:
    from backend.review import save_result
    floor=float(os.getenv('AUTONOMY_QUALITY_FLOOR') or '.95')
    minimum=int(os.getenv('AUTONOMY_MIN_REVIEWS') or '20')
    if not .5<=floor<1 or minimum<1:raise ValueError('Autonomy quality floor must be .5..<1 and minimum reviews >=1')
    measurements=quality(path);txs=records('transactions',path)
    if not txs:return {'synthetic':True,'measurements':measurements,'created':0,'rollbacks':0,'quality_floor':floor,'minimum_reviews':minimum}
    tx=txs[0];created=rollbacks=0
    with connect(path) as c:
        c.execute('BEGIN IMMEDIATE')
        for r in measurements:
            kind=r['case_type'];current=threshold_for(c,kind,Policy.configured().auto)
            bad=(r['review_samples']>=minimum and r['review_accuracy']<floor or
                 r['holdout_samples']>=20 and r['holdout_accuracy']<floor)
            active=c.execute('SELECT human_approved FROM autonomy_limits WHERE case_type=?',(kind,)).fetchone()
            if bad and active and active[0] and current<.99:
                c.execute('UPDATE autonomy_limits SET threshold=.99,updated_at=? WHERE case_type=?',(utcnow(),kind))
                audit.append(c,'AUTONOMY_ROLLBACK',kind,{'from_threshold':current,'to_threshold':.99,
                             'basis':r,'quality_floor':floor,'direction':'safer: higher confidence required; no financial action'})
                rollbacks+=1
                continue
            enough=(r['review_samples']>=minimum and r['holdout_samples']>=20 and
                    r['review_95_wilson'][0]>=floor and r['holdout_95_wilson'][0]>=floor)
            if bad and current<.99:proposed=.99
            elif enough and kind=='CLEAN' and current>.70:proposed=round(max(.70,current-.01),2)
            else:continue
            result={'agent':'autonomy','transaction_id':tx['id'],
                    'proposal':{'case_type':kind,'expected_threshold':current,'proposed_threshold':proposed,
                                'quality_floor':floor,'basis':r},'provider':'local measured review + synthetic holdout quality',
                    'features':[r['review_samples'],r['holdout_samples']], 'payment_executed':False}
            d=Decision(action='POLICY_CHANGE',confidence=min(.99,r['holdout_accuracy'] or .5),
                       reasoning='Measured type-level autonomy threshold proposal. Human approval required. '
                       'Amount is an example ledger transaction, not a policy transfer amount.',
                       evidence=[tx['id']],amount=money(tx['amount_paise']),
                       case_id=f'AUTO-{kind}-{current}-{proposed}-{r["review_samples"]}-{r["review_correct"]}')
            result['decision']=d.model_dump(mode='json')
            created+=int(save_result(c,result))
        audit.append(c,'AUTONOMY_ASSESSED','autonomy-ramp',{'created':created,'safer_rollbacks':rollbacks,'quality_floor':floor})
    return {'synthetic':True,'measurements':measurements,'created':created,'rollbacks':rollbacks,
            'quality_floor':floor,'minimum_reviews':minimum,'note':'Lower thresholds increase autonomy. Only CLEAN bookkeeping can become automatic. Restricted actions stay human-only.'}


def apply_approved(conn,result: dict) -> None:
    proposal=result['proposal'];kind=proposal['case_type']
    current=threshold_for(conn,kind,Policy.configured().auto)
    if abs(current-proposal['expected_threshold'])>1e-9:raise ValueError('Stale autonomy proposal; reassess current quality')
    new=proposal['proposed_threshold']
    if not .70<=new<=.99:raise ValueError('Invalid autonomy limit')
    conn.execute('INSERT INTO autonomy_limits VALUES(?,?,1,?) ON CONFLICT(case_type) DO UPDATE SET '
                 'threshold=excluded.threshold,human_approved=1,updated_at=excluded.updated_at',(kind,new,utcnow()))
    audit.append(conn,'AUTONOMY_LIMIT_APPROVED',result['decision']['case_id'],
                 {'case_type':kind,'old_threshold':current,'new_threshold':new,'proposal':proposal,'financial_action_executed':False})


def monitor_quality(path=None) -> int:
    """Review/evaluation-triggered rollback, never an automatic increase."""
    with connect(path) as c:
        if not c.execute('SELECT 1 FROM autonomy_limits WHERE human_approved=1 AND threshold<.99').fetchone():return 0
    measurements=quality(path)
    floor=float(os.getenv('AUTONOMY_QUALITY_FLOOR') or '.95');minimum=int(os.getenv('AUTONOMY_MIN_REVIEWS') or '20')
    count=0
    with connect(path) as c:
        c.execute('BEGIN IMMEDIATE')
        for r in measurements:
            active=c.execute('SELECT * FROM autonomy_limits WHERE case_type=?',(r['case_type'],)).fetchone()
            bad=(r['review_samples']>=minimum and r['review_accuracy']<floor or r['holdout_samples']>=20 and r['holdout_accuracy']<floor)
            if active and active['human_approved'] and active['threshold']<.99 and bad:
                c.execute('UPDATE autonomy_limits SET threshold=.99,updated_at=? WHERE case_type=?',(utcnow(),r['case_type']))
                audit.append(c,'AUTONOMY_ROLLBACK',r['case_type'],{'from_threshold':active['threshold'],'to_threshold':.99,
                             'basis':r,'trigger':'review/evaluation quality monitor','direction':'safer only'})
                count+=1
    return count


def history(path=None) -> dict:
    measurements=quality(path)
    with connect(path) as c:
        return {'synthetic':True,'measurements':measurements,
                'limits':[dict(r) for r in c.execute('SELECT * FROM autonomy_limits ORDER BY case_type')],
                'history':[dict(r)|{'payload':json.loads(r['payload'])} for r in c.execute("SELECT * FROM audit_events WHERE event LIKE 'AUTONOMY_%' ORDER BY id DESC LIMIT 50")],
                'note':'Review agreement is a noisy analyst label, not proof of financial correctness. Holdout outcomes share synthetic assumptions. No automatic increase in autonomy.'}
