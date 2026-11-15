"""Append-only, hash-chained events. Triggers protect against ordinary SQL edits.

This detects edits but cannot protect against a database administrator rewriting
the entire chain; a production system needs an external trusted checkpoint.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3

from backend.ledger import utcnow


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def digest(event: dict) -> str:
    return hashlib.sha256(canonical(event).encode()).hexdigest()


def append(conn: sqlite3.Connection, event: str, case_id: str, payload: dict) -> dict:
    # Caller owns an IMMEDIATE transaction when multiple writes are involved.
    if not conn.in_transaction:
        conn.execute('BEGIN IMMEDIATE')
    last = conn.execute('SELECT id,hash FROM audit_events ORDER BY id DESC LIMIT 1').fetchone()
    entry = {'id': last['id'] + 1 if last else 1, 'created_at': utcnow(),
             'event': event, 'case_id': case_id, 'payload': canonical(payload),
             'previous_hash': last['hash'] if last else '0' * 64}
    entry['hash'] = digest(entry)
    conn.execute('INSERT INTO audit_events VALUES(:id,:created_at,:event,:case_id,:payload,:previous_hash,:hash)', entry)
    return entry


def verify(conn: sqlite3.Connection) -> dict:
    previous, count = '0' * 64, 0
    for row in conn.execute('SELECT * FROM audit_events ORDER BY id'):
        entry = dict(row)
        stored = entry.pop('hash')
        count += 1
        if entry['id'] != count or entry['previous_hash'] != previous or stored != digest(entry):
            return {'valid': False, 'checked': count, 'broken_at': entry['id']}
        previous = stored
    return {'valid': True, 'checked': count, 'head': previous}
