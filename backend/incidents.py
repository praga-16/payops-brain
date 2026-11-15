"""Deterministic incident batches; never alter existing ledger records."""
from __future__ import annotations
import threading
from backend.ledger import connect
from backend.simulator import seed,INCIDENTS

lock=threading.Lock()


def ensure(conn) -> None:
    conn.executescript('''CREATE TABLE IF NOT EXISTS incident_runs(
        run_id TEXT PRIMARY KEY REFERENCES simulation_runs(id), scenario TEXT NOT NULL,
        count INTEGER NOT NULL,created_at TEXT NOT NULL); INSERT OR IGNORE INTO schema_version VALUES(5);''')


def history(path=None) -> dict:
    with connect(path) as c:
        return {'synthetic':True,'scenarios':list(INCIDENTS),'next_seed':c.execute('SELECT COALESCE(MAX(seed),999)+1 FROM simulation_runs').fetchone()[0],
                'runs':[dict(r) for r in c.execute('SELECT * FROM incident_runs ORDER BY created_at DESC')]}


def trigger(scenario: str, *, count: int = 16, seed_value: int | None = None, path=None) -> dict:
    from backend.control_tower import run_agents
    if scenario not in INCIDENTS:raise ValueError('Unknown synthetic incident')
    with lock:
        if seed_value is None:seed_value=history(path)['next_seed']
        batch=seed(count,seed_value,path,scenario=scenario)
        created=run_agents(path)
    return {'synthetic':True,'batch':batch,'scenario':scenario,'new_decisions':created,
            'restricted_action_executed':False,'note':'Only new synthetic payment records were generated; no bank or payment policy changed.'}
