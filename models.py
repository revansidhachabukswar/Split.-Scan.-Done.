import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer,
    String, Text, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class RoleEnum(str, enum.Enum):
    owner = "owner"
    employee = "employee"
    admin = "admin"


class TransactionStatus(str, enum.Enum):
    pending = "PENDING"
    success = "SUCCESS"
    failed = "FAILED"
    expired = "EXPIRED"


class PaymentEventStatus(str, enum.Enum):
    pending = "PENDING"
    marked_received = "MARKED_RECEIVED"
    success = "SUCCESS"
    failed = "FAILED"
    expired = "EXPIRED"


class SplitMode(str, enum.Enum):
    standard = "standard"
    equal = "equal"
    custom = "custom"


class User(Base):
    """Login identity. Every merchant owner and every employee is a User."""
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    full_name = Column(String, nullable=False)
    mobile_number = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.owner, nullable=False)
    merchant_id = Column(String, ForeignKey("merchants.id"), nullable=True)
    branch_id = Column(String, ForeignKey("branches.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    merchant = relationship("Merchant", back_populates="owner_user", foreign_keys=[merchant_id])


class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(String, primary_key=True, default=gen_uuid)
    business_name = Column(String, nullable=False)
    upi_id = Column(String, nullable=False)
    mobile_number = Column(String, nullable=True)
    business_category = Column(String, nullable=True)
    default_max_installment = Column(Float, default=2000.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner_user = relationship("User", back_populates="merchant", uselist=False, foreign_keys=[User.merchant_id])
    branches = relationship("Branch", back_populates="merchant", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="merchant", cascade="all, delete-orphan")


class Branch(Base):
    """Multi-branch support. Every merchant gets an implicit 'Main' branch on registration."""
    __tablename__ = "branches"

    id = Column(String, primary_key=True, default=gen_uuid)
    merchant_id = Column(String, ForeignKey("merchants.id"), nullable=False)
    name = Column(String, nullable=False, default="Main")
    upi_id = Column(String, nullable=True)  # overrides merchant UPI ID if set
    address = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    merchant = relationship("Merchant", back_populates="branches")


class MerchantCategory(Base):
    __tablename__ = "merchant_categories"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, unique=True, nullable=False)
    is_essential_sector = Column(Boolean, default=False)
    is_capital_market = Column(Boolean, default=False)
    description = Column(String, nullable=True)


class PaymentRule(Base):
    """
    Configurable, database-driven MDR rule. Never hard-code rules into
    application logic — the rule engine reads from this table at runtime.
    """
    __tablename__ = "payment_rules"

    id = Column(String, primary_key=True, default=gen_uuid)
    rule_name = Column(String, nullable=False)
    payment_type = Column(String, nullable=False)  # P2P | P2M | ESSENTIAL | CAPITAL_MARKET
    merchant_category = Column(String, nullable=True)  # null = applies to all categories
    threshold_amount = Column(Float, default=0.0)  # rule applies above this amount
    mdr_percentage = Column(Float, default=0.0)
    fixed_mdr = Column(Float, nullable=True)  # flat fee instead of percentage, if set
    maximum_mdr = Column(Float, nullable=True)  # cap, if any
    effective_date = Column(DateTime, default=datetime.utcnow)
    expiry_date = Column(DateTime, nullable=True)
    status = Column(String, default="ACTIVE")  # ACTIVE | INACTIVE
    source_reference = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String, primary_key=True, default=gen_uuid)
    invoice_number = Column(String, unique=True, nullable=False)
    merchant_id = Column(String, ForeignKey("merchants.id"), nullable=False)
    transaction_id = Column(String, ForeignKey("transactions.id"), nullable=False)
    customer_name = Column(String, nullable=True)
    customer_mobile = Column(String, nullable=True)
    order_number = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, default=gen_uuid)
    merchant_id = Column(String, ForeignKey("merchants.id"), nullable=False)
    branch_id = Column(String, ForeignKey("branches.id"), nullable=True)
    created_by_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    total_amount = Column(Float, nullable=False)
    number_of_parts = Column(Integer, nullable=False)
    split_mode = Column(Enum(SplitMode), default=SplitMode.standard)
    payment_type = Column(String, nullable=True)  # snapshot of matched rule's payment_type
    rule_id = Column(String, ForeignKey("payment_rules.id"), nullable=True)
    estimated_mdr_total = Column(Float, default=0.0)
    customer_name = Column(String, nullable=True)
    customer_mobile = Column(String, nullable=True)
    order_number = Column(String, nullable=True)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.pending)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    merchant = relationship("Merchant", back_populates="transactions")
    parts = relationship("TransactionPart", back_populates="transaction", cascade="all, delete-orphan", order_by="TransactionPart.part_index")


class TransactionPart(Base):
    __tablename__ = "transaction_parts"

    id = Column(String, primary_key=True, default=gen_uuid)
    transaction_id = Column(String, ForeignKey("transactions.id"), nullable=False)
    part_index = Column(Integer, nullable=False)  # 1-based order
    amount = Column(Float, nullable=False)
    upi_uri = Column(Text, nullable=False)
    status = Column(Enum(PaymentEventStatus), default=PaymentEventStatus.pending)
    marked_received_at = Column(DateTime, nullable=True)

    transaction = relationship("Transaction", back_populates="parts")
    events = relationship("PaymentEvent", back_populates="part", cascade="all, delete-orphan")


class PaymentEvent(Base):
    """
    Audit trail of every status change for a transaction part. A production
    payment-provider webhook should write here instead of trusting client input.
    """
    __tablename__ = "payment_events"

    id = Column(String, primary_key=True, default=gen_uuid)
    transaction_part_id = Column(String, ForeignKey("transaction_parts.id"), nullable=False)
    event_type = Column(String, nullable=False)  # e.g. MANUAL_MARK_RECEIVED, WEBHOOK_SUCCESS
    status = Column(Enum(PaymentEventStatus), nullable=False)
    source = Column(String, default="manual")  # manual | webhook | system
    raw_payload = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    part = relationship("TransactionPart", back_populates="events")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
