from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import get_current_user
from ..database import get_db
from ..models import Merchant, PaymentEventStatus, Transaction, TransactionPart, User

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=schemas.DashboardResponse)
def get_dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    merchant = db.query(Merchant).filter(Merchant.id == user.merchant_id).first()

    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    all_txns = db.query(Transaction).filter(Transaction.merchant_id == merchant.id).all()
    today_txns = [t for t in all_txns if t.created_at >= today_start]

    today_sales = sum(t.total_amount for t in today_txns if t.status.value == "SUCCESS")
    today_transaction_count = len(today_txns)

    pending_parts = (
        db.query(TransactionPart)
        .join(Transaction, Transaction.id == TransactionPart.transaction_id)
        .filter(Transaction.merchant_id == merchant.id)
        .filter(TransactionPart.status == PaymentEventStatus.pending)
        .all()
    )
    pending_payments = len(pending_parts)
    pending_amount = sum(p.amount for p in pending_parts)

    total_qr_plans = len(all_txns)
    total_installments = sum(t.number_of_parts for t in all_txns)
    completed_amounts = [t.total_amount for t in all_txns if t.status.value == "SUCCESS"]
    average_payment = (sum(completed_amounts) / len(completed_amounts)) if completed_amounts else 0.0

    # last 7 days of sales for a simple chart
    daily_sales = []
    for i in range(6, -1, -1):
        day = (now - timedelta(days=i)).date()
        day_total = sum(
            t.total_amount for t in all_txns
            if t.status.value == "SUCCESS" and t.created_at.date() == day
        )
        daily_sales.append({"date": day.isoformat(), "sales": day_total})

    return schemas.DashboardResponse(
        business_name=merchant.business_name,
        today_sales=today_sales,
        today_transactions=today_transaction_count,
        pending_payments=pending_payments,
        total_qr_plans=total_qr_plans,
        total_installments=total_installments,
        average_payment=round(average_payment, 2),
        pending_amount=pending_amount,
        daily_sales=daily_sales,
    )
