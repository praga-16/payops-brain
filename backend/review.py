"""Persist agent predictions and queue tiers in the same transaction as audit."""
from __future__ import annotations

import json
from backend import audit
from backend.decision import Decision, Policy
from backend.ledger import connect, utcnow


def save_result(conn, result: dict) -> bool:
    decision=Decision.model_validate(result['decision'])
    # All agents must cite real operational rows; no opaque model citations.
    available=set()
    for table in ('transactions','settlements','refunds','fees','disputes'):
        available.update(row[0] for row in conn.execute(f'SELECT id FROM {table}'))
    if not set(decision.evidence)<=available:
        raise ValueError('Agent cited nonexistent evidence')
    tx=conn.execute('SELECT amount_paise FROM transactions WHERE id=?',(result['transaction_id'],)).fetchone()
    if not tx or decision.amount*100 != tx[0]:
        raise ValueError('Decision amount must equal ledger transaction amount')
    if conn.execute('SELECT 1 FROM agent_decisions WHERE case_id=?',(decision.case_id,)).fetchone():
        return False
    tier=Policy.configured().gate(decision)
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
        return [json.loads(r['payload'])|{k:r[k] for k in ('tier','status','version','created_at','updated_at')}
                for r in rows]
