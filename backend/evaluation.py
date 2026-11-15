"""Reproducible held-out synthetic evaluation. Labels are read only here."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import tempfile
from contextlib import closing

import numpy as np
from sklearn.metrics import roc_auc_score

from backend import audit
from backend.decision import Decision, Policy
from backend.ledger import connect, utcnow, records
from backend.simulator import seed
from backend.reconciliation import analyze as reconcile
from backend.dispute_intelligence import analyze as disputes
from backend.fraud import analyze as fraud


def wilson(successes: int, count: int) -> list[float] | None:
    if not count:return None
    z=1.96;p=successes/count;denom=1+z*z/count
    center=(p+z*z/(2*count))/denom
    radius=z*((p*(1-p)/count+z*z/(4*count*count))**.5)/denom
    return [max(0,center-radius),min(1,center+radius)]


def run_evaluation(*, count: int = 512, test_seed: int = 916, persist: bool = True, path=None) -> dict:
    with tempfile.TemporaryDirectory(prefix='payops-eval-') as folder:
        test_db=Path(folder)/'holdout.sqlite3'
        seed(count,test_seed,test_db)
        # Evaluation is the sole reader of the isolated ground-truth database.
        with closing(sqlite3.connect(test_db.with_name('holdout.truth.sqlite3'))) as conn:
            truth={r[0]:{'break_type':r[1],'fraud':r[2],'won':r[3]} for r in conn.execute('SELECT * FROM ground_truth_labels')}
        baseline=reconcile(test_db,assisted=False)
        assisted=reconcile(test_db,assisted=True)
        dispute_rows=disputes(test_db,now=datetime(2026,11,15,tzinfo=timezone.utc))
        fraud_rows=fraud(test_db)
        operational=records('transactions',test_db)
        refund_rows=records('refunds',test_db)
        # Explicit rules-only fraud baseline uses the same observable safety rules,
        # rather than an artificially weakened baseline to inflate ML gains.
        baseline_fraud={t['id'] for t in operational if t['device_risk']>=.85 or
                        sum(r['amount_paise'] for r in refund_rows if r['transaction_id']==t['id'])>t['amount_paise']}
        assisted_fraud={r['transaction_id'] for r in fraud_rows}
        labels=[truth[r['transaction_id']]['won'] for r in dispute_rows]
        probs=[r['win_probability'] for r in dispute_rows]
        auc=float(roc_auc_score(labels,probs)) if len(set(labels))>1 else None
        results={};samples={};intervals={}
        for name,rows,fraud_ids,win_auc in [('baseline',baseline,baseline_fraud,.5 if auc is not None else None),
                                           ('assisted',assisted,assisted_fraud,auc)]:
            correct=sum((r['ml_break_type'] if name=='assisted' else r['break_type'])==truth[r['transaction_id']]['break_type'] for r in rows)
            decisions=[r['decision'] for r in rows]+[r['decision'] for r in dispute_rows]+[r['decision'] for r in fraud_rows]
            auto=[r for r in rows if Policy.configured().gate(Decision.model_validate(r['decision']))=='AUTO_RESOLVED']
            false_auto=sum(truth[r['transaction_id']]['break_type']!='CLEAN' for r in auto)
            true_pos=sum(truth[tid]['fraud'] for tid in fraud_ids)
            actual_fraud=sum(t['fraud'] for t in truth.values())
            auto_match=sum(bool(r['matched_ids']) and r['match_score']>=.95 for r in rows)
            human=sum(Policy.configured().gate(Decision.model_validate(d))!='AUTO_RESOLVED' for d in decisions)
            results[name]={'auto_match_rate':auto_match/len(rows),
                           'break_classification_accuracy':correct/len(rows),'dispute_win_auc':win_auc,
                           'fraud_precision':true_pos/len(fraud_ids) if fraud_ids else None,
                           'fraud_recall':true_pos/actual_fraud if actual_fraud else None,
                           'human_review_rate':human/len(decisions),
                           'false_auto_resolution_rate':false_auto/len(auto) if auto else None}
            samples[name]={'classified':len(rows),'correct':correct,'fraud_alerts':len(fraud_ids),
                           'fraud_true_positives':true_pos,'actual_fraud':actual_fraud,
                           'auto_resolutions':len(auto),'false_auto_resolutions':false_auto,
                           'reviewed_cases':human,'total_agent_cases':len(decisions),'dispute_outcomes':len(labels),
                           'dispute_wins':sum(labels),'auto_linked_transactions':auto_match}
            intervals[name]={'break_accuracy_95_wilson':wilson(correct,len(rows)),
                             'fraud_precision_95_wilson':wilson(true_pos,len(fraud_ids)),
                             'false_auto_resolution_95_wilson':wilson(false_auto,len(auto))}
        report={'created_at':utcnow(),'test_seed':test_seed,'as_of':'2026-11-15T00:00:00+00:00',
                'transaction_count':count,'case_count':samples['assisted']['total_agent_cases'],
                'baseline':results['baseline'],'assisted':results['assisted'],'sample_counts':samples,
                'confidence_intervals':intervals,
                'training':'Match GB: 1,200 synthetic pairs seed 1701; break GB: 900 synthetic vectors seed 1702; '
                           'dispute logistic: 2,000 synthetic outcomes seed 732; Isolation Forest: 800 normal vectors seed 991. '
                           'No holdout ledger IDs or labels are used in training or inference.',
                'definitions':{'auto_match_rate':'Reference links with match score >= .95 / all transactions; fuzzy suggestions remain reviewed.',
                               'false_auto_resolution_rate':'Incorrect CLEAN bookkeeping auto-resolutions / all auto-resolutions.',
                               'human_review_rate':'Non-auto decisions / reconciliation, dispute and fraud cases.',
                               'baseline':'Exact-reference reconciliation, deterministic break/fraud rules, constant win prior (.5 AUC).',
                               'assisted':'Normalized/fuzzy GB matching, GB break classification, logistic win estimate, Isolation Forest plus rules.'},
                'limitations':'Synthetic-demo validation only. Training and test seeds differ but share generator assumptions. '
                               'Heuristic confidence is not a calibrated real-world probability. Fraud labels identify injected bursts; '
                               'over-refund alerts count as false positives for this narrow target. No OCR/LLM quality benchmark. '
                               'Observed gains or losses do not imply production performance. Feedback calibration is reported separately.'}
    if persist:
        with connect(path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            conn.execute('INSERT INTO model_registry(name,payload,created_at) VALUES(?,?,?)',
                         ('evaluation',json.dumps(report),utcnow()))
            audit.append(conn,'EVALUATION_COMPLETED','control-tower',{'transaction_count':count,'test_seed':test_seed})
    return report


def markdown(report: dict) -> str:
    lines=['# PayOps Brain control tower evaluation','',f"Synthetic transactions: {report['transaction_count']}; agent cases: {report['case_count']}; seed: {report['test_seed']}.",
           '',report['training'],'','| Metric | Rules-only | AI-assisted |','|---|---|---|']
    for key in report['baseline']:
        def fmt(value):return 'N/A' if value is None else f'{value:.4f}'
        lines.append(f"| {key} | {fmt(report['baseline'][key])} | {fmt(report['assisted'][key])} |")
    lines+=['','## Sample counts and confidence intervals','', '```json',
            json.dumps({'samples':report['sample_counts'],'intervals':report['confidence_intervals']},indent=2),'```',
            '', '## Metric definitions','']
    lines += [f'- {k}: {v}' for k,v in report['definitions'].items()]
    lines+=['','## Limitations','',report['limitations'],'']
    return '\n'.join(lines)
