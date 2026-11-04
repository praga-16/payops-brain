# Evaluation results

Mode: **LIVE MODELS**

Extraction and drafting ran on real models over 30 synthetic notices with synthetic policy labels.
These numbers do not measure real-world dispute performance.

- Action accuracy: **100.0% (30/30)**
- Citation-validity rate (existing ledger IDs / all cited IDs): **100.0% (31/31)**
- Full evidence-verifier pass rate: **100.0% (30/30)**
- Recommended escalations: **12/30**
- Cases requiring human approval or rejection: **30/30**
- Agent errors: **0**

## Per-step configuration

```json
{
  "extract": {
    "model": "muse-spark-1.3",
    "protocol": "responses",
    "mode": "live"
  },
  "redact": {
    "model": "muse-spark-1.3",
    "protocol": "responses",
    "mode": "live"
  },
  "draft": {
    "model": "muse-spark-1.3",
    "protocol": "responses",
    "mode": "live"
  }
}
```

## Per-case results

| Case | Scenario | Image | Expected | Actual | Correct | Verified |
|---|---|---|---|---|---|---|
| D001 | duplicate_debit | rotated | REFUND | REFUND | True | True |
| D002 | already_refunded | blurred | NO_ACTION | NO_ACTION | True | True |
| D003 | amount_mismatch | low_contrast | ESCALATE | ESCALATE | True | True |
| D004 | outside_window | clean | ESCALATE | ESCALATE | True | True |
| D005 | failed_but_debited | rotated | REFUND | REFUND | True | True |
| D006 | unknown_txn | blurred | ESCALATE | ESCALATE | True | True |
| D007 | clean | low_contrast | NO_ACTION | NO_ACTION | True | True |
| D008 | duplicate_debit | clean | REFUND | REFUND | True | True |
| D009 | already_refunded | rotated | NO_ACTION | NO_ACTION | True | True |
| D010 | amount_mismatch | blurred | ESCALATE | ESCALATE | True | True |
| D011 | outside_window | low_contrast | ESCALATE | ESCALATE | True | True |
| D012 | failed_but_debited | clean | REFUND | REFUND | True | True |
| D013 | unknown_txn | rotated | ESCALATE | ESCALATE | True | True |
| D014 | clean | blurred | NO_ACTION | NO_ACTION | True | True |
| D015 | duplicate_debit | low_contrast | REFUND | REFUND | True | True |
| D016 | already_refunded | clean | NO_ACTION | NO_ACTION | True | True |
| D017 | amount_mismatch | rotated | ESCALATE | ESCALATE | True | True |
| D018 | outside_window | blurred | ESCALATE | ESCALATE | True | True |
| D019 | failed_but_debited | low_contrast | REFUND | REFUND | True | True |
| D020 | unknown_txn | clean | ESCALATE | ESCALATE | True | True |
| D021 | clean | rotated | NO_ACTION | NO_ACTION | True | True |
| D022 | duplicate_debit | blurred | REFUND | REFUND | True | True |
| D023 | already_refunded | low_contrast | NO_ACTION | NO_ACTION | True | True |
| D024 | amount_mismatch | clean | ESCALATE | ESCALATE | True | True |
| D025 | outside_window | rotated | ESCALATE | ESCALATE | True | True |
| D026 | failed_but_debited | blurred | REFUND | REFUND | True | True |
| D027 | unknown_txn | low_contrast | ESCALATE | ESCALATE | True | True |
| D028 | clean | clean | NO_ACTION | NO_ACTION | True | True |
| D029 | duplicate_debit | rotated | REFUND | REFUND | True | True |
| D030 | already_refunded | blurred | NO_ACTION | NO_ACTION | True | True |

## Failures

None in this run.

The separate adversarial verifier tests inject nonexistent, wrong-transaction, duplicate,
wrong-amount, wrong-date and wrong-status citations. They are not included in the
clean-fixture citation-validity denominator above.
