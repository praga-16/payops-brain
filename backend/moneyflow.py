"""Additive synthetic lifecycle snapshots and fee-adjusted three-way checks."""
from __future__ import annotations

from datetime import datetime, timedelta
import hashlib

from backend.ledger import connect, records
from backend.reconciliation import match, classify

SCHEMA = """
CREATE TABLE IF NOT EXISTS lifecycle_events(
 id TEXT PRIMARY KEY, transaction_id TEXT NOT NULL REFERENCES transactions(id),
 stage TEXT NOT NULL CHECK(stage IN ('AUTHORIZATION','CLEARING')),
 amount_paise INTEGER NOT NULL CHECK(amount_paise>=0), occurred_at TEXT NOT NULL,
 status TEXT NOT NULL, source TEXT NOT NULL, UNIQUE(transaction_id,stage));
CREATE INDEX IF NOT EXISTS lifecycle_transaction ON lifecycle_events(transaction_id);
CREATE TABLE IF NOT EXISTS payment_details(
 transaction_id TEXT PRIMARY KEY REFERENCES transactions(id), bin TEXT NOT NULL,
 issuer TEXT NOT NULL, card_token TEXT NOT NULL, decline_reason TEXT);
INSERT OR IGNORE INTO schema_version VALUES(2);
"""


def backfill(path=None) -> None:
    with connect(path) as conn:
        conn.executescript(SCHEMA)
        for row in conn.execute('SELECT * FROM transactions').fetchall():
            tx=dict(row)
            for stage,delay in [('AUTHORIZATION',0),('CLEARING',30)]:
                conn.execute('INSERT OR IGNORE INTO lifecycle_events VALUES(?,?,?,?,?,?,?)',
                             (tx['id']+'-'+stage,tx['id'],stage,tx['amount_paise'],
                              (datetime.fromisoformat(tx['created_at'])+timedelta(minutes=delay)).isoformat(),
                              'APPROVED' if stage=='AUTHORIZATION' else 'CLEARED',
                              'synthetic snapshot inferred from captured ledger; not external telemetry'))
            digest=hashlib.sha256(tx['id'].encode()).hexdigest()
            bucket=int(digest[:2],16)%4
            conn.execute('INSERT OR IGNORE INTO payment_details VALUES(?,?,?,?,?)',
                         (tx['id'],f'SYN-BIN-{bucket:02}' if tx['rail']=='CARD' else 'N/A',
                          f'SYN-ISSUER-{bucket:02}', 'tok_syn_'+digest[:12] if tx['rail']=='CARD' else '',None))
        from backend.margins import snapshot
        snapshot(conn)
        from backend.impact import ensure
        ensure(conn)


def flow(transaction_id: str, path=None) -> dict:
    tx=next((t for t in records('transactions',path) if t['id']==transaction_id),None)
    if tx is None:raise LookupError('Synthetic transaction not found')
    with connect(path) as conn:
        events=[dict(r) for r in conn.execute('SELECT * FROM lifecycle_events WHERE transaction_id=? ORDER BY occurred_at,stage',(transaction_id,))]
    matched,method,_=match(tx,records('settlements',path))
    refunds=[r for r in records('refunds',path) if r['transaction_id']==transaction_id]
    fees=[r for r in records('fees',path) if r['transaction_id']==transaction_id]
    disputes=[r for r in records('disputes',path) if r['transaction_id']==transaction_id]
    authorization=next((e['amount_paise'] for e in events if e['stage']=='AUTHORIZATION'),None)
    clearing=next((e['amount_paise'] for e in events if e['stage']=='CLEARING'),None)
    settled=sum(s['amount_paise'] for s in matched)
    expected=max(0,clearing-tx['fee_paise']) if clearing is not None else None
    gap=None if expected is None else expected-settled
    kind=classify(tx,matched,refunds,fees,disputes)
    for s in matched:
        events.append({'id':s['id'],'stage':'SETTLEMENT','amount_paise':s['amount_paise'],
                       'occurred_at':s['settled_at'],'status':s['status'],'source':'settlement ledger'})
    if not matched:
        events.append({'id':None,'stage':'SETTLEMENT','amount_paise':0,'occurred_at':None,'status':'MISSING','source':'no matched ledger row'})
    for r in refunds:
        events.append({'id':r['id'],'stage':'REFUND','amount_paise':r['amount_paise'],
                       'occurred_at':r['created_at'],'status':'RECORDED','source':'refund ledger'})
    for d in disputes:
        events.append({'id':d['id'],'stage':'DISPUTE','amount_paise':tx['amount_paise'],
                       'occurred_at':d['opened_at'],'status':d['status'],'source':'dispute ledger'})
    order={'AUTHORIZATION':0,'CLEARING':1,'SETTLEMENT':2,'REFUND':3,'DISPUTE':4}
    events.sort(key=lambda e:(order[e['stage']],e['occurred_at'] or ''))
    return {'synthetic':True,'transaction_id':transaction_id,'merchant_id':tx['merchant_id'],'rail':tx['rail'],
            'stages':events,'authorization_paise':authorization,'clearing_paise':clearing,
            'settlement_paise':settled,'expected_settlement_paise':expected,'expected_fee_paise':tx['fee_paise'],
            'authorization_clearing_gap_paise':None if authorization is None or clearing is None else authorization-clearing,
            'clearing_settlement_gap_paise':gap,'stuck_paise':max(0,gap or 0),
            'excess_settlement_paise':max(0,-(gap or 0)),'likely_cause':kind,'match_method':method,
            'note':'Settlement is net of expected fee; a pending gap is exposure, not a realized loss.'}


def flow_summary(path=None) -> dict:
    items=[flow(t['id'],path) for t in records('transactions',path)]
    def group(key):
        grouped={}
        for item in items:
            r=grouped.setdefault(item[key],{'key':item[key],'count':0,'stuck_paise':0,'excess_settlement_paise':0})
            r['count']+=1
            r['stuck_paise']+=item['stuck_paise'];r['excess_settlement_paise']+=item['excess_settlement_paise']
        return list(grouped.values())
    return {'synthetic':True,'transaction_count':len(items),'by_rail':group('rail'),'by_merchant':group('merchant_id'),
            'stuck_paise':sum(i['stuck_paise'] for i in items),'excess_settlement_paise':sum(i['excess_settlement_paise'] for i in items),
            'realized_loss_paise':None,'note':'No realized-loss entries exist. Authorization/clearing snapshots are explicitly synthetic inferred history.'}
