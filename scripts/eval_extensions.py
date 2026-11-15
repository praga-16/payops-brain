import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.extension_evaluation import save

if __name__=='__main__':
    report=save()
    print(json.dumps({k:report[k] for k in ('transaction_count','clean_lifecycle_no_gap','injected_gap_detection','fee_audit','bounded_outage_proposals','security_database_findings')},indent=2))
