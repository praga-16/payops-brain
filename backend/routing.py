"""Synthetic BIN diagnostics and contextual LinUCB routing suggestions only."""
from __future__ import annotations

from collections import Counter,defaultdict
from decimal import Decimal
import hashlib
import math
import os
import random

import numpy as np
from scipy.stats import fisher_exact
from backend.decision import Decision
from backend.evaluation import wilson
from backend.ledger import connect,records,money


def settings() -> dict:
    minimum=int(os.getenv('ROUTING_MIN_SAMPLES') or '30')
    shift=float(os.getenv('ROUTING_MAX_TRAFFIC_SHIFT') or '.10')
    if minimum<10 or not 0<shift<=.25:raise ValueError('Routing guardrails: minimum >=10 and shift >0 through .25')
    return {'minimum_sample_size':minimum,'maximum_traffic_shift':shift,'ucb_alpha':.25}


def backfill(conn) -> None:
    conn.executescript('''CREATE TABLE IF NOT EXISTS route_observations(
        id TEXT PRIMARY KEY,transaction_id TEXT NOT NULL REFERENCES transactions(id),route TEXT NOT NULL,
        rail TEXT NOT NULL,outage INTEGER NOT NULL,success INTEGER NOT NULL CHECK(success IN (0,1)),
        cost_paise INTEGER NOT NULL CHECK(cost_paise>=0),source TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS route_context ON route_observations(rail,outage,route);
        INSERT OR IGNORE INTO schema_version VALUES(6);''')
    done={r[0] for r in conn.execute('SELECT DISTINCT transaction_id FROM route_observations')}
    for tx in conn.execute('SELECT * FROM transactions').fetchall():
        if tx['id'] in done:continue
        outage=int('upi-bank-outage' in tx['run_id'])
        rng=random.Random(int(hashlib.sha256(tx['id'].encode()).hexdigest()[:12],16))
        for route,cost,probability in [('SYN-ROUTE-A',10,.25 if outage else .94),('SYN-ROUTE-B',20,.90 if outage else .96)]:
            for trial in range(8):
                conn.execute('INSERT OR IGNORE INTO route_observations VALUES(?,?,?,?,?,?,?,?)',
                             (f'{tx["id"]}-{route}-{trial}',tx['id'],route,tx['rail'],outage,
                              int(rng.random()<probability),cost,'seeded counterfactual route trial; not a real payment outcome'))


def bin_report(path=None) -> dict:
    txs={r['id']:r for r in records('transactions',path)}
    fees=records('fees',path);disputes=records('disputes',path)
    with connect(path) as c:
        details=[dict(r) for r in c.execute('SELECT d.*,e.status FROM payment_details d JOIN lifecycle_events e '
                                          "ON e.transaction_id=d.transaction_id AND e.stage='AUTHORIZATION'")]
        flagged={r['transaction_id'] for r in c.execute('SELECT d.transaction_id FROM fraud_alerts f JOIN agent_decisions d USING(case_id)')}
    groups=defaultdict(list)
    for d in details:groups[(d['bin'],d['issuer'],txs[d['transaction_id']]['rail'])].append(d)
    result=[]
    for (bin_id,issuer,rail),items in groups.items():
        ids={r['transaction_id'] for r in items};n=len(items)
        successes=sum(r['status']=='APPROVED' for r in items)
        others=[d for d in details if d['transaction_id'] not in ids and txs[d['transaction_id']]['rail']==rail]
        other_success=sum(r['status']=='APPROVED' for r in others)
        p=float(fisher_exact([[successes,n-successes],[other_success,len(others)-other_success]]).pvalue) if others else 1.
        adjusted=min(1.,p*max(1,len(groups)))
        result.append({'bin':bin_id,'issuer':issuer,'rail':rail,'sample_size':n,'success_rate':successes/n,
                       'success_95_wilson':wilson(successes,n),'top_decline_reasons':dict(Counter(d['decline_reason'] or 'UNSPECIFIED' for d in items if d['status']!='APPROVED')),
                       'dispute_rate':sum(any(r['transaction_id']==tid for r in disputes) for tid in ids)/n,
                       'fraud_flag_rate':len(ids&flagged)/n,'fees_paid_paise':sum(r['amount_paise'] for r in fees if r['transaction_id'] in ids),
                       'fisher_adjusted_p':adjusted,'low_success_outlier':n>=20 and len(others)>=20 and adjusted<.05 and successes/n<other_success/len(others)})
    return {'synthetic':True,'groups':result,'method':'Two-sided Fisher exact test, Bonferroni-adjusted across displayed groups; minimum 20 payments in group and comparator.',
            'provenance':'Synthetic authorization snapshots; historical captured payments are inferred approved. No external issuer/decline telemetry is claimed.'}


def context(rail: str,outage: int) -> np.ndarray:
    return np.array([1.,float(rail=='UPI'),float(rail=='CARD'),float(rail=='NET_BANKING'),float(outage)])


def routing_report(path=None) -> dict:
    config=settings();observations=records('route_observations',path)
    stats=defaultdict(list);models={}
    for row in observations:
        x=context(row['rail'],row['outage']);arm=row['route']
        if arm not in models:models[arm]=[np.eye(5),np.zeros(5)]
        models[arm][0]+=np.outer(x,x)
        models[arm][1]+=x*(row['success']-row['cost_paise']/10000)
        stats[(row['rail'],row['outage'],arm)].append(row)
    contexts=[];proposals=[];txs={t['id']:t for t in records('transactions',path)}
    for rail,outage in sorted({(r['rail'],r['outage']) for r in observations}):
        x=context(rail,outage);arms=[]
        for arm,(a,b) in models.items():
            rows=stats[(rail,outage,arm)];n=len(rows)
            if not n:continue
            inv=np.linalg.inv(a);score=float(x@inv@b+config['ucb_alpha']*math.sqrt(float(x@inv@x)))
            successes=sum(r['success'] for r in rows)
            arms.append({'route':arm,'sample_size':n,'successes':successes,'success_rate':successes/n,
                         'success_95_wilson':wilson(successes,n),'cost_paise':sum(r['cost_paise'] for r in rows),
                         'cost_per_trial_paise':str(Decimal(sum(r['cost_paise'] for r in rows))/n),'linucb_score':score})
        arms.sort(key=lambda a:a['route']);base=next((a for a in arms if a['route']=='SYN-ROUTE-A'),None)
        best=max(arms,key=lambda a:a['linucb_score']) if arms else None
        item={'rail':rail,'outage':bool(outage),'routes':arms,'current_route':'SYN-ROUTE-A'}
        contexts.append(item)
        if not base or not best or best['route']==base['route'] or min(base['sample_size'],best['sample_size'])<config['minimum_sample_size'] or best['success_rate']<=base['success_rate']:continue
        sample=stats[(rail,outage,best['route'])][0];tx=txs[sample['transaction_id']]
        shift=config['maximum_traffic_shift'];uplift=shift*(best['success_rate']-base['success_rate'])
        p=float(fisher_exact([[base['successes'],base['sample_size']-base['successes']],
                             [best['successes'],best['sample_size']-best['successes']]]).pvalue)
        decision=Decision(action='ROUTING_CHANGE',confidence=min(.99,max(.7,1-p)),
                          reasoning='Contextual LinUCB suggests a bounded synthetic shift after success/cost observation. Human approval required; no routing is executed.',
                          evidence=[tx['id'],sample['id']],amount=money(tx['amount_paise']),
                          case_id=f'ROUTE-{rail}-{outage}-{len(observations)}')
        proposals.append({'decision':decision.model_dump(mode='json'),'agent':'routing','transaction_id':tx['id'],
                          'proposed_route':best['route'],'maximum_shift':shift,'simulated_success_uplift':uplift,
                          'baseline_success_rate':base['success_rate'],'estimated_success_rate_after':base['success_rate']+uplift,
                          'sample_sizes':{a['route']:a['sample_size'] for a in arms},'fisher_p':p,
                          'context':{'rail':rail,'outage':bool(outage)},'features':x.tolist(),
                          'provider':'local contextual LinUCB over seeded route observations','routing_executed':False,'payment_executed':False})
    return {'synthetic':True,'guardrails':config,'contexts':contexts,'proposals':proposals,
            'limitation':'Observed synthetic counterfactual trials, not independent production payments. Uplift is a bounded simulation estimate, not a measured live gain. Approval records advice only.'}
