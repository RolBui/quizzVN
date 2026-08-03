from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from fastapi import HTTPException, status

DEFAULT_EXAM_TOTAL_POINTS = Decimal("10.00")
MAX_EXAM_TOTAL_POINTS = Decimal("10.00")
POINT_QUANTUM = Decimal("0.01")
POINT_MODE_AUTO = "auto"
POINT_MODE_MANUAL = "manual"


def _to_point_units(value: Any, field_name: str) -> int:
    try:
        decimal_value = Decimal(str(value)).quantize(
            POINT_QUANTUM,
            rounding=ROUND_HALF_UP,
        )
    except (InvalidOperation, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} must be a valid number",
        ) from None

    if decimal_value <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} must be greater than 0",
        )
    return int(decimal_value * 100)


def apply_exam_scoring(
    questions: list[dict],
    *,
    total_points: Any = DEFAULT_EXAM_TOTAL_POINTS,
    point_mode: str = POINT_MODE_AUTO,
) -> Decimal:
    """Normalize question points using integer hundredths as source of truth."""
    target_units = _to_point_units(total_points, "total_points")
    if target_units > int(MAX_EXAM_TOTAL_POINTS * 100):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="total_points cannot exceed 10.00",
        )
    if not questions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="questions must not be empty",
        )

    normalized_mode = (point_mode or POINT_MODE_AUTO).strip().lower()
    if normalized_mode == POINT_MODE_AUTO:
        if len(questions) > target_units:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Too many questions to assign at least 0.01 point to each question",
            )
        base_units, remainder = divmod(target_units, len(questions))
        ordered_indexes = sorted(
            range(len(questions)),
            key=lambda index: (questions[index].get("order_index", index), index),
        )
        for position, question_index in enumerate(ordered_indexes):
            units = base_units + (1 if position < remainder else 0)
            questions[question_index]["points"] = Decimal(units) / 100
        return Decimal(target_units) / 100

    if normalized_mode != POINT_MODE_MANUAL:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="point_mode must be auto or manual",
        )

    actual_units = 0
    for index, question in enumerate(questions, start=1):
        units = _to_point_units(question.get("points"), f"Question {index} points")
        question["points"] = Decimal(units) / 100
        actual_units += units
    if actual_units > target_units:
        actual_total = Decimal(actual_units) / 100
        target_total = Decimal(target_units) / 100
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Question points total {actual_total:.2f} exceeds "
                f"total_points {target_total:.2f}"
            ),
        )
    return Decimal(actual_units) / 100
