from backend.extension_evaluation import run


def test_extension_metrics_are_measured_and_guarded():
    r=run()
    assert r['transaction_count']==512
    assert r['clean_lifecycle_no_gap']['passed']==r['clean_lifecycle_no_gap']['sample_size']
    assert r['injected_gap_detection']['passed']==r['injected_gap_detection']['sample_size']
    assert 0<=r['fee_audit']['precision']<=1 and 0<=r['fee_audit']['recall']<=1
    assert r['autonomy_replay']['case_count']==608
    assert r['security_database_findings']==0
    assert all(not p['routing_executed'] and 0<p['shift']<=.1 for p in r['bounded_outage_proposals'])
