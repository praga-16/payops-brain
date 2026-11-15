"""Backend aggregates, batch orchestration and a stoppable local simulator."""
from __future__ import annotations

from collections import Counter
from datetime import datetime
import json
import logging
import threading

from backend import audit
from backend.ledger import connect, records, money, db_path
from backend.reconciliation import analyze as reconcile
from backend.dispute_intelligence import analyze as dispute_analysis
from backend.fraud import analyze as fraud_analysis, persist_alerts
from backend.review import persist, queue
from backend.simulator import seed

logger=logging.getLogger('payops.control_tower')
agent_lock=threading.Lock()


def run_agents(path=None) -> dict:
    with agent_lock:
        rec=reconcile(path)
        disputes=dispute_analysis(path)
        fraud=fraud_analysis(path)
        counts={'reconciliation':persist(rec,path),'dispute':persist(disputes,path),
                'fraud':persist_alerts(fraud,path)}
        from backend.margins import fee_audit
        counts['fee_audit']=persist(fee_audit(path),path)
        with connect(path) as conn:
            audit.append(conn,'AGENT_BATCH_COMPLETED','control-tower',{'created':counts,'provider':'local evidence computation'})
        logger.info(json.dumps({'event':'agent_batch_completed','created':counts}))
        return counts


def summary(path=None) -> dict:
    txs=records('transactions',path);settlements=records('settlements',path)
    cases=queue(path);rec=[c for c in cases if c['agent']=='reconciliation']
    breaks=Counter(c['break_type'] for c in rec)
    tiers=Counter(c['tier'] for c in cases if c['status']=='OPEN')
    with connect(path) as conn:
        touches=conn.execute('SELECT COUNT(*) FROM human_approvals').fetchone()[0]
        durations=[max(0,(datetime.fromisoformat(r['updated_at'])-datetime.fromisoformat(r['created_at'])).total_seconds())
                   for r in conn.execute('SELECT q.updated_at,d.created_at FROM review_queue q '
                                         'JOIN agent_decisions d USING(case_id) WHERE q.status IN (\'APPROVED\',\'REJECTED\',\'EDITED\')')]
        fraud_count=conn.execute('SELECT COUNT(*) FROM fraud_alerts').fetchone()[0]
    auto=sum(c['tier']=='AUTO_RESOLVED' for c in cases)
    return {'synthetic_only':True,'total_transactions':len(txs),
            'total_transaction_volume':money(sum(t['amount_paise'] for t in txs)),
            'total_settlements':len(settlements),'settlement_volume':money(sum(s['amount_paise'] for s in settlements)),
            'reconciliation_match_rate':sum(bool(c['matched_ids']) for c in rec)/len(rec) if rec else 0,
            'missing_settlements':breaks['MISSING_SETTLEMENT'],'short_settlements':breaks['SHORT_SETTLEMENT'],
            'duplicate_settlements':breaks['DUPLICATE_SETTLEMENT'],
            'open_disputes':sum(d['status']=='OPEN' for d in records('disputes',path)),
            'fraud_alerts':fraud_count,'auto_resolve_rate':auto/len(cases) if cases else 0,
            'auto_resolved':auto,'analyst_touches_per_case':touches/len(cases) if cases else 0,
            'average_resolution_seconds':sum(durations)/len(durations) if durations else None,
            'total_cases':len(cases),'open_cases':sum(c['status']=='OPEN' for c in cases),
            'queue_by_tier':{tier:tiers[tier] for tier in ('AUTO_RESOLVED','ONE_CLICK_REVIEW','EXPERT_QUEUE')},
            'break_counts':dict(breaks),'rails':dict(Counter(t['rail'] for t in txs)),
            'resolution_sample_count':len(durations),'payment_executed':False}


class SimulatorService:
    def __init__(self) -> None:
        self.lock=threading.Lock()
        self.stop_event=threading.Event()
        self.thread=None
        self.state={'running':False,'batches':0,'last_run':None,'error':None}

    def status(self) -> dict:
        with self.lock:
            return dict(self.state)

    def start(self, *, count: int, seed_value: int, continuous: bool, interval: float) -> dict:
        with self.lock:
            if self.state['running']:
                raise ValueError('Simulator is already running')
            self.state.update(running=True,error=None)
            self.stop_event.clear()
        path=db_path()  # Capture path; environment changes cannot redirect a running worker.
        def work() -> None:
            current=seed_value
            try:
                while not self.stop_event.is_set():
                    result=seed(count,current,path)
                    run_agents(path)
                    with self.lock:
                        self.state.update(batches=self.state['batches']+1,last_run=result)
                    if not continuous or self.stop_event.wait(interval):break
                    current+=1
            except Exception as exc:
                logger.error(json.dumps({'event':'simulator_failed','error_type':type(exc).__name__}))
                with self.lock:self.state['error']='Simulation failed; inspect local diagnostics.'
            finally:
                with self.lock:self.state['running']=False
        if continuous:
            self.thread=threading.Thread(target=work,daemon=True,name='payops-simulator')
            self.thread.start()
        else:
            work()
        return self.status()

    def stop(self) -> dict:
        self.stop_event.set()
        if self.thread:self.thread.join(timeout=2)
        return self.status()


simulator=SimulatorService()
