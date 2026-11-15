"""Isolation Forest plus explicit risk, velocity and refund checks."""
from __future__ import annotations

from datetime import datetime
from functools import lru_cache
import math
import random
import statistics

from sklearn.ensemble import IsolationForest
from backend.decision import Decision
from backend.ledger import records, money, connect
from backend.review import save_result


@lru_cache(maxsize=1)
def anomaly_model() -> IsolationForest:
    rng=random.Random(991)
    normal=[[math.log1p(rng.randrange(10000,2500000)),rng.uniform(.01,.3),
             rng.randrange(1,4),rng.uniform(0,.1),rng.uniform(.2,3)] for _ in range(800)]
    return IsolationForest(n_estimators=60, contamination=.04,random_state=991).fit(normal)


def analyze(path=None) -> list[dict]:
    transactions=records('transactions',path)
    refunds=records('refunds',path)
    results=[]
    for tx in transactions:
        peers=[r for r in transactions if r['merchant_id']==tx['merchant_id']]
        stamp=datetime.fromisoformat(tx['created_at'])
        velocity=sum(0 <= (stamp-datetime.fromisoformat(r['created_at'])).total_seconds() <= 60 for r in peers)
        refunded=sum(r['amount_paise'] for r in refunds if r['transaction_id']==tx['id'])
        ratio=refunded/tx['amount_paise']
        merchant_ratio=tx['amount_paise']/max(1,statistics.median(r['amount_paise'] for r in peers))
        features=[math.log1p(tx['amount_paise']),tx['device_risk'],velocity,ratio,merchant_ratio]
        anomaly=float(anomaly_model().score_samples([features])[0])
        isolation=max(0.,min(1.,(-anomaly-.4)/.3))
        risk=min(1.,.55*tx['device_risk']+.25*min(1,velocity/5)+.20*isolation)
        flags=[]
        if tx['device_risk']>=.85:flags.append('high device risk')
        if velocity>=5:flags.append('merchant burst: at least five payments per minute')
        if ratio>1:flags.append('refund exceeds captured amount')
        if merchant_ratio>4:flags.append('unusual merchant amount')
        if risk<.6 and not flags:
            continue
        decision=Decision(action='MERCHANT_REVIEW',confidence=round(max(.65,risk),4),
                          reasoning='; '.join(flags or ['Isolation Forest outlier'])+'. No processing restriction executed.',
                          evidence=[tx['id']]+[r['id'] for r in refunds if r['transaction_id']==tx['id']],
                          amount=money(tx['amount_paise']),case_id='FRD-'+tx['id'])
        results.append({'decision':decision.model_dump(mode='json'),'agent':'fraud','transaction_id':tx['id'],
                        'risk_score':round(risk,4),'velocity_60s':velocity,'refund_ratio':ratio,
                        'merchant_amount_ratio':merchant_ratio,'isolation_score':anomaly,
                        'features':features,'provider':'local Isolation Forest + deterministic rules',
                        'payment_executed':False,'processing_disabled':False})
    return results


def persist_alerts(results: list[dict], path=None) -> int:
    with connect(path) as conn:
        conn.execute('BEGIN IMMEDIATE')
        count=0
        for result in results:
            if save_result(conn,result):
                conn.execute('INSERT INTO fraud_alerts(case_id,risk) VALUES(?,?)',
                             (result['decision']['case_id'],result['risk_score']))
                count+=1
        return count
