"""Explicit opt-in provider check with synthetic facts; never prints secrets."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.merchant import chat
from backend.ledger import initialize,records
from backend.simulator import seed


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument('--require-live',action='store_true')
    args=parser.parse_args()
    initialize()
    if not records('transactions'):seed()
    for language in ('en','hi','ta'):
        result=chat('SYN-M001','Why is my settlement short?',language)
        print({'language':language,'provider':result['provider'],'mode':result['mode'],
               'grounded':result['grounded'],'fallback_reason':result.get('fallback_reason')})
        if args.require_live and result['mode']!='live':return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
