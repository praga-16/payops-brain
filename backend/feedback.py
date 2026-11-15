"""Recalibrate correctness confidence from analyst labels; never assume gains."""
from __future__ import annotations

import json
import math
import random
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss

from backend import audit
from backend.decision import Decision, Policy
from backend.ledger import connect, utcnow


def features(confidence: float) -> list[float]:
    value=max(.001,min(.999,confidence))
    return [math.log(value/(1-value))]


def calibrated(confidence: float, model: dict | None) -> float:
    if not model:
        return confidence
    logit=model['coefficient']*features(confidence)[0]+model['intercept']
    return 1/(1+math.exp(-max(-30,min(30,logit))))


def latest(conn) -> dict | None:
    row=conn.execute("SELECT payload FROM model_registry WHERE name='confidence_calibrator' ORDER BY id DESC LIMIT 1").fetchone()
    return json.loads(row[0]) if row else None


def recalibrate(path=None) -> dict:
    with connect(path) as conn:
        conn.execute('BEGIN IMMEDIATE')
        rows=conn.execute('SELECT * FROM human_feedback ORDER BY id').fetchall()
        if not rows:
            return {'trained':False,'reason':'No analyst feedback yet','feedback_count':0}
        # Seeded synthetic prior makes a fit possible before both analyst classes
        # exist. Feedback gets higher weight; feedback never becomes test data.
        rng=random.Random(661)
        x,y,weights=[],[],[]
        for _ in range(300):
            score=rng.uniform(.5,.99)
            x.append(features(score));y.append(int(rng.random()<score));weights.append(1.)
        for row in rows:
            original=json.loads(row['original']);corrected=json.loads(row['corrected'])
            x.append(features(original['confidence']))
            y.append(int(original['action']==corrected['action']));weights.append(8.)
        fitted=LogisticRegression(C=1.,random_state=661).fit(x,y,sample_weight=weights)
        model={'coefficient':float(fitted.coef_[0][0]),'intercept':float(fitted.intercept_[0]),
               'feedback_count':len(rows),'synthetic_prior_count':300,
               'training':'seed 661 synthetic correctness prior + analyst feedback (weight 8)',
               'evaluation':'separate seeded synthetic holdout; not evidence of real-world improvement'}
        holdout=random.Random(662)
        test_scores=[holdout.uniform(.5,.99) for _ in range(300)]
        test_labels=[int(holdout.random()<s) for s in test_scores]
        model['brier_before']=float(brier_score_loss(test_labels,test_scores))
        model['brier_after']=float(brier_score_loss(test_labels,[calibrated(s,model) for s in test_scores]))
        predictions=[json.loads(r[0])['decision'] for r in conn.execute('SELECT payload FROM agent_decisions')]
        policy=Policy.configured()
        model['review_estimate_before']=sum(policy.gate(Decision.model_validate(d))!='AUTO_RESOLVED' for d in predictions)
        model['review_estimate_after']=sum(policy.gate(Decision.model_validate(d|{'confidence':calibrated(d['confidence'],model)}))!='AUTO_RESOLVED' for d in predictions)
        model['estimate_case_count']=len(predictions)
        conn.execute('INSERT INTO model_registry(name,payload,created_at) VALUES(?,?,?)',
                     ('confidence_calibrator',json.dumps(model),utcnow()))
        audit.append(conn,'MODEL_RECALIBRATED','confidence_calibrator',model)
        return {'trained':True,**model}
