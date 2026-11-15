"""Repeatable synthetic payment batches; no real customer identifiers.

Ground truth is written to an evaluation-only sibling database. Operational
agents receive only ordinary transaction, settlement and evidence records.
"""
from __future__ import annotations

import argparse
import random
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend import audit
from backend.ledger import connect, db_path, initialize, utcnow

BREAKS = ['MISSING_SETTLEMENT', 'SHORT_SETTLEMENT', 'DUPLICATE_SETTLEMENT',
          'OVER_REFUND', 'FEE_MISMATCH', 'CHARGEBACK', 'FRAUD_SUSPECTED']


def seed(count: int = 160, seed_value: int = 42, path: Path | str | None = None) -> dict:
    if not 16 <= count <= 10000:
        raise ValueError('Batch size must be between 16 and 10000')
    target = Path(path) if path else db_path()
    initialize(target)
    rng = random.Random(seed_value)
    # A repeated seed is idempotent, never clears historical ledger or audit.
    run_id = f'SIM-{seed_value}-{count}'
    labels: list[tuple] = []
    with connect(target) as conn:
        conn.execute('BEGIN IMMEDIATE')
        if conn.execute('SELECT 1 FROM simulation_runs WHERE id=?', (run_id,)).fetchone():
            return {'run_id': run_id, 'count': count, 'created': False}
        conn.execute('INSERT INTO simulation_runs VALUES(?,?,?,?)', (run_id, seed_value, count, utcnow()))
        for merchant in range(1, 13):
            conn.execute('INSERT OR IGNORE INTO merchant_profiles VALUES(?,?)',
                         (f'SYN-M{merchant:03}', f'Synthetic merchant {merchant:03}'))
        base = datetime(2026, 11, 1, tzinfo=timezone.utc) + timedelta(days=seed_value % 10)
        for i in range(count):
            slot = i % 16
            anomaly = BREAKS[slot] if slot < 7 else 'CLEAN'
            tid = f'{run_id}-T{i:05}'
            merchant = f'SYN-M{12 if anomaly == "FRAUD_SUSPECTED" else rng.randrange(1, 12):03}'
            rail = ['CARD', 'UPI', 'NET_BANKING'][i % 3]
            # All chargeback batches include a UPI demonstration, without a score fixture.
            if anomaly == 'CHARGEBACK':
                rail = 'UPI'
            amount = rng.randrange(10000, 2500000)
            expected_fee = amount * 2 // 100
            stamp = base + timedelta(seconds=i * 240)
            if anomaly == 'FRAUD_SUSPECTED':
                stamp = base + timedelta(seconds=(i // 16) * 2)
            delivery, auth = int(rng.random() > .15), int(rng.random() > .1)
            risk = rng.uniform(.86, .99) if anomaly == 'FRAUD_SUSPECTED' else rng.uniform(.01, .25)
            conn.execute('INSERT INTO transactions VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                         (tid, run_id, merchant, rail, amount, expected_fee, stamp.isoformat(),
                          'CAPTURED', delivery, auth, risk))
            if anomaly != 'MISSING_SETTLEMENT':
                net = amount - expected_fee
                if anomaly == 'SHORT_SETTLEMENT':
                    net -= rng.randrange(100, max(101, net // 5))
                # Some valid rows need reference normalization or candidate scoring.
                reference = tid if i % 4 else tid.lower().replace('-', '')
                fuzzy = i % 8 == 7
                if fuzzy:
                    reference = tid + 'x'
                conn.execute('INSERT INTO settlements VALUES(?,?,?,?,?,?,?,?)',
                             (f'{tid}-S1', tid if i % 4 and not fuzzy else None, reference, merchant, rail,
                              net, (stamp + timedelta(days=1)).isoformat(), 'SETTLED'))
                if anomaly == 'DUPLICATE_SETTLEMENT':
                    conn.execute('INSERT INTO settlements VALUES(?,?,?,?,?,?,?,?)',
                                 (f'{tid}-S2', tid, tid, merchant, rail, net,
                                  (stamp + timedelta(days=1)).isoformat(), 'SETTLED'))
            fee = expected_fee + (rng.randrange(100, 1000) if anomaly == 'FEE_MISMATCH' else 0)
            conn.execute('INSERT INTO fees VALUES(?,?,?)', (f'{tid}-F', tid, fee))
            if anomaly == 'OVER_REFUND':
                conn.execute('INSERT INTO refunds VALUES(?,?,?,?)',
                             (f'{tid}-R', tid, amount + rng.randrange(100, 3000), stamp.isoformat()))
            if anomaly == 'CHARGEBACK':
                conn.execute('INSERT INTO disputes VALUES(?,?,?,?,?,?)',
                             (f'{tid}-D', tid, 'UPI_UNAUTHORIZED', stamp.isoformat(),
                              (stamp + timedelta(days=30)).isoformat(), 'OPEN'))
            # A sampled synthetic outcome, not the model's predicted probability.
            probability = .35 + .27 * delivery + .20 * auth
            labels.append((tid, anomaly, int(anomaly == 'FRAUD_SUSPECTED'),
                           int(rng.random() < probability)))
        audit.append(conn, 'SIMULATION_BATCH', run_id, {'count': count, 'seed': seed_value, 'synthetic': True})
    truth_path = target.with_name(target.stem + '.truth.sqlite3')
    with closing(sqlite3.connect(truth_path)) as truth:
        with truth:
            truth.execute('CREATE TABLE IF NOT EXISTS ground_truth_labels '
                          '(transaction_id TEXT PRIMARY KEY, break_type TEXT, fraud INTEGER, dispute_won INTEGER)')
            truth.executemany('INSERT OR IGNORE INTO ground_truth_labels VALUES(?,?,?,?)', labels)
    from backend.moneyflow import backfill
    backfill(target)
    return {'run_id': run_id, 'count': count, 'created': True}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--count', type=int, default=160)
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    print(seed(args.count, args.seed))


if __name__ == '__main__':
    main()
