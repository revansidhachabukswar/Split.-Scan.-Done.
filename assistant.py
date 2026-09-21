"""
AI business assistant — analytics and explanations only.

Design constraint: every number in a response must come from an actual
database query. This module never lets a language model invent transaction
figures. If AI_API_KEY is configured, it may be used purely to phrase the
answer in natural language around numbers we already computed ourselves —
never to generate the numbers.
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import get_current_user
from ..database import get_db
from ..models import Transaction, User

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


def _today_range():
    now = datetime.utcnow()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, now


@router.post("/query", response_model=schemas.AssistantQueryResponse)
def query_assistant(payload: schemas.AssistantQueryRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = payload.question.lower()
    txns = db.query(Transaction).filter(Transaction.merchant_id == user.merchant_id).all()
    completed = [t for t in txns if t.status.value == "SUCCESS"]

    if "today" in q and ("collect" in q or "sales" in q or "sold" in q):
        start, _ = _today_range()
        today_txns = [t for t in completed if t.created_at >= start]
        total = sum(t.total_amount for t in today_txns)
        data = {"count": len(today_txns), "total": total}
        answer = f"Your recorded completed transactions today total Rs. {total:,.2f} across {len(today_txns)} transactions."
        return schemas.AssistantQueryResponse(answer=answer, data_used=data)

    if "week" in q:
        start = datetime.utcnow() - timedelta(days=7)
        week_txns = [t for t in completed if t.created_at >= start]
        total = sum(t.total_amount for t in week_txns)
        data = {"count": len(week_txns), "total": total}
        answer = f"Over the last 7 days you collected Rs. {total:,.2f} across {len(week_txns)} completed transactions."
        return schemas.AssistantQueryResponse(answer=answer, data_used=data)

    if "biggest" in q or "largest" in q or "highest" in q and "day" not in q:
        top = sorted(completed, key=lambda t: t.total_amount, reverse=True)[:5]
        data = {"transactions": [{"amount": t.total_amount, "date": t.created_at.isoformat()} for t in top]}
        if not top:
            return schemas.AssistantQueryResponse(answer="You don't have any completed transactions yet.", data_used=data)
        lines = ", ".join(f"Rs. {t.total_amount:,.2f}" for t in top)
        return schemas.AssistantQueryResponse(answer=f"Your biggest recorded transactions are: {lines}.", data_used=data)

    if "highest" in q and "day" in q:
        by_day = {}
        for t in completed:
            d = t.created_at.date().isoformat()
            by_day[d] = by_day.get(d, 0) + t.total_amount
        if not by_day:
            return schemas.AssistantQueryResponse(answer="No completed transactions recorded yet.", data_used={})
        best_day = max(by_day.items(), key=lambda kv: kv[1])
        return schemas.AssistantQueryResponse(
            answer=f"Your highest sales day so far was {best_day[0]} with Rs. {best_day[1]:,.2f} collected.",
            data_used={"by_day": by_day},
        )

    if "pending" in q:
        pending = [t for t in txns if t.status.value == "PENDING"]
        total_pending = sum(p.amount for t in pending for p in t.parts if p.status.value == "PENDING")
        data = {"pending_transactions": len(pending), "pending_amount": total_pending}
        return schemas.AssistantQueryResponse(
            answer=f"You have {len(pending)} transaction(s) with pending payments, totalling Rs. {total_pending:,.2f}.",
            data_used=data,
        )

    if "above" in q:
        import re
        match = re.search(r"[\d,]+", q)
        if match:
            threshold = float(match.group().replace(",", ""))
            above = [t for t in completed if t.total_amount > threshold]
            data = {"count": len(above), "threshold": threshold}
            return schemas.AssistantQueryResponse(
                answer=f"You have {len(above)} completed transaction(s) above Rs. {threshold:,.2f}.",
                data_used=data,
            )

    total_all = sum(t.total_amount for t in completed)
    return schemas.AssistantQueryResponse(
        answer=(
            f"I can answer questions about your recorded transactions (currently {len(completed)} completed, "
            f"totalling Rs. {total_all:,.2f}). Try asking things like 'How much did I collect today?', "
            f"'Show my biggest transactions', or 'Show pending payments'."
        ),
        data_used={"total_completed_transactions": len(completed), "total_collected": total_all},
    )
