"""Reporting-only synthetic rupee impact. Never used by agent inference."""
from __future__ import annotations

from contextlib import closing
from decimal import Decimal, ROUND_HALF_UP
import os
from pathlib import Path
import sqlite3

from backend.decision import Policy,Decision
from backend.ledger import connect,db_path,records
from backend.margins import margin_rows
from backend.reconciliation import analyze
from backend.review import queue


def truth_for_reporting(path=None) -> dict:
    target=Path(path) if path else db_path()
    target=target.with_name(target.stem+'.truth.sqlite3')
    if not target.exists():return {}
    with closing(sqlite3.connect(target.as_uri()+'?mode=ro',uri=True)) as conn:
        return {r[0]:{'break_type':r[1],'fraud':r[2],'won':r[3]} for r in conn.execute('SELECT * FROM ground_truth_labels')}


def ensure(conn) -> None:
    conn.executescript('''CREATE TABLE IF NOT EXISTS synthetic_recoveries(
        id TEXT PRIMARY KEY,transaction_id TEXT NOT NULL REFERENCES transactions(id),
        amount_paise INTEGER NOT NULL CHECK(amount_paise>=0), source TEXT NOT NULL);
        INSERT OR IGNORE INTO schema_version VALUES(4);''')


def impact_report(path=None) -> dict:
    rows=margin_rows(path);count=len(rows);truth=truth_for_reporting(path)
    policy=Policy.configured()
    baseline=analyze(path,assisted=False);assisted=analyze(path,assisted=True)
    touches_before=sum(policy.gate(Decision.model_validate(r['decision']))!='AUTO_RESOLVED' for r in baseline)
    touches_after=sum(policy.gate(Decision.model_validate(r['decision']))!='AUTO_RESOLVED' for r in assisted)
    avoided=touches_before-touches_after
    minutes=Decimal(os.getenv('MINUTES_PER_ANALYST_TOUCH') or '5')
    if not Decimal('0')<minutes<=Decimal('120'):raise ValueError('Minutes per touch must be >0 and <=120')
    leakage=sum(r['leakage_paise'] for r in rows)
    confirmed=sum(r['leakage_paise'] for r in rows if truth.get(r['transaction_id'],{}).get('break_type') in
                  {'SHORT_SETTLEMENT','DUPLICATE_SETTLEMENT','OVER_REFUND','FEE_MISMATCH'})
    with connect(path) as conn:
        recovered=conn.execute('SELECT COALESCE(SUM(amount_paise),0) FROM synthetic_recoveries').fetchone()[0]
    fight_cases=[r for r in queue(path) if r['agent']=='dispute' and r['status']!='REJECTED' and
                 r['effective_decision']['action']=='FIGHT' and r.get('win_probability') is not None]
    expected=sum((Decimal(r['decision']['amount'])*100*Decimal(str(r['win_probability'])) for r in fight_cases),Decimal(0))
    expected=int(expected.quantize(Decimal(1),rounding=ROUND_HALF_UP))
    def norm(value):
        return None if not count else str((Decimal(value)*100000/count).quantize(Decimal('.01'),rounding=ROUND_HALF_UP))
    hours=Decimal(avoided)*minutes/60
    return {'synthetic':True,'transaction_count':count,'ground_truth_coverage':sum(r['transaction_id'] in truth for r in rows),
            'leakage_found_paise':leakage,'label_validated_exposure_paise':confirmed,'resolved_recovery_paise':recovered,
            'fight_recommendation_count':len(fight_cases),'expected_recovery_paise':expected,
            'baseline_review_touches':touches_before,'assisted_review_touches':touches_after,'touches_avoided':avoided,
            'minutes_per_touch':str(minutes),'estimated_hours_avoided':str(hours.quantize(Decimal('.01'))),
            'per_100000_transactions':{'leakage_found_rupees':norm(Decimal(leakage)/100),
                                     'resolved_recovery_rupees':norm(Decimal(recovered)/100),
                                     'expected_recovery_rupees':norm(Decimal(expected)/100),
                                     'analyst_touches_avoided':norm(avoided),'hours_avoided':norm(hours)},
            'assumptions':['Leakage found is potential ledger exposure, not realized cash loss.',
                           'Resolved amounts require synthetic recovery ledger entries; approvals alone never count.',
                           'Expected recovery = ledger dispute amount times synthetic-model win probability; not guaranteed or executed.',
                           'Touches avoided compare raw reconciliation rules-only versus assisted gates on the same ledger, not measured staff hours.',
                           'Normalization scales this sample arithmetically to 100,000 transactions; it is not a forecast.',
                           'Ground truth is read only for this reporting view, never passed to agents.']}
