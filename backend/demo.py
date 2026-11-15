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
    report=run_evaluation()
    print('Evaluation:',report['transaction_count'],'transactions;',report['case_count'],'cases')
    print('Open review cases:',summary()['open_cases'])
    print('Ready. Start backend.main:app and the Vite frontend, or use docker compose up --build.')


if __name__=='__main__':main()
