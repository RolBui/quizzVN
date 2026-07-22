import hmac

import redis
from fastapi import Depends, FastAPI, Header, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ai_agent.artifact_service import create_approved_artifact
from ai_agent.config import settings
from ai_agent.data_lake import data_lake_configuration_status
from ai_agent.database import SessionLocal, bootstrap_storage, get_db
from ai_agent.knowledge import knowledge_configuration_status
from ai_agent.model_registry import (
    approve_model,
    deploy_model,
    register_model_event,
    retire_model,
    routing_configuration_status,
    submit_evaluation,
)
from ai_agent.models import (
    AgentArtifact,
    AgentDatasetSnapshot,
    AgentJob,
    AgentModelEvent,
    AgentModelRun,
    AgentModelVersion,
)
from ai_agent.schemas import (
    AgentJobCreate,
    AgentJobResponse,
    ApprovedDatasetCreate,
    ArtifactResponse,
    DatasetSnapshotCreate,
    DatasetSnapshotResponse,
    ModelApprovalRequest,
    ModelDeploymentRequest,
    ModelEvaluationSubmit,
    ModelEventResponse,
    ModelRetireRequest,
    ModelRunResponse,
    ModelVersionCreate,
    ModelVersionResponse,
)
from ai_agent.tasks import archive_artifact, export_training_dataset, generate_exam


app = FastAPI(title=settings.APP_NAME, version="0.1.0")


@app.on_event("startup")
def startup() -> None:
    bootstrap_storage()


def require_internal_auth(authorization: str = Header(default="")) -> None:
    expected = f"Bearer {settings.SHARED_SECRET}"
    if not settings.SHARED_SECRET or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid internal token")


@app.get("/health")
def health() -> dict:
    database_status = "unavailable"
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        database_status = "ok"
    except Exception:
        pass
    finally:
        db.close()

    redis_status = "unavailable"
    try:
        client = redis.Redis.from_url(settings.REDIS_URL, socket_timeout=2)
        redis_status = "ok" if client.ping() else "unavailable"
    except redis.RedisError:
        pass
    data_lake_status = data_lake_configuration_status()
    rag_status = knowledge_configuration_status()
    model_routing_status = routing_configuration_status()
    required_ok = database_status == "ok" and redis_status == "ok"
    data_lake_ok = data_lake_status in {"disabled", "configured"}
    rag_ok = rag_status in {"disabled", "configured"}
    return {
        "status": "ok" if required_ok and data_lake_ok and rag_ok else "degraded",
        "database": database_status,
        "redis": redis_status,
        "data_lake": data_lake_status,
        "rag": rag_status,
        "model_routing": model_routing_status,
        "ml_dataset": "configured" if settings.ML_DATASET_ROOT else "missing_path",
    }


@app.post("/v1/jobs", response_model=AgentJobResponse, status_code=status.HTTP_202_ACCEPTED)
def create_job(
    payload: AgentJobCreate,
    _: None = Depends(require_internal_auth),
    idempotency_key: str = Header(default="", alias="Idempotency-Key"),
    db: Session = Depends(get_db),
) -> AgentJob:
    if idempotency_key != payload.dispatch_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid idempotency key")

    existing = db.query(AgentJob).filter(AgentJob.dispatch_id == payload.dispatch_id).first()
    if existing:
        if existing.status == "dispatch_failed":
            existing.status = "queued"
            existing.error_message = ""
            db.commit()
            try:
                generate_exam.apply_async(args=[existing.id], priority=int(existing.priority or 0))
            except Exception as exc:
                existing.status = "dispatch_failed"
                existing.error_message = str(exc)
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Queue unavailable",
                ) from exc
        return existing

    job = AgentJob(
        dispatch_id=payload.dispatch_id,
        external_job_id=payload.external_job_id,
        operation=payload.operation,
        prompt=payload.prompt,
        request_data=payload.request_data,
        callback_url=str(payload.callback_url),
        status="queued",
        stage="queued",
        progress_current=0,
        progress_total=int(payload.request_data.get("question_count") or 0),
        progress_message="Job is waiting for an AI worker",
        priority=payload.priority,
        provider=settings.AI_PROVIDER,
        model=settings.AI_MODEL,
    )
    db.add(job)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(AgentJob).filter(AgentJob.dispatch_id == payload.dispatch_id).first()
        if existing:
            return existing
        raise
    db.refresh(job)
    try:
        generate_exam.apply_async(args=[job.id], priority=payload.priority)
    except Exception as exc:
        job.status = "dispatch_failed"
        job.error_message = str(exc)
        db.commit()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Queue unavailable") from exc
    return job


@app.get("/v1/jobs/{job_id}", response_model=AgentJobResponse)
def get_job(
    job_id: str,
    _: None = Depends(require_internal_auth),
    db: Session = Depends(get_db),
) -> AgentJob:
    job = db.get(AgentJob, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent job not found")
    return job


@app.post(
    "/v1/datasets/approved",
    response_model=ArtifactResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_approved_dataset(
    payload: ApprovedDatasetCreate,
    _: None = Depends(require_internal_auth),
    idempotency_key: str = Header(default="", alias="Idempotency-Key"),
    db: Session = Depends(get_db),
) -> AgentArtifact:
    if idempotency_key != payload.idempotency_key:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid idempotency key")
    if data_lake_configuration_status() != "configured":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data lake is not configured",
        )

    artifact, created = create_approved_artifact(
        db,
        external_job_id=payload.external_job_id,
        idempotency_key=payload.idempotency_key,
        request_data=payload.request_data,
        questions=payload.questions,
        metadata=payload.metadata,
    )
    should_queue = created
    if artifact.status == "failed":
        artifact.status = "queued"
        artifact.error_message = ""
        db.commit()
        should_queue = True
    if should_queue:
        try:
            archive_artifact.apply_async(args=[artifact.id], priority=0)
        except Exception as exc:
            artifact.status = "failed"
            artifact.error_message = str(exc)[:2000]
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Archive queue unavailable",
            ) from exc
    return artifact


@app.get("/v1/artifacts/{artifact_id}", response_model=ArtifactResponse)
def get_artifact(
    artifact_id: str,
    _: None = Depends(require_internal_auth),
    db: Session = Depends(get_db),
) -> AgentArtifact:
    artifact = db.get(AgentArtifact, artifact_id)
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    return artifact


@app.post(
    "/v1/ml/datasets",
    response_model=DatasetSnapshotResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_ml_dataset_snapshot(
    payload: DatasetSnapshotCreate,
    _: None = Depends(require_internal_auth),
    idempotency_key: str = Header(default="", alias="Idempotency-Key"),
    db: Session = Depends(get_db),
) -> AgentDatasetSnapshot:
    if len(idempotency_key) < 16 or len(idempotency_key) > 160:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid idempotency key",
        )
    if payload.include_private_opt_in and not settings.ML_PRIVATE_OPT_IN_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Private training data export is disabled",
        )

    existing = (
        db.query(AgentDatasetSnapshot)
        .filter(AgentDatasetSnapshot.idempotency_key == idempotency_key)
        .first()
    )
    if existing:
        if existing.status == "dispatch_failed":
            existing.status = "queued"
            existing.error_message = ""
            db.commit()
            try:
                export_training_dataset.apply_async(args=[existing.id], priority=0)
            except Exception as exc:
                existing.status = "dispatch_failed"
                existing.error_message = str(exc)[:2000]
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="ML dataset queue unavailable",
                ) from exc
        return existing

    snapshot = AgentDatasetSnapshot(
        idempotency_key=idempotency_key,
        name=payload.name.strip(),
        status="queued",
        min_quality_score=(
            payload.min_quality_score
            if payload.min_quality_score is not None
            else settings.ML_MIN_QUALITY_SCORE
        ),
        include_private_opt_in=payload.include_private_opt_in,
    )
    db.add(snapshot)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(AgentDatasetSnapshot)
            .filter(AgentDatasetSnapshot.idempotency_key == idempotency_key)
            .first()
        )
        if existing:
            return existing
        raise
    db.refresh(snapshot)
    try:
        export_training_dataset.apply_async(args=[snapshot.id], priority=0)
    except Exception as exc:
        snapshot.status = "dispatch_failed"
        snapshot.error_message = str(exc)[:2000]
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML dataset queue unavailable",
        ) from exc
    return snapshot


@app.get("/v1/ml/datasets/{snapshot_id}", response_model=DatasetSnapshotResponse)
def get_ml_dataset_snapshot(
    snapshot_id: str,
    _: None = Depends(require_internal_auth),
    db: Session = Depends(get_db),
) -> AgentDatasetSnapshot:
    snapshot = db.get(AgentDatasetSnapshot, snapshot_id)
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ML dataset snapshot not found",
        )
    return snapshot


def _get_model_version(db: Session, model_id: str) -> AgentModelVersion:
    model = db.get(AgentModelVersion, model_id)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model version not found",
        )
    return model


def _model_transition_error(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@app.post(
    "/v1/ml/models",
    response_model=ModelVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_model_version(
    payload: ModelVersionCreate,
    _: None = Depends(require_internal_auth),
    idempotency_key: str = Header(default="", alias="Idempotency-Key"),
    db: Session = Depends(get_db),
) -> AgentModelVersion:
    if len(idempotency_key) < 16 or len(idempotency_key) > 160:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid idempotency key",
        )
    existing = (
        db.query(AgentModelVersion)
        .filter(AgentModelVersion.idempotency_key == idempotency_key)
        .first()
    )
    if existing:
        return existing

    if payload.dataset_snapshot_id:
        snapshot = db.get(AgentDatasetSnapshot, payload.dataset_snapshot_id)
        if not snapshot:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Dataset snapshot not found",
            )
        if snapshot.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Dataset snapshot must be completed before model registration",
            )

    model = AgentModelVersion(
        idempotency_key=idempotency_key,
        name=payload.name.strip(),
        version=payload.version.strip(),
        provider=payload.provider,
        base_model=payload.base_model.strip(),
        serving_model=payload.serving_model.strip(),
        adapter_uri=payload.adapter_uri.strip(),
        adapter_checksum=payload.adapter_checksum.strip(),
        dataset_snapshot_id=payload.dataset_snapshot_id,
        training_report=payload.training_report,
        evaluation_threshold=(
            payload.evaluation_threshold
            if payload.evaluation_threshold is not None
            else settings.MODEL_MIN_EVALUATION_SCORE
        ),
    )
    db.add(model)
    try:
        db.flush()
        register_model_event(
            db,
            model,
            "model_registered",
            "",
            "registered",
            "training-pipeline",
            {"dataset_snapshot_id": payload.dataset_snapshot_id},
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        duplicate = (
            db.query(AgentModelVersion)
            .filter(
                (AgentModelVersion.idempotency_key == idempotency_key)
                | (
                    (AgentModelVersion.name == payload.name.strip())
                    & (AgentModelVersion.version == payload.version.strip())
                )
            )
            .first()
        )
        if duplicate:
            return duplicate
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Model version already exists",
        ) from exc
    db.refresh(model)
    return model


@app.get("/v1/ml/models", response_model=list[ModelVersionResponse])
def list_model_versions(
    model_status: str = "",
    limit: int = 50,
    _: None = Depends(require_internal_auth),
    db: Session = Depends(get_db),
) -> list[AgentModelVersion]:
    query = db.query(AgentModelVersion)
    if model_status.strip():
        query = query.filter(AgentModelVersion.status == model_status.strip())
    return (
        query.order_by(AgentModelVersion.created_at.desc())
        .limit(min(max(limit, 1), 200))
        .all()
    )


@app.get("/v1/ml/models/{model_id}", response_model=ModelVersionResponse)
def get_model_version(
    model_id: str,
    _: None = Depends(require_internal_auth),
    db: Session = Depends(get_db),
) -> AgentModelVersion:
    return _get_model_version(db, model_id)


@app.post("/v1/ml/models/{model_id}/evaluation", response_model=ModelVersionResponse)
def evaluate_model_version(
    model_id: str,
    payload: ModelEvaluationSubmit,
    _: None = Depends(require_internal_auth),
    db: Session = Depends(get_db),
) -> AgentModelVersion:
    try:
        return submit_evaluation(
            db,
            _get_model_version(db, model_id),
            payload.report,
            payload.actor,
        )
    except ValueError as exc:
        raise _model_transition_error(exc) from exc


@app.post("/v1/ml/models/{model_id}/approve", response_model=ModelVersionResponse)
def approve_model_version(
    model_id: str,
    payload: ModelApprovalRequest,
    _: None = Depends(require_internal_auth),
    db: Session = Depends(get_db),
) -> AgentModelVersion:
    try:
        return approve_model(
            db,
            _get_model_version(db, model_id),
            payload.actor,
            payload.reason,
        )
    except ValueError as exc:
        raise _model_transition_error(exc) from exc


@app.post("/v1/ml/models/{model_id}/deploy", response_model=ModelVersionResponse)
def deploy_model_version(
    model_id: str,
    payload: ModelDeploymentRequest,
    _: None = Depends(require_internal_auth),
    db: Session = Depends(get_db),
) -> AgentModelVersion:
    try:
        return deploy_model(
            db,
            _get_model_version(db, model_id),
            payload.mode,
            payload.actor,
            payload.reason,
            payload.routing_weight,
        )
    except ValueError as exc:
        raise _model_transition_error(exc) from exc


@app.post("/v1/ml/models/{model_id}/retire", response_model=ModelVersionResponse)
def retire_model_version(
    model_id: str,
    payload: ModelRetireRequest,
    _: None = Depends(require_internal_auth),
    db: Session = Depends(get_db),
) -> AgentModelVersion:
    return retire_model(
        db,
        _get_model_version(db, model_id),
        payload.actor,
        payload.reason,
    )


@app.get("/v1/ml/models/{model_id}/runs", response_model=list[ModelRunResponse])
def list_model_runs(
    model_id: str,
    limit: int = 50,
    _: None = Depends(require_internal_auth),
    db: Session = Depends(get_db),
) -> list[AgentModelRun]:
    _get_model_version(db, model_id)
    return (
        db.query(AgentModelRun)
        .filter(AgentModelRun.model_version_id == model_id)
        .order_by(AgentModelRun.created_at.desc())
        .limit(min(max(limit, 1), 200))
        .all()
    )


@app.get("/v1/ml/models/{model_id}/events", response_model=list[ModelEventResponse])
def list_model_events(
    model_id: str,
    limit: int = 100,
    _: None = Depends(require_internal_auth),
    db: Session = Depends(get_db),
) -> list[AgentModelEvent]:
    _get_model_version(db, model_id)
    return (
        db.query(AgentModelEvent)
        .filter(AgentModelEvent.model_version_id == model_id)
        .order_by(AgentModelEvent.created_at.desc())
        .limit(min(max(limit, 1), 500))
        .all()
    )
