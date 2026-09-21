"""Configurable payment-split engine. All modes must always satisfy:
    sum(parts) == total amount (to the paisa, i.e. rounded to 2 decimals)
"""
import math
from typing import List, Optional

from fastapi import HTTPException


def _round2(x: float) -> float:
    return round(x + 1e-9, 2)


def standard_split(amount: float, max_installment: float) -> List[float]:
    if max_installment <= 0:
        raise HTTPException(status_code=400, detail="max_installment must be greater than 0")
    if amount <= max_installment:
        return [_round2(amount)]

    num_full = int(amount // max_installment)
    remainder = _round2(amount - num_full * max_installment)

    parts = [max_installment] * num_full
    if remainder > 0:
        parts.append(remainder)
    return [_round2(p) for p in parts]


def equal_split(amount: float, num_parts: int) -> List[float]:
    if num_parts <= 0:
        raise HTTPException(status_code=400, detail="num_parts must be greater than 0")
    base = math.floor((amount / num_parts) * 100) / 100
    parts = [base] * num_parts
    distributed = _round2(base * num_parts)
    leftover = _round2(amount - distributed)
    # Add any rounding leftover (paise) onto the final installment so the sum matches exactly.
    if leftover != 0:
        parts[-1] = _round2(parts[-1] + leftover)
    return parts


def custom_split(amount: float, custom_parts: List[float]) -> List[float]:
    if not custom_parts:
        raise HTTPException(status_code=400, detail="custom_parts is required for custom split mode")
    if any(p <= 0 for p in custom_parts):
        raise HTTPException(status_code=400, detail="Every installment must be greater than 0")
    total = _round2(sum(custom_parts))
    if total != _round2(amount):
        raise HTTPException(
            status_code=400,
            detail=f"Installments sum to {total}, which does not match the total amount {amount}",
        )
    return [_round2(p) for p in custom_parts]


def compute_split(
    amount: float,
    mode: str,
    max_installment: Optional[float] = None,
    num_parts: Optional[int] = None,
    custom_parts: Optional[List[float]] = None,
    default_max_installment: float = 2000.0,
) -> List[float]:
    mode = (mode or "standard").lower()
    if mode == "standard":
        return standard_split(amount, max_installment or default_max_installment)
    elif mode == "equal":
        if not num_parts:
            # infer a reasonable number of equal parts from the default max installment
            num_parts = max(1, math.ceil(amount / (max_installment or default_max_installment)))
        return equal_split(amount, num_parts)
    elif mode == "custom":
        return custom_split(amount, custom_parts or [])
    else:
        raise HTTPException(status_code=400, detail=f"Unknown split mode: {mode}")


def validate_sum(amount: float, parts: List[float]) -> None:
    if _round2(sum(parts)) != _round2(amount):
        raise HTTPException(
            status_code=500,
            detail="Internal error: installment parts do not sum to the total amount",
        )
