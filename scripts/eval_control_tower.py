"""Standalone reproducible evaluation; original dispute eval remains intact."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.ledger import initialize,ROOT
from backend.evaluation import run_evaluation,markdown


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--count',type=int,default=512)
    parser.add_argument('--seed',type=int,default=916)
    args=parser.parse_args()
    initialize()
    report=run_evaluation(count=args.count,test_seed=args.seed)
    folder=ROOT/'reports';folder.mkdir(exist_ok=True)
    (folder/'control_tower_eval.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (folder/'control_tower_eval.md').write_text(markdown(report),encoding='utf-8')
    print(markdown(report))


if __name__=='__main__':main()
