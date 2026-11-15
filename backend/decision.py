"""Shared agent decision contract and configurable financial review policy."""
from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

AgentAction = Literal['RECONCILE', 'INVESTIGATE', 'REFUND_REVIEW', 'FIGHT', 'ACCEPT',
                      'MERCHANT_REVIEW', 'RESTRICT_PAYMENTS', 'KILL_SWITCH',
                      'ARBITRATION', 'WRITE_OFF', 'POLICY_CHANGE', 'NO_ACTION', 'RAISE_CLAIM', 'ROUTING_CHANGE']


class Decision(BaseModel):
    model_config = ConfigDict(extra='forbid')
    action: AgentAction
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    reasoning: str = Field(min_length=1)
    evidence: list[str] = Field(min_length=1)
    amount: Decimal = Field(ge=0, max_digits=16, decimal_places=2)
    case_id: str = Field(min_length=1, max_length=120)


@dataclass(frozen=True)
class Policy:
    auto: float = 0.95
    review: float = 0.70
    high_value: Decimal = Decimal('50000')
    write_off: Decimal = Decimal('5000')

    def __post_init__(self) -> None:
        if not 0 <= self.review <= self.auto <= 1 or self.high_value <= 0 or self.write_off < 0:
            raise ValueError('Invalid review policy thresholds')

    @classmethod
    def configured(cls) -> 'Policy':
        return cls(float(os.getenv('AUTO_RESOLVE_THRESHOLD') or '.95'),
                   float(os.getenv('HUMAN_REVIEW_THRESHOLD') or '.70'),
                   Decimal(os.getenv('HIGH_VALUE_THRESHOLD') or '50000'),
                   Decimal(os.getenv('WRITE_OFF_LIMIT') or '5000'))

    def gate(self, decision: Decision) -> str:
        mandatory = {'KILL_SWITCH', 'ARBITRATION', 'POLICY_CHANGE', 'RESTRICT_PAYMENTS', 'RAISE_CLAIM','ROUTING_CHANGE'}
        if (decision.action in mandatory or decision.amount >= self.high_value or
                decision.action == 'WRITE_OFF' and decision.amount > self.write_off):
            return 'EXPERT_QUEUE'
        if decision.confidence < self.review:
            return 'EXPERT_QUEUE'
        # Only evidence-backed bookkeeping/no-action is eligible for automation.
        if decision.confidence >= self.auto and decision.action in {'RECONCILE', 'NO_ACTION'}:
            return 'AUTO_RESOLVED'
        return 'ONE_CLICK_REVIEW'
