from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import require_admin
from ..database import get_db
from ..models import AuditLog, PaymentRule, User

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/rules", response_model=List[schemas.PaymentRuleOut])
def admin_list_rules(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return db.query(PaymentRule).order_by(PaymentRule.created_at.desc()).all()


@router.post("/rules", response_model=schemas.PaymentRuleOut)
def admin_create_rule(payload: schemas.PaymentRuleCreateRequest, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    rule = PaymentRule(
        rule_name=payload.rule_name,
        payment_type=payload.payment_type,
        merchant_category=payload.merchant_category,
        threshold_amount=payload.threshold_amount,
        mdr_percentage=payload.mdr_percentage,
        fixed_mdr=payload.fixed_mdr,
        maximum_mdr=payload.maximum_mdr,
        effective_date=payload.effective_date or datetime.utcnow(),
        expiry_date=payload.expiry_date,
        status=payload.status,
        source_reference=payload.source_reference,
    )
    db.add(rule)
    db.add(AuditLog(user_id=admin.id, action="CREATE_RULE", details=f"Created rule {payload.rule_name}"))
    db.commit()
    db.refresh(rule)
    return rule


@router.put("/rules/{rule_id}", response_model=schemas.PaymentRuleOut)
def admin_update_rule(rule_id: str, payload: schemas.PaymentRuleCreateRequest, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    rule = db.query(PaymentRule).filter(PaymentRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(rule, field, value)
    rule.updated_at = datetime.utcnow()
    db.add(AuditLog(user_id=admin.id, action="UPDATE_RULE", details=f"Updated rule {rule_id}"))
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}")
def admin_deactivate_rule(rule_id: str, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    rule = db.query(PaymentRule).filter(PaymentRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    rule.status = "INACTIVE"
    db.add(AuditLog(user_id=admin.id, action="DEACTIVATE_RULE", details=f"Deactivated rule {rule_id}"))
    db.commit()
    return {"detail": "Rule deactivated"}
