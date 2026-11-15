"""Evidence-based matching and break classification, without evaluation labels."""
from __future__ import annotations

import random
import re
from datetime import datetime
from difflib import SequenceMatcher
from functools import lru_cache

from sklearn.ensemble import GradientBoostingClassifier

from backend.decision import Decision
from backend.ledger import money, records


def normalize(reference: str) -> str:
    return re.sub(r'[^a-z0-9]', '', reference.lower())


def pair_features(tx: dict, settlement: dict) -> list[float]:
    expected = tx['amount_paise'] - tx['fee_paise']
    return [abs(settlement['amount_paise'] - expected) / max(expected, 1),
            abs((datetime.fromisoformat(settlement['settled_at']) -
                 datetime.fromisoformat(tx['created_at'])).total_seconds() / 86400 - 1),
            float(tx['merchant_id'] == settlement['merchant_id']),
            float(tx['rail'] == settlement['rail']),
            SequenceMatcher(None, normalize(tx['id']), normalize(settlement['reference'])).ratio(),
            float(settlement['status'] == 'SETTLED')]


@lru_cache(maxsize=1)
def match_model() -> GradientBoostingClassifier:
    # Separate generated training pairs, never current ledger labels. This is
    # synthetic training, not a production calibrated probability model.
    rng = random.Random(1701)
    features, labels = [], []
    for _ in range(1200):
        matched = rng.random() > .5
        features.append([rng.uniform(0,.2) if matched else rng.uniform(.01,1),
                         rng.uniform(0,.2) if matched else rng.uniform(0,5),
                         1 if matched else rng.randrange(2),
                         1 if matched else rng.randrange(2),
                         rng.uniform(.88,1) if matched else rng.uniform(.1,.94), 1])
        labels.append(int(matched))
    return GradientBoostingClassifier(n_estimators=40, max_depth=2, random_state=1701).fit(features, labels)


def match(tx: dict, settlements: list[dict], *, assisted: bool = True) -> tuple[list[dict], str, float]:
    exact = [s for s in settlements if s['transaction_id'] == tx['id'] or s['reference'] == tx['id']]
    if exact:
        return exact, 'exact reference', 1.0
    if not assisted:
        return [], 'no exact reference', .5
    normalized = [s for s in settlements if s['transaction_id'] is None and
                  normalize(s['reference']) == normalize(tx['id']) and
                  s['merchant_id'] == tx['merchant_id'] and s['rail'] == tx['rail']]
    if normalized:
        return normalized, 'normalized reference rule', .98
    candidates = []
    for s in settlements:
        if s['transaction_id'] is not None:
            continue
        # Never fuzzy-match distinct numeric payment references just because
        # their shared batch prefix makes their strings look similar.
        if re.sub(r'\D', '', s['reference']) != re.sub(r'\D', '', tx['id']):
            continue
        features = pair_features(tx,s)
        if features[2:4] != [1.0,1.0] or features[1] > 2 or features[0] > .25 or features[4] < .75:
            continue
        score = float(match_model().predict_proba([features])[0][1])
        if score >= .9:
            candidates.append((score,s))
    candidates.sort(key=lambda item:item[0], reverse=True)
    # Ambiguity is reviewed, never settled by arbitrary ordering.
    if candidates and (len(candidates)==1 or candidates[0][0]-candidates[1][0] >= .1):
        return [candidates[0][1]], 'fuzzy reference + gradient boosting', min(.89,candidates[0][0])
    return [], 'ambiguous or missing reference', .5


def classify(tx: dict, matched: list[dict], refunds: list[dict], fees: list[dict], disputes: list[dict]) -> str:
    if disputes:
        return 'CHARGEBACK'
    if sum(r['amount_paise'] for r in refunds) > tx['amount_paise']:
        return 'OVER_REFUND'
    if tx['device_risk'] >= .85:
        return 'FRAUD_SUSPECTED'
    if not matched:
        return 'MISSING_SETTLEMENT'
    if len(matched)>1:
        return 'DUPLICATE_SETTLEMENT'
    if sum(f['amount_paise'] for f in fees) != tx['fee_paise']:
        return 'FEE_MISMATCH'
    if matched[0]['amount_paise'] < tx['amount_paise']-tx['fee_paise']:
        return 'SHORT_SETTLEMENT'
    if matched[0]['amount_paise'] != tx['amount_paise']-tx['fee_paise']:
        return 'AMOUNT_MISMATCH'
    return 'CLEAN'


def break_features(tx: dict, matched: list[dict], refunds: list[dict], fees: list[dict], disputes: list[dict]) -> list[float]:
    expected=max(1,tx['amount_paise']-tx['fee_paise'])
    return [len(matched),(sum(s['amount_paise'] for s in matched)-expected)/expected,
            sum(r['amount_paise'] for r in refunds)/tx['amount_paise'],
            (sum(f['amount_paise'] for f in fees)-tx['fee_paise'])/max(1,tx['fee_paise']),
            float(bool(disputes)),tx['device_risk']]


@lru_cache(maxsize=1)
def break_model() -> GradientBoostingClassifier:
    rng=random.Random(1702)
    x,y=[],[]
    classes=['CLEAN','MISSING_SETTLEMENT','SHORT_SETTLEMENT','DUPLICATE_SETTLEMENT',
             'OVER_REFUND','FEE_MISMATCH','CHARGEBACK','FRAUD_SUSPECTED','AMOUNT_MISMATCH']
    for kind in classes:
        for _ in range(100):
            row=[1,0,0,0,0,rng.uniform(.01,.25)]
            if kind=='MISSING_SETTLEMENT':row[:2]=[0,-1]
            if kind=='SHORT_SETTLEMENT':row[1]=-rng.uniform(.00005,.25)
            if kind=='DUPLICATE_SETTLEMENT':row[:2]=[2,1]
            if kind=='OVER_REFUND':row[2]=rng.uniform(1.0001,1.4)
            if kind=='FEE_MISMATCH':row[3]=rng.uniform(.001,1)
            if kind=='CHARGEBACK':row[4]=1
            if kind=='FRAUD_SUSPECTED':row[5]=rng.uniform(.85,1)
            if kind=='AMOUNT_MISMATCH':row[1]=rng.uniform(.001,.3)
            x.append(row);y.append(kind)
    return GradientBoostingClassifier(n_estimators=40,max_depth=2,random_state=1702).fit(x,y)


def analyze(path=None, *, assisted: bool = True) -> list[dict]:
    tables = {name:records(name,path) for name in ('transactions','settlements','refunds','fees','disputes')}
    results=[]
    for tx in tables['transactions']:
        matched, method, confidence = match(tx,tables['settlements'],assisted=assisted)
        related = {name:[r for r in tables[name] if r['transaction_id']==tx['id']]
                   for name in ('refunds','fees','disputes')}
        kind=classify(tx,matched,**related)
        ml_features=break_features(tx,matched,**related)
        predicted=str(break_model().predict([ml_features])[0]) if assisted else kind
        evidence=[tx['id']]+[r['id'] for r in matched]+[r['id'] for rows in related.values() for r in rows]
        clean=kind==predicted=='CLEAN'
        decision=Decision(action='RECONCILE' if clean else 'INVESTIGATE',
                          confidence=confidence if clean else .88 if matched else .65,
                          reasoning=f'{kind}: {method}. Gross, expected fee and observed net checked in paise.',
                          evidence=evidence,amount=money(tx['amount_paise']),case_id='REC-'+tx['id'])
        results.append({'decision':decision.model_dump(mode='json'),'agent':'reconciliation',
                        'transaction_id':tx['id'],'break_type':kind,'match_method':method,
                        'ml_break_type':predicted,'match_score':confidence,'classifier_features':ml_features,
                        'matched_ids':[s['id'] for s in matched],
                        'features':[float(clean),confidence,tx['device_risk']],
                        'provider':'deterministic rules + synthetic-trained gradient boosting',
                        'payment_executed':False})
    return results
