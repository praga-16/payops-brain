"""Read-only counterfactual replay of the original three-agent 512/608 holdout."""
from __future__ import annotations

from datetime import datetime,timezone
from functools import lru_cache
from pathlib import Path
import tempfile

from backend.decision import Decision,Policy
from backend.evaluation import wilson
from backend.impact import truth_for_reporting
from backend.simulator import seed
from backend.reconciliation import analyze as reconcile
from backend.dispute_intelligence import analyze as dispute_analysis
from backend.fraud import analyze as fraud_analysis


@lru_cache(maxsize=1)
def holdout() -> tuple:
    with tempfile.TemporaryDirectory(prefix='payops-replay-') as folder:
        path=Path(folder)/'holdout.sqlite3';seed(512,916,path)
        truth=truth_for_reporting(path)
        cases=[]
        for r in reconcile(path):
            cases.append((r['decision'],r['break_type'],r['ml_break_type']==truth[r['transaction_id']]['break_type'],
                          truth[r['transaction_id']]['break_type']=='CLEAN'))
        for r in dispute_analysis(path,now=datetime(2026,11,15,tzinfo=timezone.utc)):
            correct=(r['decision']['action']=='FIGHT')==bool(truth[r['transaction_id']]['won'])
            cases.append((r['decision'],'CHARGEBACK',correct,False))
        for r in fraud_analysis(path):
            cases.append((r['decision'],'FRAUD_ALERT',bool(truth[r['transaction_id']]['fraud']),False))
        return tuple(cases)


def replay(threshold: float) -> dict:
    if not .70<=threshold<=.99:raise ValueError('Replay threshold must be between .70 and .99')
    policy=Policy.configured()
    cases=holdout()
    def at(value):
        counterfactual=Policy(auto=value,review=min(policy.review,value),high_value=policy.high_value,write_off=policy.write_off)
        automated=[(d,safe) for d,_,_,safe in cases if counterfactual.gate(Decision.model_validate(d))=='AUTO_RESOLVED']
        errors=sum(not safe for _,safe in automated)
        return {'threshold':value,'auto_resolved':len(automated),'human_review':len(cases)-len(automated),
                'auto_resolve_rate':len(automated)/len(cases),'human_review_rate':1-len(automated)/len(cases),
                'false_auto_resolutions':errors,'false_auto_resolution_rate':errors/len(automated) if automated else None,
                'false_auto_resolution_95_wilson':wilson(errors,len(automated))}
    curve=[at(v) for v in sorted(set([.70,.75,.80,.85,.90,.95,.99,threshold]))]
    return {'synthetic':True,'transaction_count':512,'case_count':len(cases),'test_seed':916,
            'selected':at(threshold),'curve':curve,'stored_thresholds_changed':False,
            'scope':'Original reconciliation/dispute/fraud holdout only; new fee/routing agents are not added to the 608-case denominator.',
            'guardrails':'Restricted actions remain human-only at every threshold. No ledger, threshold or audit history is changed by replay.',
            'limitation':'Counterfactual synthetic results with shared generator assumptions, not deployment advice or production risk estimates.'}
