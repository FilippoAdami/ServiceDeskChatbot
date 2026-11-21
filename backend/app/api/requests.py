from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db.models import SupportRequest
from backend.app.db.session import get_db
from backend.app.schemas.support_request import SupportRequestListResponse, SupportRequestResponse

router = APIRouter(prefix="/requests", tags=["Support Requests"])


@router.get(
    "",
    response_model=SupportRequestListResponse,
    summary="List all SupportRequests with filtering and pagination",
)
def list_support_requests(
    status_filter: Optional[str] = Query(
        default=None,
        alias="status",
        description="Filter by status (open, in_progress, closed)",
    ),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> SupportRequestListResponse:
    """Retrieve support requests for the technician view."""
    base_query = select(SupportRequest)
    count_query = select(func.count(SupportRequest.id))

    if status_filter:
        base_query = base_query.where(SupportRequest.status == status_filter.strip())
        count_query = count_query.where(SupportRequest.status == status_filter.strip())

    total = db.scalar(count_query) or 0

    stmt = (
        base_query.order_by(SupportRequest.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    records = db.scalars(stmt).all()

    items = [SupportRequestResponse.model_validate(r) for r in records]

    return SupportRequestListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{request_id}",
    response_model=SupportRequestResponse,
    summary="Get single SupportRequest by ID",
)
def get_support_request(
    request_id: str,
    db: Session = Depends(get_db),
) -> SupportRequestResponse:
    """Retrieve details for a single SupportRequest."""
    req = db.execute(
        select(SupportRequest).where(SupportRequest.id == request_id)
    ).scalar_one_or_none()

    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Support request '{request_id}' not found",
        )

    return SupportRequestResponse.model_validate(req)
