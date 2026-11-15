"""Synthetic pricing snapshots, margin attribution and fee-audit decisions."""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
import os
import statistics

from backend.decision import Decision
from backend.ledger import connect,records,money
from backend.moneyflow import flow,flow_data


def rates() -> dict:
    result={'earned_bps':int(os.getenv('SYNTHETIC_EARNED_FEE_BPS') or '250'),
            'paid_bps':int(os.getenv('SYNTHETIC_PAID_FEE_BPS') or '200')}
    if any(not 0<=v<=10000 for v in result.values()):raise ValueError('Synthetic fee rates must be 0..10000 basis points')
    return result


def snapshot(conn) -> None:
    conn.executescript('''CREATE TABLE IF NOT EXISTS pricing_contracts(
        transaction_id TEXT PRIMARY KEY REFERENCES transactions(id), earned_bps INTEGER NOT NULL,
        paid_bps INTEGER NOT NULL, earned_paise INTEGER NOT NULL, expected_paid_paise INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS dispute_loss_records(
        id TEXT PRIMARY KEY,transaction_id TEXT NOT NULL REFERENCES transactions(id),amount_paise INTEGER NOT NULL CHECK(amount_paise>=0),
        source TEXT NOT NULL); INSERT OR IGNORE INTO schema_version VALUES(3);''')
    config=rates()
    conn.execute('INSERT OR IGNORE INTO pricing_contracts SELECT id,?,?,amount_paise*?/10000,fee_paise FROM transactions',
                 (config['earned_bps'],config['paid_bps'],config['earned_bps']))


def margin_rows(path=None) -> list[dict]:
    with connect(path) as c:
        contracts={r['transaction_id']:dict(r) for r in c.execute('SELECT * FROM pricing_contracts')}
        details={r['transaction_id']:dict(r) for r in c.execute('SELECT * FROM payment_details')}
        losses=defaultdict(int)
        for r in c.execute('SELECT * FROM dispute_loss_records'):losses[r['transaction_id']]+=r['amount_paise']
    fees=records('fees',path);refunds=records('refunds',path)
    results=[]
    source=flow_data(path)
    for tx in records('transactions',path):
        contract=contracts[tx['id']];f=flow(tx['id'],path,source=source)
        actual=sum(r['amount_paise'] for r in fees if r['transaction_id']==tx['id'])
        over_refund=max(0,sum(r['amount_paise'] for r in refunds if r['transaction_id']==tx['id'])-tx['amount_paise'])
        fee_excess=max(0,actual-contract['expected_paid_paise'])
        shortfall=f['stuck_paise'] if f['settlement_paise'] else 0
        duplicate=f['excess_settlement_paise']
        why=[]
        for issue,value in [('FEE_MISMATCH',fee_excess),('SHORT_SETTLEMENT',shortfall),('DUPLICATE_SETTLEMENT',duplicate),('OVER_REFUND',over_refund),('RECORDED_DISPUTE_LOSS',losses[tx['id']])]:
            if value:why.append({'issue':issue,'amount_paise':value,'transaction_id':tx['id']})
        leakage=fee_excess+shortfall+duplicate+over_refund
        # Fee excess is already counted in actual fee cost, so do not subtract it twice.
        margin=contract['earned_paise']-actual-shortfall-duplicate-over_refund-losses[tx['id']]
        results.append({'transaction_id':tx['id'],'merchant_id':tx['merchant_id'],'rail':tx['rail'],
                        'bin':details[tx['id']]['bin'],'fees_paid_paise':actual,'fees_earned_paise':contract['earned_paise'],
                        'expected_fees_paise':contract['expected_paid_paise'],'leakage_paise':leakage,
                        'dispute_losses_paise':losses[tx['id']],'net_margin_paise':margin,
                        'earned_fee_bps':contract['earned_bps'],'paid_fee_bps':contract['paid_bps'],
                        'pending_settlement_paise':f['stuck_paise'] if not f['settlement_paise'] else 0,
                        'why':why})
    return results


def profit_summary(path=None) -> dict:
    rows=margin_rows(path)
    measures=['fees_paid_paise','fees_earned_paise','leakage_paise','dispute_losses_paise','net_margin_paise','pending_settlement_paise']
    def group(key):
        groups={}
        for row in rows:
            g=groups.setdefault(row[key],{'key':row[key],'sample_size':0,**{m:0 for m in measures}})
            g['sample_size']+=1
            for m in measures:g[m]+=row[m]
        return sorted(groups.values(),key=lambda g:g['net_margin_paise'])
    return {'synthetic':True,'pricing_for_new_transactions':rates(),'by_merchant':group('merchant_id'),
            'by_rail':group('rail'),'by_bin':group('bin'),'ranked_transactions':sorted(rows,key=lambda r:r['net_margin_paise']),
            'totals':{m:sum(r[m] for r in rows) for m in measures},
            'assumptions':'Fees earned are modeled synthetic revenue at snapshotted rates. Leakage is potential exposure, not cash recovered. '
            'Fee excess is included once in net margin. Missing settlements are pending, not realized losses. Dispute losses require explicit ledger entries.'}


def fee_audit(path=None) -> list[dict]:
    rows=margin_rows(path);transactions={t['id']:t for t in records('transactions',path)}
    fees=records('fees',path);settlements=records('settlements',path)
    results=[]
    for row in rows:
        tx=transactions[row['transaction_id']]
        peers=[r['fees_paid_paise']/transactions[r['transaction_id']]['amount_paise'] for r in rows if r['rail']==row['rail']]
        rate=row['fees_paid_paise']/tx['amount_paise'];sd=statistics.pstdev(peers) if peers else 0
        z=(rate-statistics.mean(peers))/sd if sd else 0
        issues=[w for w in row['why'] if w['issue'] in {'FEE_MISMATCH','SHORT_SETTLEMENT'}]
        if not issues and not (len(peers)>=8 and abs(z)>=3):continue
        from backend.reconciliation import match
        matched,_,_=match(tx,settlements)
        evidence=[tx['id']]+[f['id'] for f in fees if f['transaction_id']==tx['id']]+[s['id'] for s in matched]
        decision=Decision(action='RAISE_CLAIM',confidence=.90 if issues else .72,
                          reasoning='Synthetic fee/settlement discrepancy; claim is a human-approved suggestion only.',
                          evidence=evidence,amount=money(tx['amount_paise']),case_id='FEE-'+tx['id'])
        results.append({'decision':decision.model_dump(mode='json'),'agent':'fee_audit','transaction_id':tx['id'],
                        'sample_size':len(peers),'fee_rate_z_score':z,'statistical_outlier':len(peers)>=8 and abs(z)>=3,
                        'findings':issues,'features':[rate,z,len(peers)],'provider':'local fee contracts + rail population z-score',
                        'payment_executed':False,'claim_filed':False})
    return results
