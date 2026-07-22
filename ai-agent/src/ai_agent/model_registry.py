import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from ai_agent.config import settings
from ai_agent.models import AgentModelEvent, AgentModelRun, AgentModelVersion


DEPLOYED_STATUSES = {"shadow", "canary", "active"}


@dataclass(frozen=True)
class ModelRoute:
    provider: str
    model: str
    mode: str = "default"
    model_version_id: str | None = None
    shadow_model_version_id: str | None = None


def routing_configuration_status() -> str:
    if not settings.MODEL_ROUTING_ENABLED:
        return "disabled"
    if not settings.LOCAL_INFERENCE_URL:
        return "missing_endpoint"
    return "configured"


def register_model_event(
    db: Session,
    model: AgentModelVersion,
    event_type: str,
    from_status: str,
    to_status: str,
    actor: str,
    details: dict[str, Any] | None = None,
) -> None:
    db.add(
        AgentModelEvent(
            model_version_id=model.id,
            event_type=event_type,
            from_status=from_status,
            to_status=to_status,
            actor=actor.strip() or "system",
            details=details or {},
        )
    )


def submit_evaluation(
    db: Session,
    model: AgentModelVersion,
    report: dict[str, Any],
    actor: str,
) -> AgentModelVersion:
    if model.status in DEPLOYED_STATUSES or model.status == "retired":
        raise ValueError("Model must not be deployed or retired while evaluation is updated")

    score = _evaluation_score(report)
    activation_allowed = report.get("activation_allowed") is not False
    report_status = str(report.get("status") or "").strip().lower()
    passed = (
        score >= float(model.evaluation_threshold)
        and activation_allowed
        and report_status not in {"failed", "error"}
    )
    previous = model.status
    model.evaluation_report = report
    model.evaluation_score = score
    model.evaluated_at = datetime.now(timezone.utc)
    model.status = "evaluation_passed" if passed else "evaluation_failed"
    model.routing_weight = 0
    register_model_event(
        db,
        model,
        "evaluation_submitted",
        previous,
        model.status,
        actor,
        {
            "score": score,
            "threshold": float(model.evaluation_threshold),
            "activation_allowed": activation_allowed,
        },
    )
    db.commit()
    db.refresh(model)
    return model


def approve_model(
    db: Session,
    model: AgentModelVersion,
    actor: str,
    reason: str,
) -> AgentModelVersion:
    if model.status != "evaluation_passed":
        raise ValueError("Only a model that passed evaluation can be approved")
    if model.evaluation_score is None or model.evaluation_score < model.evaluation_threshold:
        raise ValueError("Model evaluation score is below the activation threshold")

    previous = model.status
    model.status = "approved"
    model.approved_by = actor.strip()
    model.approval_reason = reason.strip()
    model.approved_at = datetime.now(timezone.utc)
    register_model_event(
        db,
        model,
        "model_approved",
        previous,
        model.status,
        actor,
        {"reason": reason.strip()},
    )
    db.commit()
    db.refresh(model)
    return model


def deploy_model(
    db: Session,
    model: AgentModelVersion,
    mode: str,
    actor: str,
    reason: str,
    routing_weight: int | None = None,
) -> AgentModelVersion:
    if model.status not in {"approved", "shadow", "canary", "active"}:
        raise ValueError("Model must be approved before deployment")
    if not settings.LOCAL_INFERENCE_URL:
        raise ValueError("AI_AGENT_LOCAL_INFERENCE_URL is required before deployment")
    if mode not in DEPLOYED_STATUSES:
        raise ValueError("Deployment mode must be shadow, canary, or active")

    weight = 0
    if mode == "canary":
        weight = routing_weight if routing_weight is not None else 10
        if not 1 <= weight <= 99:
            raise ValueError("Canary routing weight must be between 1 and 99")
    elif mode == "active":
        weight = 100

    _deactivate_other_models(db, model.id, mode, actor)
    previous = model.status
    model.status = mode
    model.routing_weight = weight
    model.activated_at = datetime.now(timezone.utc)
    model.retired_at = None
    register_model_event(
        db,
        model,
        "model_deployed",
        previous,
        mode,
        actor,
        {"reason": reason.strip(), "routing_weight": weight},
    )
    db.commit()
    db.refresh(model)
    return model


def retire_model(
    db: Session,
    model: AgentModelVersion,
    actor: str,
    reason: str,
) -> AgentModelVersion:
    if model.status == "retired":
        return model
    previous = model.status
    model.status = "retired"
    model.routing_weight = 0
    model.retired_at = datetime.now(timezone.utc)
    register_model_event(
        db,
        model,
        "model_retired",
        previous,
        model.status,
        actor,
        {"reason": reason.strip()},
    )
    db.commit()
    db.refresh(model)
    return model


def select_model_route(db: Session, dispatch_id: str) -> ModelRoute:
    default = ModelRoute(provider=settings.AI_PROVIDER, model=settings.AI_MODEL)
    if routing_configuration_status() != "configured":
        return default

    shadow = (
        db.query(AgentModelVersion)
        .filter(AgentModelVersion.status == "shadow")
        .order_by(AgentModelVersion.activated_at.desc(), AgentModelVersion.created_at.desc())
        .first()
    )
    shadow_id = shadow.id if shadow else None
    model = (
        db.query(AgentModelVersion)
        .filter(AgentModelVersion.status.in_(["active", "canary"]))
        .order_by(AgentModelVersion.activated_at.desc(), AgentModelVersion.created_at.desc())
        .first()
    )
    if not model or (
        model.status == "canary"
        and _routing_bucket(dispatch_id) >= model.routing_weight
    ):
        return ModelRoute(
            provider=default.provider,
            model=default.model,
            shadow_model_version_id=shadow_id,
        )
    return ModelRoute(
        provider=model.provider,
        model=model.serving_model,
        mode=model.status,
        model_version_id=model.id,
        shadow_model_version_id=shadow_id,
    )


def create_model_run(
    db: Session,
    model: AgentModelVersion,
    job_id: str,
    mode: str,
) -> AgentModelRun:
    run = AgentModelRun(
        model_version_id=model.id,
        job_id=job_id,
        mode=mode,
        status="running",
        provider=model.provider,
        model=model.serving_model,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _deactivate_other_models(
    db: Session,
    model_id: str,
    deployment_mode: str,
    actor: str,
) -> None:
    replaced_statuses = ["shadow"] if deployment_mode == "shadow" else ["canary", "active"]
    others = (
        db.query(AgentModelVersion)
        .filter(
            AgentModelVersion.id != model_id,
            AgentModelVersion.status.in_(replaced_statuses),
        )
        .all()
    )
    for other in others:
        previous = other.status
        other.status = "approved"
        other.routing_weight = 0
        register_model_event(
            db,
            other,
            "deployment_replaced",
            previous,
            other.status,
            actor,
            {"replacement_model_id": model_id},
        )


def _evaluation_score(report: dict[str, Any]) -> float:
    value = report.get("structural_accuracy")
    if value is None and isinstance(report.get("metrics"), dict):
        value = report["metrics"].get("structural_accuracy")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Evaluation report must contain numeric structural_accuracy")
    score = float(value)
    if not 0.0 <= score <= 1.0:
        raise ValueError("Evaluation structural_accuracy must be between 0 and 1")
    return score


def _routing_bucket(dispatch_id: str) -> int:
    digest = hashlib.sha256(dispatch_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % 100
