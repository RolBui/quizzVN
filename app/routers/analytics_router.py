from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.analytics import (
    TrackHeartbeatRequest,
    TrackHeartbeatResponse,
    TrackPageViewRequest,
    TrackPageViewResponse,
)
from app.services.analytics_service import record_heartbeat, record_page_view

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.post("/page-view", response_model=TrackPageViewResponse)
def post_page_view(
    payload: TrackPageViewRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TrackPageViewResponse:
    return record_page_view(db, payload, request)


@router.post("/heartbeat", response_model=TrackHeartbeatResponse)
def post_heartbeat(
    payload: TrackHeartbeatRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TrackHeartbeatResponse:
    return record_heartbeat(db, payload, request)
