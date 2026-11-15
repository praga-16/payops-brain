"""SQLite operational ledger. Money is integer paise; labels live elsewhere."""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Iterator

from backend.config import ROOT


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def money(paise: int) -> str:
    return str((Decimal(paise) / 100).quantize(Decimal('0.01')))


def db_path() -> Path:
    return Path(os.getenv('PAYOPS_DB') or ROOT / 'runtime' / 'payops.sqlite3')


SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version(version INTEGER PRIMARY KEY);
INSERT OR IGNORE INTO schema_version VALUES(1);
CREATE TABLE IF NOT EXISTS simulation_runs(
 id TEXT PRIMARY KEY, seed INTEGER NOT NULL, count INTEGER NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS merchant_profiles(id TEXT PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS transactions(
 id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES simulation_runs(id),
 merchant_id TEXT NOT NULL REFERENCES merchant_profiles(id),
 rail TEXT NOT NULL CHECK(rail IN ('CARD','UPI','NET_BANKING')),
 amount_paise INTEGER NOT NULL CHECK(amount_paise>0), fee_paise INTEGER NOT NULL CHECK(fee_paise>=0),
 created_at TEXT NOT NULL, status TEXT NOT NULL, delivery_proof INTEGER NOT NULL,
 authenticated INTEGER NOT NULL, device_risk REAL NOT NULL CHECK(device_risk BETWEEN 0 AND 1));
CREATE TABLE IF NOT EXISTS settlements(
 id TEXT PRIMARY KEY, transaction_id TEXT REFERENCES transactions(id), reference TEXT NOT NULL,
 merchant_id TEXT NOT NULL REFERENCES merchant_profiles(id), rail TEXT NOT NULL,
 amount_paise INTEGER NOT NULL CHECK(amount_paise>=0), settled_at TEXT NOT NULL, status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS refunds(
 id TEXT PRIMARY KEY, transaction_id TEXT NOT NULL REFERENCES transactions(id),
 amount_paise INTEGER NOT NULL CHECK(amount_paise>0), created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS fees(
 id TEXT PRIMARY KEY, transaction_id TEXT NOT NULL REFERENCES transactions(id),
 amount_paise INTEGER NOT NULL CHECK(amount_paise>=0));
CREATE TABLE IF NOT EXISTS disputes(
 id TEXT PRIMARY KEY, transaction_id TEXT NOT NULL REFERENCES transactions(id), reason_code TEXT NOT NULL,
 opened_at TEXT NOT NULL, deadline TEXT NOT NULL, status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS agent_decisions(
 case_id TEXT PRIMARY KEY, agent TEXT NOT NULL, transaction_id TEXT REFERENCES transactions(id),
 payload TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS review_queue(
 case_id TEXT PRIMARY KEY REFERENCES agent_decisions(case_id), tier TEXT NOT NULL,
 status TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS human_approvals(
 id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL REFERENCES agent_decisions(case_id),
 decision TEXT NOT NULL, comment TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS human_feedback(
 id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL REFERENCES agent_decisions(case_id),
 original TEXT NOT NULL, corrected TEXT NOT NULL, reason TEXT NOT NULL,
 features TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS model_registry(
 id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS fraud_alerts(
 case_id TEXT PRIMARY KEY REFERENCES agent_decisions(case_id), risk REAL NOT NULL, suggested INTEGER NOT NULL DEFAULT 0,
 approved INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS audit_events(
 id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, event TEXT NOT NULL,
 case_id TEXT NOT NULL, payload TEXT NOT NULL, previous_hash TEXT NOT NULL, hash TEXT NOT NULL);
CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit_events
 BEGIN SELECT RAISE(ABORT,'audit events are append-only'); END;
CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit_events
 BEGIN SELECT RAISE(ABORT,'audit events are append-only'); END;
CREATE INDEX IF NOT EXISTS settlement_reference ON settlements(reference);
CREATE INDEX IF NOT EXISTS settlement_transaction ON settlements(transaction_id);
CREATE INDEX IF NOT EXISTS transaction_merchant_time ON transactions(merchant_id,created_at);
CREATE INDEX IF NOT EXISTS refund_transaction ON refunds(transaction_id);
CREATE INDEX IF NOT EXISTS dispute_transaction ON disputes(transaction_id);
CREATE INDEX IF NOT EXISTS audit_case ON audit_events(case_id,id);
"""


@contextmanager
def connect(path: Path | str | None = None) -> Iterator[sqlite3.Connection]:
    target = Path(path) if path else db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('PRAGMA busy_timeout=30000')
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def initialize(path: Path | str | None = None) -> None:
    with connect(path) as conn:
        conn.execute('PRAGMA journal_mode=WAL')
        conn.executescript(SCHEMA)


def records(table: str, path: Path | str | None = None) -> list[dict]:
    allowed = {'transactions', 'settlements', 'refunds', 'disputes', 'fees', 'merchant_profiles'}
    if table not in allowed:
        raise ValueError('Not an operational ledger table')
    with connect(path) as conn:
        return [dict(row) for row in conn.execute(f'SELECT * FROM {table} ORDER BY id')]
