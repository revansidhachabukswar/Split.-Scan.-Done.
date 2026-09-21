from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import get_current_user
from ..database import get_db
from ..models import Invoice, Transaction, User

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("", response_model=List[schemas.TransactionSummaryOut])
def list_transactions(
    period: Optional[str] = Query(None, description="today | week | month"),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(Transaction).filter(Transaction.merchant_id == user.merchant_id)

    now = datetime.utcnow()
    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        q = q.filter(Transaction.created_at >= start)
    elif period == "week":
        q = q.filter(Transaction.created_at >= now - timedelta(days=7))
    elif period == "month":
        q = q.filter(Transaction.created_at >= now - timedelta(days=30))

    if date_from:
        q = q.filter(Transaction.created_at >= date_from)
    if date_to:
        q = q.filter(Transaction.created_at <= date_to)
    if status:
        q = q.filter(Transaction.status == status)

    if search:
        like = f"%{search}%"
        q = q.join(Invoice, Invoice.transaction_id == Transaction.id, isouter=True).filter(
            or_(
                Invoice.invoice_number.ilike(like),
                Transaction.customer_name.ilike(like),
                Transaction.order_number.ilike(like),
            )
        )

    results = q.order_by(Transaction.created_at.desc()).limit(500).all()

    out = []
    for txn in results:
        invoice = db.query(Invoice).filter(Invoice.transaction_id == txn.id).first()
        out.append(schemas.TransactionSummaryOut(
            id=txn.id,
            invoice_number=invoice.invoice_number if invoice else txn.id[:8].upper(),
            total_amount=txn.total_amount,
            number_of_parts=txn.number_of_parts,
            status=txn.status.value,
            customer_name=txn.customer_name,
            created_at=txn.created_at,
        ))
    return out
