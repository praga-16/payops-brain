"""Measured extension validation on separate synthetic data, not production QA."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile

from backend.ledger import ROOT,records
from backend.simulator import seed
from backend.impact import truth_for_reporting
from backend.moneyflow import flow,flow_data
from backend.margins import fee_audit
from backend.routing import routing_report
from backend.autonomy_replay import replay
from backend.evaluation import wilson
from backend.security import scan_database


def run() -> dict:
    with tempfile.TemporaryDirectory(prefix='payops-extension-eval-') as folder:
        path=Path(folder)/'eval.sqlite3';seed(512,916,path)
        truth=truth_for_reporting(path);source=flow_data(path)
        flows={t['id']:flow(t['id'],path,source=source) for t in records('transactions',path)}
        clean=[tid for tid,t in truth.items() if t['break_type']=='CLEAN']
        gap=[tid for tid,t in truth.items() if t['break_type'] in {'MISSING_SETTLEMENT','SHORT_SETTLEMENT','DUPLICATE_SETTLEMENT'}]
        clean_pass=sum(flows[t]['clearing_settlement_gap_paise']==0 and flows[t]['authorization_clearing_gap_paise']==0 for t in clean)
        detected=sum(flows[t]['clearing_settlement_gap_paise']!=0 for t in gap)
        expected={tid for tid,t in truth.items() if t['break_type'] in {'SHORT_SETTLEMENT','FEE_MISMATCH'}}
        predictions={r['transaction_id'] for r in fee_audit(path)}
        tp=len(expected&predictions)
        safety=scan_database(path)
        outage=Path(folder)/'outage.sqlite3';seed(32,917,outage,scenario='upi-bank-outage')
        routing=routing_report(outage)
        report={'synthetic':True,'transaction_count':512,'test_seed':916,
                'clean_lifecycle_no_gap':{'passed':clean_pass,'sample_size':len(clean),'95_wilson':wilson(clean_pass,len(clean))},
                'injected_gap_detection':{'passed':detected,'sample_size':len(gap),'95_wilson':wilson(detected,len(gap))},
                'fee_audit':{'true_positives':tp,'predicted_claims':len(predictions),'actual_discrepancies':len(expected),
                             'precision':tp/len(predictions) if predictions else None,'recall':tp/len(expected) if expected else None,
                             'precision_95_wilson':wilson(tp,len(predictions)),'recall_95_wilson':wilson(tp,len(expected))},
                'outage_route_contexts':routing['contexts'],
                'bounded_outage_proposals':[{'shift':r['maximum_shift'],'simulated_success_uplift':r['simulated_success_uplift'],
                                             'sample_sizes':r['sample_sizes'],'routing_executed':r['routing_executed']} for r in routing['proposals']],
                'autonomy_replay':replay(.95),'security_database_findings':len(safety['card_like_findings']),
                'limitations':'Seeded synthetic-only validation. Models share simulator assumptions. Route trials are counterfactual, '
                               'not independent production payments. No production improvement, cash recovery or physical microphone QA is claimed. '
                               'Voice loopback results are separate. New agents are excluded from the original 608-case replay denominator.'}
    return report


def save() -> dict:
    report=run();folder=ROOT/'reports';folder.mkdir(exist_ok=True)
    (folder/'extensions_eval.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    lines=['# Synthetic operations extension evaluation','',report['limitations'],'',
           '## Measured results','', '```json',json.dumps(report,indent=2),'```','']
    (folder/'extensions_eval.md').write_text('\n'.join(lines),encoding='utf-8')
    return report
