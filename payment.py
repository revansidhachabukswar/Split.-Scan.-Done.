from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import get_current_user
from ..database import get_db
from ..models import (
    Invoice, Merchant, PaymentEvent, PaymentEventStatus, Transaction,
    TransactionPart, TransactionStatus, User,
)
from ..qr_service import build_upi_uri, generate_qr_base64
from ..receipt_service import generate_invoice_number, generate_receipt_pdf
from ..rules_engine import analyze as run_rule_analysis
from ..split_engine import compute_split, validate_sum

router = APIRouter(prefix="/api/payment", tags=["payment"])


def _get_merchant(db: Session, user: User) -> Merchant:
    if not user.merchant_id:
        raise HTTPException(status_code=400, detail="This account is not linked to a merchant")
    merchant = db.query(Merchant).filter(Merchant.id == user.merchant_id).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return merchant


@router.post("/analyze", response_model=schemas.AnalyzeResponse)
def analyze_payment(payload: schemas.AnalyzeRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    merchant = _get_merchant(db, user)
    result = run_rule_analysis(db, payload.amount, merchant.business_category, payload.payment_type_hint)
    return schemas.AnalyzeResponse(
        amount=result["amount"],
        payment_type=result["payment_type"],
        matched_rule_name=result["matched_rule_name"],
        threshold=result["threshold"],
        estimated_mdr=result["estimated_mdr"],
        disclaimer=result["disclaimer"],
    )


@router.post("/split", response_model=schemas.SplitResponse)
def split_payment(payload: schemas.SplitRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    merchant = _get_merchant(db, user)
    parts = compute_split(
        amount=payload.amount,
        mode=payload.mode,
        max_installment=payload.max_installment,
        num_parts=payload.num_parts,
        custom_parts=payload.custom_parts,
        default_max_installment=merchant.default_max_installment,
    )
    validate_sum(payload.amount, parts)
    return schemas.SplitResponse(amount=payload.amount, mode=payload.mode, parts=parts)


@router.post("/generate-qr", response_model=schemas.TransactionOut)
def generate_qr(payload: schemas.GenerateQrRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    merchant = _get_merchant(db, user)

    parts_amounts = compute_split(
        amount=payload.amount,
        mode=payload.mode,
        max_installment=payload.max_installment,
        num_parts=payload.num_parts,
        custom_parts=payload.custom_parts,
        default_max_installment=merchant.default_max_installment,
    )
    validate_sum(payload.amount, parts_amounts)

    rule_result = run_rule_analysis(db, payload.amount, merchant.business_category)

    branch = None
    payee_upi = merchant.upi_id
    if payload.branch_id:
        from ..models import Branch
        branch = db.query(Branch).filter(Branch.id == payload.branch_id, Branch.merchant_id == merchant.id).first()
        if branch and branch.upi_id:
            payee_upi = branch.upi_id

    txn = Transaction(
        merchant_id=merchant.id,
        branch_id=payload.branch_id,
        created_by_user_id=user.id,
        total_amount=payload.amount,
        number_of_parts=len(parts_amounts),
        split_mode=payload.mode,
        payment_type=rule_result["payment_type"],
        rule_id=rule_result.get("matched_rule_id"),
        estimated_mdr_total=rule_result["estimated_mdr"],
        customer_name=payload.customer_name,
        customer_mobile=payload.customer_mobile,
        order_number=payload.order_number,
        status=TransactionStatus.pending,
    )
    db.add(txn)
    db.flush()

    for idx, amt in enumerate(parts_amounts, start=1):
        uri = build_upi_uri(payee_upi, merchant.business_name, amt, note=f"SplitPay {idx}/{len(parts_amounts)}")
        part = TransactionPart(
            transaction_id=txn.id,
            part_index=idx,
            amount=amt,
            upi_uri=uri,
            status=PaymentEventStatus.pending,
        )
        db.add(part)

    # sequence-based invoice number
    seq = db.query(Invoice).count() + 1
    invoice_number = generate_invoice_number(seq)
    invoice = Invoice(
        invoice_number=invoice_number,
        merchant_id=merchant.id,
        transaction_id=txn.id,
        customer_name=payload.customer_name,
        customer_mobile=payload.customer_mobile,
        order_number=payload.order_number,
    )
    db.add(invoice)
    db.commit()
    db.refresh(txn)

    return _serialize_transaction(txn, invoice_number)


def _serialize_transaction(txn: Transaction, invoice_number: str) -> schemas.TransactionOut:
    parts_out = []
    for p in txn.parts:
        qr_b64 = generate_qr_base64(p.upi_uri)
        parts_out.append(schemas.TransactionPartOut(
            id=p.id, part_index=p.part_index, amount=p.amount,
            upi_uri=p.upi_uri, qr_base64=qr_b64, status=p.status.value,
        ))
    return schemas.TransactionOut(
        id=txn.id, invoice_number=invoice_number, total_amount=txn.total_amount,
        number_of_parts=txn.number_of_parts, split_mode=txn.split_mode.value if hasattr(txn.split_mode, "value") else txn.split_mode,
        payment_type=txn.payment_type, estimated_mdr_total=txn.estimated_mdr_total,
        status=txn.status.value, customer_name=txn.customer_name,
        created_at=txn.created_at, parts=parts_out,
    )


@router.get("/{transaction_id}", response_model=schemas.TransactionOut)
def get_transaction(transaction_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    txn = db.query(Transaction).filter(Transaction.id == transaction_id, Transaction.merchant_id == user.merchant_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    invoice = db.query(Invoice).filter(Invoice.transaction_id == txn.id).first()
    return _serialize_transaction(txn, invoice.invoice_number if invoice else txn.id[:8].upper())


@router.post("/{transaction_id}/mark-received", response_model=schemas.TransactionOut)
def mark_received(transaction_id: str, payload: schemas.MarkReceivedRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Manual demo/MVP tracking only. This does NOT confirm a real payment was
    made — it exists so a merchant can track collection during the pilot.
    A production deployment should instead have an authorized payment-provider
    webhook write PaymentEvent rows with source='webhook'.
    """
    txn = db.query(Transaction).filter(Transaction.id == transaction_id, Transaction.merchant_id == user.merchant_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    part = db.query(TransactionPart).filter(TransactionPart.id == payload.part_id, TransactionPart.transaction_id == txn.id).first()
    if not part:
        raise HTTPException(status_code=404, detail="Payment part not found")

    from datetime import datetime
    part.status = PaymentEventStatus.marked_received
    part.marked_received_at = datetime.utcnow()
    db.add(PaymentEvent(transaction_part_id=part.id, event_type="MANUAL_MARK_RECEIVED", status=PaymentEventStatus.marked_received, source="manual"))

    db.flush()
    all_received = all(p.status == PaymentEventStatus.marked_received for p in txn.parts)
    if all_received:
        txn.status = TransactionStatus.success
    db.commit()
    db.refresh(txn)

    invoice = db.query(Invoice).filter(Invoice.transaction_id == txn.id).first()
    return _serialize_transaction(txn, invoice.invoice_number if invoice else txn.id[:8].upper())


@router.get("/{transaction_id}/receipt.pdf")
def download_receipt(transaction_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    txn = db.query(Transaction).filter(Transaction.id == transaction_id, Transaction.merchant_id == user.merchant_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    merchant = db.query(Merchant).filter(Merchant.id == txn.merchant_id).first()
    pdf_bytes = generate_receipt_pdf(txn, merchant.business_name)
    return Response(content=pdf_bytes, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="receipt-{transaction_id[:8]}.pdf"'
    })
