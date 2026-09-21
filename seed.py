from datetime import datetime

from sqlalchemy.orm import Session

from .models import MerchantCategory, PaymentRule

DEFAULT_CATEGORIES = [
    ("General Retail", False, False, "Default category for most merchants"),
    ("Railways", True, False, "Essential / specified sector"),
    ("Telecommunications", True, False, "Essential / specified sector"),
    ("Insurance", True, False, "Essential / specified sector"),
    ("Fuel", True, False, "Essential / specified sector"),
    ("Agricultural Inputs", True, False, "Essential / specified sector"),
    ("Capital Markets / Broking", False, True, "Specified capital-market payments"),
]

EFFECTIVE = datetime(2026, 4, 1)

DEFAULT_RULES = [
    dict(
        rule_name="P2P Transfers - Free",
        payment_type="P2P",
        merchant_category=None,
        threshold_amount=0,
        mdr_percentage=0,
        fixed_mdr=0,
        maximum_mdr=None,
        source_reference="2026 UPI/MDR framework — person-to-person transfers remain free of MDR at any amount.",
    ),
    dict(
        rule_name="P2M up to Rs.2,000 - Zero MDR",
        payment_type="P2M",
        merchant_category=None,
        threshold_amount=0,
        mdr_percentage=0,
        fixed_mdr=0,
        maximum_mdr=None,
        source_reference="2026 UPI/MDR framework — merchant payments up to Rs.2,000 attract zero MDR.",
    ),
    dict(
        rule_name="Specified P2M above Rs.2,000",
        payment_type="P2M",
        merchant_category=None,
        threshold_amount=2000,
        mdr_percentage=0.4,
        fixed_mdr=None,
        maximum_mdr=300,
        source_reference="2026 UPI/MDR framework — 0.4% MDR on specified merchant payments above Rs.2,000, capped at Rs.300 (cap applies from Rs.75,000 and above).",
    ),
    dict(
        rule_name="Essential Sectors above Rs.2,000",
        payment_type="ESSENTIAL",
        merchant_category=None,
        threshold_amount=2000,
        mdr_percentage=0,
        fixed_mdr=5,
        maximum_mdr=5,
        source_reference="2026 UPI/MDR framework — flat Rs.5 MDR for specified essential/thin-margin sectors (railways, telecom, insurance, fuel, agri-inputs) above Rs.2,000.",
    ),
    dict(
        rule_name="Capital Market Transactions",
        payment_type="CAPITAL_MARKET",
        merchant_category=None,
        threshold_amount=0,
        mdr_percentage=0.02,
        fixed_mdr=None,
        maximum_mdr=300,
        source_reference="2026 UPI/MDR framework — 0.02% MDR on specified capital-market payments, capped at Rs.300.",
    ),
]


def seed_defaults(db: Session):
    if db.query(MerchantCategory).count() == 0:
        for name, essential, capital, desc in DEFAULT_CATEGORIES:
            db.add(MerchantCategory(name=name, is_essential_sector=essential, is_capital_market=capital, description=desc))

    if db.query(PaymentRule).count() == 0:
        for rule in DEFAULT_RULES:
            db.add(PaymentRule(effective_date=EFFECTIVE, status="ACTIVE", **rule))

    db.commit()
