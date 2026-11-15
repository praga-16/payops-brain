# PayOps Brain control tower evaluation

Synthetic transactions: 512; agent cases: 608; seed: 916.

Match GB: 1,200 synthetic pairs seed 1701; break GB: 900 synthetic vectors seed 1702; dispute logistic: 2,000 synthetic outcomes seed 732; Isolation Forest: 800 normal vectors seed 991. No holdout ledger IDs or labels are used in training or inference.

| Metric | Rules-only | AI-assisted |
|---|---|---|
| auto_match_rate | 0.6250 | 0.8125 |
| break_classification_accuracy | 0.6875 | 1.0000 |
| dispute_win_auc | 0.5000 | 0.6745 |
| fraud_precision | 0.5000 | 0.5000 |
| fraud_recall | 1.0000 | 1.0000 |
| human_review_rate | 0.7368 | 0.6316 |
| false_auto_resolution_rate | 0.0000 | 0.0000 |

## Sample counts and confidence intervals

```json
{
  "samples": {
    "baseline": {
      "classified": 512,
      "correct": 352,
      "fraud_alerts": 64,
      "fraud_true_positives": 32,
      "actual_fraud": 32,
      "auto_resolutions": 160,
      "false_auto_resolutions": 0,
      "reviewed_cases": 448,
      "total_agent_cases": 608,
      "dispute_outcomes": 32,
      "dispute_wins": 24,
      "auto_linked_transactions": 320
    },
    "assisted": {
      "classified": 512,
      "correct": 512,
      "fraud_alerts": 64,
      "fraud_true_positives": 32,
      "actual_fraud": 32,
      "auto_resolutions": 224,
      "false_auto_resolutions": 0,
      "reviewed_cases": 384,
      "total_agent_cases": 608,
      "dispute_outcomes": 32,
      "dispute_wins": 24,
      "auto_linked_transactions": 416
    }
  },
  "intervals": {
    "baseline": {
      "break_accuracy_95_wilson": [
        0.6460793438632031,
        0.7261279383722739
      ],
      "fraud_precision_95_wilson": [
        0.38101888493214947,
        0.6189811150678505
      ],
      "false_auto_resolution_95_wilson": [
        0,
        0.023447036650032713
      ]
    },
    "assisted": {
      "break_accuracy_95_wilson": [
        0.9925527526279385,
        1
      ],
      "fraud_precision_95_wilson": [
        0.38101888493214947,
        0.6189811150678505
      ],
      "false_auto_resolution_95_wilson": [
        0,
        0.01686083665142801
      ]
    }
  }
}
```

## Metric definitions

- auto_match_rate: Reference links with match score >= .95 / all transactions; fuzzy suggestions remain reviewed.
- false_auto_resolution_rate: Incorrect CLEAN bookkeeping auto-resolutions / all auto-resolutions.
- human_review_rate: Non-auto decisions / reconciliation, dispute and fraud cases.
- baseline: Exact-reference reconciliation, deterministic break/fraud rules, constant win prior (.5 AUC).
- assisted: Normalized/fuzzy GB matching, GB break classification, logistic win estimate, Isolation Forest plus rules.

## Limitations

Synthetic-demo validation only. Training and test seeds differ but share generator assumptions. Heuristic confidence is not a calibrated real-world probability. Fraud labels identify injected bursts; over-refund alerts count as false positives for this narrow target. No OCR/LLM quality benchmark. Observed gains or losses do not imply production performance. Feedback calibration is reported separately.
