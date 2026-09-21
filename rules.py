from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..models import PaymentRule

router = APIRouter(prefix="/api/rules", tags=["rules"])


@router.get("", response_model=List[schemas.PaymentRuleOut])
def list_active_rules(db: Session = Depends(get_db)):
    """Publicly viewable — merchants and customers can always see the
    currently configured rules and their effective dates, per product policy."""
    rules = db.query(PaymentRule).filter(PaymentRule.status == "ACTIVE").order_by(PaymentRule.payment_type, PaymentRule.threshold_amount).all()
    return rules
