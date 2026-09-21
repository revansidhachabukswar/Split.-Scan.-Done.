from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------- Auth / Registration ----------

class MerchantRegisterRequest(BaseModel):
    business_name: str
    merchant_upi_id: str
    mobile_number: Optional[str] = None
    business_category: Optional[str] = None
    owner_name: str
    password: str = Field(min_length=6)


class LoginRequest(BaseModel):
    mobile_number: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    merchant_id: Optional[str] = None
    role: str


# ---------- Employees ----------

class EmployeeCreateRequest(BaseModel):
    full_name: str
    mobile_number: str
    password: str = Field(min_length=6)
    branch_id: Optional[str] = None


class EmployeeOut(BaseModel):
    id: str
    full_name: str
    mobile_number: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


# ---------- Payment analysis / split ----------

class AnalyzeRequest(BaseModel):
    amount: float = Field(gt=0)
    payment_type_hint: Optional[str] = None  # P2P | P2M | ESSENTIAL | CAPITAL_MARKET


class AnalyzeResponse(BaseModel):
    amount: float
    payment_type: str
    matched_rule_name: Optional[str]
    threshold: float
    estimated_mdr: float
    disclaimer: str


class SplitRequest(BaseModel):
    amount: float = Field(gt=0)
    mode: str = "standard"  # standard | equal | custom
    max_installment: Optional[float] = None
    num_parts: Optional[int] = None  # used for 'equal'
    custom_parts: Optional[List[float]] = None  # used for 'custom'


class SplitResponse(BaseModel):
    amount: float
    mode: str
    parts: List[float]


class GenerateQrRequest(BaseModel):
    amount: float = Field(gt=0)
    mode: str = "standard"
    max_installment: Optional[float] = None
    num_parts: Optional[int] = None
    custom_parts: Optional[List[float]] = None
    customer_name: Optional[str] = None
    customer_mobile: Optional[str] = None
    order_number: Optional[str] = None
    branch_id: Optional[str] = None


class TransactionPartOut(BaseModel):
    id: str
    part_index: int
    amount: float
    upi_uri: str
    qr_base64: str
    status: str

    class Config:
        from_attributes = True


class TransactionOut(BaseModel):
    id: str
    invoice_number: str
    total_amount: float
    number_of_parts: int
    split_mode: str
    payment_type: Optional[str]
    estimated_mdr_total: float
    status: str
    customer_name: Optional[str]
    created_at: datetime
    parts: List[TransactionPartOut]

    class Config:
        from_attributes = True


class MarkReceivedRequest(BaseModel):
    part_id: str


# ---------- Transactions / history ----------

class TransactionSummaryOut(BaseModel):
    id: str
    invoice_number: str
    total_amount: float
    number_of_parts: int
    status: str
    customer_name: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Dashboard ----------

class DashboardResponse(BaseModel):
    business_name: str
    today_sales: float
    today_transactions: int
    pending_payments: int
    total_qr_plans: int
    total_installments: int
    average_payment: float
    pending_amount: float
    daily_sales: List[dict]


# ---------- Rules ----------

class PaymentRuleOut(BaseModel):
    id: str
    rule_name: str
    payment_type: str
    merchant_category: Optional[str]
    threshold_amount: float
    mdr_percentage: float
    fixed_mdr: Optional[float]
    maximum_mdr: Optional[float]
    effective_date: datetime
    expiry_date: Optional[datetime]
    status: str
    source_reference: Optional[str]

    class Config:
        from_attributes = True


class PaymentRuleCreateRequest(BaseModel):
    rule_name: str
    payment_type: str
    merchant_category: Optional[str] = None
    threshold_amount: float = 0.0
    mdr_percentage: float = 0.0
    fixed_mdr: Optional[float] = None
    maximum_mdr: Optional[float] = None
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    status: str = "ACTIVE"
    source_reference: Optional[str] = None


# ---------- AI assistant ----------

class AssistantQueryRequest(BaseModel):
    question: str


class AssistantQueryResponse(BaseModel):
    answer: str
    data_used: dict
