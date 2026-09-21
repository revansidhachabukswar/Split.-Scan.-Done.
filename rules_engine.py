"""
Rule engine for estimating UPI/MDR treatment.

IMPORTANT — legal/product framing:
This module produces an *informational estimate* only. It must never be
presented as a guarantee, and it must never be described as a tax or as a
way to avoid a tax. MDR is a payment-system charge, not a government tax.
All figures come from the `payment_rules` table (configurable, dated,
sourced) rather than being hard-coded here, because payment-network rules
change over time.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from .models import MerchantCategory, PaymentRule

DISCLAIMER = (
    "Applicable UPI/MDR treatment depends on the merchant category, transaction "
    "type, merchant status and current payment-network rules. Splitting a "
    "payment does not guarantee that MDR or other charges will not apply."
)


def _active_rules(db: Session):
    now = datetime.utcnow()
    rules = (
        db.query(PaymentRule)
        .filter(PaymentRule.status == "ACTIVE")
        .filter(PaymentRule.effective_date <= now)
        .all()
    )
    return [r for r in rules if r.expiry_date is None or r.expiry_date >= now]


def classify_payment_type(amount: float, merchant_category: Optional[str], hint: Optional[str]) -> str:
    """Determine which bucket a transaction falls into. A merchant-supplied
    hint (e.g. explicitly flagging a P2P transfer) is honoured when given;
    otherwise every amount entered on the merchant dashboard is treated as
    a P2M (person-to-merchant) payment, since that is what this product is for."""
    if hint:
        return hint.upper()
    return "P2M"


def find_matching_rule(db: Session, amount: float, payment_type: str, merchant_category: Optional[str]) -> Optional[PaymentRule]:
    candidates = [r for r in _active_rules(db) if r.payment_type == payment_type]

    # Prefer a rule scoped to this merchant's exact category over a generic one.
    category_specific = [r for r in candidates if r.merchant_category and merchant_category and r.merchant_category.lower() == merchant_category.lower()]
    generic = [r for r in candidates if not r.merchant_category]

    pool = category_specific or generic or candidates
    # Among the pool, pick the highest threshold that the amount still clears
    # (i.e. the most specific applicable bracket).
    applicable = [r for r in pool if amount > (r.threshold_amount or 0)]
    if not applicable:
        # amount doesn't clear any threshold -> pick the rule with the lowest threshold (e.g. "up to X" bracket)
        applicable = sorted(pool, key=lambda r: (r.threshold_amount or 0))
        return applicable[0] if applicable else None

    applicable.sort(key=lambda r: r.threshold_amount or 0, reverse=True)
    return applicable[0]


def estimate_mdr(amount: float, rule: Optional[PaymentRule]) -> float:
    if rule is None:
        return 0.0
    if rule.fixed_mdr is not None:
        estimated = rule.fixed_mdr
    else:
        estimated = amount * (rule.mdr_percentage / 100.0)
    if rule.maximum_mdr is not None:
        estimated = min(estimated, rule.maximum_mdr)
    return round(estimated, 2)


def analyze(db: Session, amount: float, merchant_category: Optional[str], hint: Optional[str] = None) -> dict:
    payment_type = classify_payment_type(amount, merchant_category, hint)
    rule = find_matching_rule(db, amount, payment_type, merchant_category)
    estimated = estimate_mdr(amount, rule)
    return {
        "amount": amount,
        "payment_type": payment_type,
        "matched_rule_name": rule.rule_name if rule else None,
        "matched_rule_id": rule.id if rule else None,
        "threshold": rule.threshold_amount if rule else 0.0,
        "estimated_mdr": estimated,
        "disclaimer": DISCLAIMER,
    }
