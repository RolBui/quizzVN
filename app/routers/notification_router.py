from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.notification import NotificationSchema
from app.schemas.common import MessageResponse
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=list[NotificationSchema])
def get_user_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[NotificationSchema]:
    return notification_service.list_notifications(db, current_user.id)


@router.post("/{notif_id}/read", response_model=MessageResponse)
def post_mark_notification_read(
    notif_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    success = notification_service.mark_as_read(db, current_user.id, notif_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    return {"message": "Notification marked as read"}


@router.post("/read-all", response_model=MessageResponse)
def post_mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    notification_service.mark_all_as_read(db, current_user.id)
    return {"message": "All notifications marked as read"}


@router.delete("/{notif_id}", response_model=MessageResponse)
def delete_single_notification(
    notif_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    success = notification_service.delete_notification(db, current_user.id, notif_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    return {"message": "Notification deleted successfully"}


@router.delete("", response_model=MessageResponse)
def delete_all_user_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    notification_service.delete_all_notifications(db, current_user.id)
    return {"message": "All notifications deleted successfully"}
