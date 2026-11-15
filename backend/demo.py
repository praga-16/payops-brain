"""Seed synthetic ledger, run all agents and populate evaluation scoreboard."""
from __future__ import annotations

import argparse
import os
os.environ.setdefault('PAYOPS_MOCK','true')

from backend.simulator import seed
from backend.control_tower import run_agents, summary
from backend.evaluation import run_evaluation


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed',type=int,default=42)
    parser.add_argument('--count',type=int,default=160)
    args=parser.parse_args()
    print('Synthetic batch:',seed(args.count,args.seed))
    print('New agent decisions:',run_agents())
    from backend.incidents import trigger
    for index,scenario in enumerate(('upi-bank-outage','duplicate-settlement-file','fee-rate-change','card-fraud-burst')):
        incident=trigger(scenario,count=16,seed_value=4200+index)
        print('Synthetic incident:',incident['scenario'],incident['batch']['created'])
    from backend.earned_autonomy import assess
    print('Autonomy assessment:',assess()['created'],'human-only proposals; no policy automatically relaxed')
    report=run_evaluation()
    print('Evaluation:',report['transaction_count'],'transactions;',report['case_count'],'cases')
    print('Open review cases:',summary()['open_cases'])
    from backend.extension_evaluation import save
    extended=save()
    print('Extension validation:',extended['transaction_count'],'synthetic transactions; card-like findings:',extended['security_database_findings'])
    print('Ready. Start backend.main:app and the Vite frontend, or use docker compose up --build.')
    print('Guided demo: http://localhost:8080/?view=Guided%20Demo (Vite: http://127.0.0.1:5173/?view=Guided%20Demo)')


if __name__=='__main__':main()
