"""Computed chargeback evidence, deadlines and synthetic-trained outcome model."""
from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
import random

from sklearn.linear_model import LogisticRegression
from backend.decision import Decision
from backend.ledger import records, money
from backend.providers.factory import explain


@lru_cache(maxsize=1)
def win_model() -> LogisticRegression:
    rng=random.Random(732)
    x,y=[],[]
    for _ in range(2000):
        delivery,auth=rng.randrange(2),rng.randrange(2)
        probability=.35+.27*delivery+.20*auth
        x.append([delivery,auth]);y.append(int(rng.random()<probability))
    return LogisticRegression(random_state=732).fit(x,y)


def checklist_score(checks: dict[str,bool]) -> float:
    # Evidence confidence is a documented heuristic, not a calibrated win rate.
    # Archived signed receipt is unavailable in this prototype, explicitly shown.
    weights={'transaction_reference':.20,'settlement_record':.18,'authentication':.16,
             'delivery_proof':.16,'within_deadline':.12,'signed_receipt':.18}
    return round(sum(weight for key,weight in weights.items() if checks.get(key)),4)


def legacy_intelligence(state: dict) -> dict:
    verified=state.get('verification',{}).get('passed',False)
    matched=state.get('matched',[])
    return {'reason_code':state.get('rule',{}).get('code','UNAVAILABLE'),
            'evidence_checklist':{'matched_reference':bool(matched),'claims_verified':verified,
                                  'policy_available':bool(state.get('rule'))},
            'evidence_completeness':sum((bool(matched),verified,bool(state.get('rule'))))/3,
            'win_probability':None,'limitation':'Original notice workflow has no labeled chargeback outcome model.'}


def analyze(path=None, *, now: datetime | None = None, live_draft: bool = False) -> list[dict]:
    now=now or datetime.now(timezone.utc)
    transactions={r['id']:r for r in records('transactions',path)}
    settlements=records('settlements',path)
    from backend.reconciliation import match
    results=[]
    for dispute in records('disputes',path):
        tx=transactions[dispute['transaction_id']]
        matched,_,_=match(tx,settlements)
        deadline=datetime.fromisoformat(dispute['deadline'])
        checks={'transaction_reference':True,'settlement_record':bool(matched),
                'authentication':bool(tx['authenticated']),'delivery_proof':bool(tx['delivery_proof']),
                'within_deadline':now<=deadline,'signed_receipt':False}
        confidence=checklist_score(checks)
        probability=float(win_model().predict_proba([[tx['delivery_proof'],tx['authenticated']]])[0][1])
        action='FIGHT' if probability>=.6 and checks['within_deadline'] else 'ACCEPT'
        amount=money(tx['amount_paise'])
        facts={'transaction_id':tx['id'],'amount':amount,'reason_code':dispute['reason_code'],
               'deadline':dispute['deadline'],'action':action,'settlement_ids':[s['id'] for s in matched]}
        sentences=[f"Synthetic {tx['rail']} chargeback {dispute['id']} concerns transaction {tx['id']} for INR {amount}.",
                   f"Reason code: {dispute['reason_code']}. Evidence deadline: {dispute['deadline']}.",
                   f"Recommendation: {action}. Authentication evidence: {bool(tx['authenticated'])}; delivery proof: {bool(tx['delivery_proof'])}.",
                   'Human approval is required. No arbitration or payment will be executed.']
        draft=explain(sentences,facts=facts,task='Compose a grounded dispute explanation.',use_provider=live_draft)
        decision=Decision(action=action,confidence=confidence,
                          reasoning='Weighted evidence checklist; signed receipt unavailable. '
                          'Win estimate is trained on separate synthetic outcomes, not a success guarantee.',
                          evidence=[tx['id'],dispute['id']]+[s['id'] for s in matched],
                          amount=amount,case_id='DIS-'+dispute['id'])
        results.append({'decision':decision.model_dump(mode='json'),'agent':'dispute',
                        'transaction_id':tx['id'],'reason_code':dispute['reason_code'],
                        'checklist':checks,'evidence_completeness':confidence,'win_probability':probability,
                        'deadline':dispute['deadline'],'overdue':now>deadline,'draft':draft,
                        'provider':draft['provider'],'features':[float(v) for v in checks.values()],
                        'payment_executed':False})
    return results
