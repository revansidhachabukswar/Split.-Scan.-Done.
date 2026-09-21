from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import create_access_token, hash_password, verify_password
from ..database import get_db
from ..models import Branch, Merchant, RoleEnum, User

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=schemas.TokenResponse)
def register(payload: schemas.MerchantRegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.mobile_number == payload.mobile_number).first()
    if payload.mobile_number and existing:
        raise HTTPException(status_code=400, detail="An account with this mobile number already exists")

    merchant = Merchant(
        business_name=payload.business_name,
        upi_id=payload.merchant_upi_id,
        mobile_number=payload.mobile_number,
        business_category=payload.business_category,
    )
    db.add(merchant)
    db.flush()  # get merchant.id

    branch = Branch(merchant_id=merchant.id, name="Main", upi_id=payload.merchant_upi_id)
    db.add(branch)

    user = User(
        full_name=payload.owner_name,
        mobile_number=payload.mobile_number,
        password_hash=hash_password(payload.password),
        role=RoleEnum.owner,
        merchant_id=merchant.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.id, "role": user.role.value, "merchant_id": merchant.id})
    return schemas.TokenResponse(access_token=token, merchant_id=merchant.id, role=user.role.value)


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.mobile_number == payload.mobile_number).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid mobile number or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    token = create_access_token({"sub": user.id, "role": user.role.value, "merchant_id": user.merchant_id})
    return schemas.TokenResponse(access_token=token, merchant_id=user.merchant_id, role=user.role.value)
