# Synthetic operations extension evaluation

Seeded synthetic-only validation. Models share simulator assumptions. Route trials are counterfactual, not independent production payments. No production improvement, cash recovery or physical microphone QA is claimed. Voice loopback results are separate. New agents are excluded from the original 608-case replay denominator.

## Measured results

```json
{
  "synthetic": true,
  "transaction_count": 512,
  "test_seed": 916,
  "clean_lifecycle_no_gap": {
    "passed": 288,
    "sample_size": 288,
    "95_wilson": [
      0.9868366949742601,
      1
    ]
  },
  "injected_gap_detection": {
    "passed": 96,
    "sample_size": 96,
    "95_wilson": [
      0.9615230525151842,
      1
    ]
  },
  "fee_audit": {
    "true_positives": 64,
    "predicted_claims": 64,
    "actual_discrepancies": 64,
    "precision": 1.0,
    "recall": 1.0,
    "precision_95_wilson": [
      0.9433739770288436,
      1
    ],
    "recall_95_wilson": [
      0.9433739770288436,
      1
    ]
  },
  "outage_route_contexts": [
    {
      "rail": "UPI",
      "outage": true,
      "routes": [
        {
          "route": "SYN-ROUTE-A",
          "sample_size": 256,
          "successes": 62,
          "success_rate": 0.2421875,
          "success_95_wilson": [
            0.19376934077577512,
            0.2982288612057398
          ],
          "cost_paise": 2560,
          "cost_per_trial_paise": "10",
          "linucb_score": 0.2564886995559504
        },
        {
          "route": "SYN-ROUTE-B",
          "sample_size": 256,
          "successes": 225,
          "success_rate": 0.87890625,
          "success_95_wilson": [
            0.8332433372210819,
            0.9133653659272978
          ],
          "cost_paise": 5120,
          "cost_per_trial_paise": "20",
          "linucb_score": 0.8913807671762398
        }
      ],
      "current_route": "SYN-ROUTE-A"
    }
  ],
  "bounded_outage_proposals": [
    {
      "shift": 0.1,
      "simulated_success_uplift": 0.063671875,
      "sample_sizes": {
        "SYN-ROUTE-A": 256,
        "SYN-ROUTE-B": 256
      },
      "routing_executed": false
    }
  ],
  "autonomy_replay": {
    "synthetic": true,
    "transaction_count": 512,
    "case_count": 608,
    "test_seed": 916,
    "selected": {
      "threshold": 0.95,
      "auto_resolved": 224,
      "human_review": 384,
      "auto_resolve_rate": 0.3684210526315789,
      "human_review_rate": 0.631578947368421,
      "false_auto_resolutions": 0,
      "false_auto_resolution_rate": 0.0,
      "false_auto_resolution_95_wilson": [
        0,
        0.01686083665142801
      ]
    },
    "curve": [
      {
        "threshold": 0.7,
        "auto_resolved": 288,
        "human_review": 320,
        "auto_resolve_rate": 0.47368421052631576,
        "human_review_rate": 0.5263157894736843,
        "false_auto_resolutions": 0,
        "false_auto_resolution_rate": 0.0,
        "false_auto_resolution_95_wilson": [
          0,
          0.01316330502573999
        ]
      },
      {
        "threshold": 0.75,
        "auto_resolved": 288,
        "human_review": 320,
        "auto_resolve_rate": 0.47368421052631576,
        "human_review_rate": 0.5263157894736843,
        "false_auto_resolutions": 0,
        "false_auto_resolution_rate": 0.0,
        "false_auto_resolution_95_wilson": [
          0,
          0.01316330502573999
        ]
      },
      {
        "threshold": 0.8,
        "auto_resolved": 288,
        "human_review": 320,
        "auto_resolve_rate": 0.47368421052631576,
        "human_review_rate": 0.5263157894736843,
        "false_auto_resolutions": 0,
        "false_auto_resolution_rate": 0.0,
        "false_auto_resolution_95_wilson": [
          0,
          0.01316330502573999
        ]
      },
      {
        "threshold": 0.85,
        "auto_resolved": 288,
        "human_review": 320,
        "auto_resolve_rate": 0.47368421052631576,
        "human_review_rate": 0.5263157894736843,
        "false_auto_resolutions": 0,
        "false_auto_resolution_rate": 0.0,
        "false_auto_resolution_95_wilson": [
          0,
          0.01316330502573999
        ]
      },
      {
        "threshold": 0.9,
        "auto_resolved": 224,
        "human_review": 384,
        "auto_resolve_rate": 0.3684210526315789,
        "human_review_rate": 0.631578947368421,
        "false_auto_resolutions": 0,
        "false_auto_resolution_rate": 0.0,
        "false_auto_resolution_95_wilson": [
          0,
          0.01686083665142801
        ]
      },
      {
        "threshold": 0.95,
        "auto_resolved": 224,
        "human_review": 384,
        "auto_resolve_rate": 0.3684210526315789,
        "human_review_rate": 0.631578947368421,
        "false_auto_resolutions": 0,
        "false_auto_resolution_rate": 0.0,
        "false_auto_resolution_95_wilson": [
          0,
          0.01686083665142801
        ]
      },
      {
        "threshold": 0.99,
        "auto_resolved": 160,
        "human_review": 448,
        "auto_resolve_rate": 0.2631578947368421,
        "human_review_rate": 0.736842105263158,
        "false_auto_resolutions": 0,
        "false_auto_resolution_rate": 0.0,
        "false_auto_resolution_95_wilson": [
          0,
          0.023447036650032713
        ]
      }
    ],
    "stored_thresholds_changed": false,
    "scope": "Original reconciliation/dispute/fraud holdout only; new fee/routing agents are not added to the 608-case denominator.",
    "guardrails": "Restricted actions remain human-only at every threshold. No ledger, threshold or audit history is changed by replay.",
    "limitation": "Counterfactual synthetic results with shared generator assumptions, not deployment advice or production risk estimates."
  },
  "security_database_findings": 0,
  "limitations": "Seeded synthetic-only validation. Models share simulator assumptions. Route trials are counterfactual, not independent production payments. No production improvement, cash recovery or physical microphone QA is claimed. Voice loopback results are separate. New agents are excluded from the original 608-case replay denominator."
}
```
