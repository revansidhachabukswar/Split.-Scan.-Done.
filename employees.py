from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import hash_password, require_owner_or_admin
from ..database import get_db
from ..models import RoleEnum, User

router = APIRouter(prefix="/api/employees", tags=["employees"])


@router.get("", response_model=List[schemas.EmployeeOut])
def list_employees(db: Session = Depends(get_db), owner: User = Depends(require_owner_or_admin)):
    return db.query(User).filter(User.merchant_id == owner.merchant_id, User.role == RoleEnum.employee).all()


@router.post("", response_model=schemas.EmployeeOut)
def create_employee(payload: schemas.EmployeeCreateRequest, db: Session = Depends(get_db), owner: User = Depends(require_owner_or_admin)):
    existing = db.query(User).filter(User.mobile_number == payload.mobile_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this mobile number already exists")
    employee = User(
        full_name=payload.full_name,
        mobile_number=payload.mobile_number,
        password_hash=hash_password(payload.password),
        role=RoleEnum.employee,
        merchant_id=owner.merchant_id,
        branch_id=payload.branch_id,
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


@router.patch("/{employee_id}/deactivate")
def deactivate_employee(employee_id: str, db: Session = Depends(get_db), owner: User = Depends(require_owner_or_admin)):
    employee = db.query(User).filter(User.id == employee_id, User.merchant_id == owner.merchant_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    employee.is_active = False
    db.commit()
    return {"detail": "Employee deactivated"}
