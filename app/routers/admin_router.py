from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_admin, get_current_administrator
from app.schemas.admin import (
    AdminAccountListResponse,
    AdminAccountResponse,
    AdminAppearanceOverviewResponse,
    AdminBannerResponse,
    AdminClassOverviewResponse,
    AdminCrmOverviewResponse,
    AdminDocumentOverviewResponse,
    AdminExamOverviewResponse,
    AdminStudentDetailResponse,
    AdminStudentOverviewResponse,
    AdminTeacherDetailResponse,
    AdminTeacherOverviewResponse,
    CreateAdminBannerRequest,
    CreateAdminAccountRequest,
    ResetAdminUserPasswordRequest,
    UpdateAdminAccountRequest,
    UpdateAdminUserProfileRequest,
)
from app.schemas.common import MessageResponse
from app.services.admin_service import (
    create_admin_banner,
    create_admin_account,
    delete_admin_account,
    delete_admin_student,
    delete_admin_teacher,
    get_admin_appearance_overview,
    get_admin_classes_overview,
    get_admin_crm_overview,
    get_admin_documents_overview,
    get_admin_exams_overview,
    get_admin_student_detail,
    get_admin_students_overview,
    get_admin_teacher_detail,
    get_admin_teachers_overview,
    list_admin_accounts,
    reset_admin_student_password,
    reset_admin_teacher_password,
    update_admin_account,
    update_admin_student_profile,
    update_admin_teacher_profile,
)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/crm/overview", response_model=AdminCrmOverviewResponse)
def get_crm_overview(
    period: str = Query("7d"),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
) -> AdminCrmOverviewResponse:
    _ = current_admin
    return get_admin_crm_overview(db, period)


@router.get("/teachers", response_model=AdminTeacherOverviewResponse)
def get_teachers_overview(
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
) -> AdminTeacherOverviewResponse:
    _ = current_admin
    return get_admin_teachers_overview(db)


@router.get("/teachers/{teacher_id}", response_model=AdminTeacherDetailResponse)
def get_teacher_detail(
    teacher_id: int,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
) -> AdminTeacherDetailResponse:
    _ = current_admin
    return get_admin_teacher_detail(db, teacher_id)


@router.put("/teachers/{teacher_id}", response_model=AdminTeacherDetailResponse)
def put_teacher_profile(
    teacher_id: int,
    payload: UpdateAdminUserProfileRequest,
    db: Session = Depends(get_db),
    current_administrator=Depends(get_current_administrator),
) -> AdminTeacherDetailResponse:
    return update_admin_teacher_profile(
        db,
        current_administrator,
        teacher_id,
        payload.full_name,
        payload.email,
        payload.phone,
        payload.avatar_url,
        payload.date_of_birth,
        payload.gender,
        payload.school_name,
        payload.status,
    )


@router.post("/teachers/{teacher_id}/reset-password", response_model=MessageResponse)
def post_teacher_password_reset(
    teacher_id: int,
    payload: ResetAdminUserPasswordRequest,
    db: Session = Depends(get_db),
    current_administrator=Depends(get_current_administrator),
) -> MessageResponse:
    return reset_admin_teacher_password(db, current_administrator, teacher_id, payload.password)


@router.get("/students", response_model=AdminStudentOverviewResponse)
def get_students_overview(
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
) -> AdminStudentOverviewResponse:
    _ = current_admin
    return get_admin_students_overview(db)


@router.get("/students/{student_id}", response_model=AdminStudentDetailResponse)
def get_student_detail(
    student_id: int,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
) -> AdminStudentDetailResponse:
    _ = current_admin
    return get_admin_student_detail(db, student_id)


@router.put("/students/{student_id}", response_model=AdminStudentDetailResponse)
def put_student_profile(
    student_id: int,
    payload: UpdateAdminUserProfileRequest,
    db: Session = Depends(get_db),
    current_administrator=Depends(get_current_administrator),
) -> AdminStudentDetailResponse:
    return update_admin_student_profile(
        db,
        current_administrator,
        student_id,
        payload.full_name,
        payload.email,
        payload.phone,
        payload.avatar_url,
        payload.date_of_birth,
        payload.gender,
        payload.school_name,
        payload.status,
    )


@router.post("/students/{student_id}/reset-password", response_model=MessageResponse)
def post_student_password_reset(
    student_id: int,
    payload: ResetAdminUserPasswordRequest,
    db: Session = Depends(get_db),
    current_administrator=Depends(get_current_administrator),
) -> MessageResponse:
    return reset_admin_student_password(db, current_administrator, student_id, payload.password)


@router.get("/classes", response_model=AdminClassOverviewResponse)
def get_classes_overview(
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
) -> AdminClassOverviewResponse:
    _ = current_admin
    return get_admin_classes_overview(db)


@router.get("/exams", response_model=AdminExamOverviewResponse)
def get_exams_overview(
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
) -> AdminExamOverviewResponse:
    _ = current_admin
    return get_admin_exams_overview(db)


@router.get("/documents", response_model=AdminDocumentOverviewResponse)
def get_documents_overview(
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
) -> AdminDocumentOverviewResponse:
    _ = current_admin
    return get_admin_documents_overview(db)


@router.get("/appearance", response_model=AdminAppearanceOverviewResponse)
def get_appearance_overview(
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
) -> AdminAppearanceOverviewResponse:
    _ = current_admin
    return get_admin_appearance_overview(db)


@router.post("/appearance/banners", response_model=AdminBannerResponse)
def post_appearance_banner(
    payload: CreateAdminBannerRequest,
    db: Session = Depends(get_db),
    current_administrator=Depends(get_current_administrator),
) -> AdminBannerResponse:
    return create_admin_banner(
        db,
        current_administrator,
        payload.title,
        payload.image_url,
        payload.link_url,
        payload.audience,
        payload.start_at,
        payload.end_at,
        payload.is_active,
    )


@router.get("/users", response_model=AdminAccountListResponse)
def get_admin_accounts(
    db: Session = Depends(get_db),
    current_administrator=Depends(get_current_administrator),
) -> AdminAccountListResponse:
    _ = current_administrator
    return list_admin_accounts(db)


@router.post("/users", response_model=AdminAccountResponse)
def post_admin_account(
    payload: CreateAdminAccountRequest,
    db: Session = Depends(get_db),
    current_administrator=Depends(get_current_administrator),
) -> AdminAccountResponse:
    _ = current_administrator
    return create_admin_account(db, payload.full_name, payload.email, payload.password)


@router.put("/users/{user_id}", response_model=AdminAccountResponse)
def put_admin_account(
    user_id: int,
    payload: UpdateAdminAccountRequest,
    db: Session = Depends(get_db),
    current_administrator=Depends(get_current_administrator),
) -> AdminAccountResponse:
    return update_admin_account(
        db,
        current_administrator,
        user_id,
        payload.full_name,
        payload.password,
        payload.status,
    )


@router.delete("/users/{user_id}", response_model=MessageResponse)
def delete_admin_account_route(
    user_id: int,
    db: Session = Depends(get_db),
    current_administrator=Depends(get_current_administrator),
) -> MessageResponse:
    return delete_admin_account(db, current_administrator, user_id)


@router.delete("/teachers/{teacher_id}", response_model=MessageResponse)
def delete_admin_teacher_route(
    teacher_id: int,
    db: Session = Depends(get_db),
    current_administrator=Depends(get_current_administrator),
) -> MessageResponse:
    return delete_admin_teacher(db, current_administrator, teacher_id)


@router.delete("/students/{student_id}", response_model=MessageResponse)
def delete_admin_student_route(
    student_id: int,
    db: Session = Depends(get_db),
    current_administrator=Depends(get_current_administrator),
) -> MessageResponse:
    return delete_admin_student(db, current_administrator, student_id)
