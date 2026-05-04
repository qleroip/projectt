from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum
from functools import wraps
from io import StringIO
from typing import Any, Iterable
import csv
import json
import os
import time

import jwt
from flask import (
    Flask,
    abort,
    flash,
    g,
    jsonify,
    Response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, text
from sqlalchemy.orm import joinedload
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)
app.config["SECRET_KEY"] = "riskguard-dev-secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///riskguard_v3.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

DESKTOP_ALLOWED_ORIGINS = {
    "http://localhost:1420",
    "http://127.0.0.1:1420",
    "http://tauri.localhost",
    "tauri://localhost",
}


@app.after_request
def allow_desktop_client(response):
    origin = request.headers.get("Origin", "")
    if origin in DESKTOP_ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, OPTIONS"
        response.headers["Vary"] = "Origin"
    try:
        started_at = getattr(g, "request_started_at", None)
        if started_at and request.path.startswith("/api/"):
            elapsed = int((time.perf_counter() - started_at) * 1000)
            kind = "COMMAND" if request.method in {"POST", "PATCH", "PUT", "DELETE"} else "QUERY"
            record_metric(request.path, kind, elapsed)
            db.session.commit()
    except Exception:  # noqa: BLE001
        db.session.rollback()
    return response


class Role(StrEnum):
    ADMIN = "admin"
    WORKER = "worker"
    RISK_MANAGER = "risk_manager"
    EXPERT = "expert"


class RiskStatus(StrEnum):
    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class TaskStatus(StrEnum):
    RUNNING = "RUNNING"
    QUEUED = "QUEUED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class IntakeStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSED = "PROCESSED"


class DomainEventStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


ALLOWED_TRANSITIONS: dict[RiskStatus, set[RiskStatus]] = {
    RiskStatus.CREATED: {RiskStatus.ACTIVE},
    RiskStatus.ACTIVE: {RiskStatus.COMPLETED, RiskStatus.CANCELLED},
    RiskStatus.COMPLETED: set(),
    RiskStatus.CANCELLED: set(),
}

ROLE_LABELS = {
    Role.ADMIN.value: "Администратор",
    Role.WORKER.value: "Работник",
    Role.RISK_MANAGER.value: "Риск-менеджер",
    Role.EXPERT.value: "Эксперт",
}

STATUS_LABELS = {
    RiskStatus.CREATED.value: "Создан",
    RiskStatus.ACTIVE.value: "В работе",
    RiskStatus.COMPLETED.value: "Завершен",
    RiskStatus.CANCELLED.value: "Отменен",
}

TASK_STATUS_LABELS = {
    TaskStatus.RUNNING.value: "Выполняется",
    TaskStatus.QUEUED.value: "В очереди",
    TaskStatus.COMPLETED.value: "Завершено",
    TaskStatus.FAILED.value: "С ошибкой",
}

CATEGORY_LABELS = {
    "Operational": "Операционный",
    "Security": "Информационная безопасность",
    "Compliance": "Соответствие требованиям",
    "Technology": "Технологический",
    "Infrastructure": "Инфраструктура",
}

PRIORITY_LABELS = {
    "HIGH": "Высокий",
    "MEDIUM": "Средний",
    "LOW": "Низкий",
    "High": "Высокий",
    "Medium": "Средний",
    "Low": "Низкий",
}

SEVERITY_LABELS = {
    "Critical": "Критический",
    "High": "Высокий",
    "Medium": "Средний",
    "Low": "Низкий",
}


def status_label_text(status: str) -> str:
    return STATUS_LABELS.get(status, status)


def severity_label_text(severity: str) -> str:
    return SEVERITY_LABELS.get(severity, severity)


def category_label_text(category: str) -> str:
    return CATEGORY_LABELS.get(category, category)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(40), nullable=False, default=Role.RISK_MANAGER.value)
    is_approved = db.Column(db.Boolean, nullable=False, default=False)
    joined_at = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    risks = db.relationship("Risk", back_populates="owner", foreign_keys="Risk.owner_id", lazy="selectin")
    assigned_risks = db.relationship("Risk", back_populates="expert", foreign_keys="Risk.expert_id", lazy="selectin")
    assessments = db.relationship("Assessment", back_populates="expert", lazy="selectin")
    incidents = db.relationship("Incident", back_populates="reporter", lazy="selectin")
    incident_intakes = db.relationship("IncidentIntake", back_populates="reporter", lazy="selectin")


class Risk(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(32), unique=True, nullable=False)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(80), nullable=False)
    impact_level = db.Column(db.String(40), nullable=False)
    status = db.Column(db.String(40), nullable=False, default=RiskStatus.CREATED.value)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    expert_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_at = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    owner = db.relationship("User", back_populates="risks", foreign_keys=[owner_id])
    expert = db.relationship("User", back_populates="assigned_risks", foreign_keys=[expert_id])
    measures = db.relationship(
        "MitigationMeasure",
        back_populates="risk",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    assessments = db.relationship("Assessment", back_populates="risk", cascade="all, delete-orphan", lazy="selectin")
    incidents = db.relationship("Incident", back_populates="risk", cascade="all, delete-orphan", lazy="selectin")


class MitigationMeasure(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    risk_id = db.Column(db.Integer, db.ForeignKey("risk.id"), nullable=False)
    action = db.Column(db.String(220), nullable=False)
    responsible_person = db.Column(db.String(120), nullable=False)
    deadline = db.Column(db.String(20), nullable=False)
    priority = db.Column(db.String(16), nullable=False)
    status = db.Column(db.String(32), nullable=False, default="planned")
    risk = db.relationship("Risk", back_populates="measures")


class Assessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    risk_id = db.Column(db.Integer, db.ForeignKey("risk.id"), nullable=False)
    probability = db.Column(db.Integer, nullable=False)
    impact_score = db.Column(db.Integer, nullable=False)
    recommendation = db.Column(db.Text, nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    expert_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    risk = db.relationship("Risk", back_populates="assessments")
    expert = db.relationship("User", back_populates="assessments")

    @property
    def severity_level(self) -> str:
        score = self.probability * self.impact_score
        if score >= 20:
            return "Critical"
        if score >= 12:
            return "High"
        if score >= 6:
            return "Medium"
        return "Low"


class Incident(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(32), unique=True, nullable=False)
    risk_id = db.Column(db.Integer, db.ForeignKey("risk.id"), nullable=False)
    occurrence_date = db.Column(db.String(25), nullable=False)
    actual_loss = db.Column(db.Integer, nullable=False, default=0)
    description = db.Column(db.Text, nullable=False)
    reporter_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    risk = db.relationship("Risk", back_populates="incidents")
    reporter = db.relationship("User", back_populates="incidents")


class IncidentIntake(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(32), unique=True, nullable=False)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(80), nullable=False)
    impact_level = db.Column(db.String(40), nullable=False)
    occurrence_date = db.Column(db.String(25), nullable=False)
    actual_loss = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default=IntakeStatus.PENDING.value)
    reporter_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    linked_risk_id = db.Column(db.Integer, db.ForeignKey("risk.id"))
    created_at = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    reporter = db.relationship("User", back_populates="incident_intakes")
    linked_risk = db.relationship("Risk")


class BackgroundTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    priority = db.Column(db.String(16), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    progress = db.Column(db.Integer, nullable=False, default=0)
    started_at = db.Column(db.String(25), nullable=False)
    eta = db.Column(db.String(25))


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.String(25), nullable=False)
    user_name = db.Column(db.String(120), nullable=False)
    action = db.Column(db.String(60), nullable=False)
    resource = db.Column(db.String(60), nullable=False)
    status = db.Column(db.String(20), nullable=False)


class RiskReadModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    risk_public_id = db.Column(db.String(32), unique=True, nullable=False, index=True)
    risk_title = db.Column(db.String(180), nullable=False)
    risk_status = db.Column(db.String(40), nullable=False)
    impact_level = db.Column(db.String(40), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    owner_name = db.Column(db.String(120), nullable=False)
    expert_name = db.Column(db.String(120), nullable=False, default="")
    measure_count = db.Column(db.Integer, nullable=False, default=0)
    assessment_count = db.Column(db.Integer, nullable=False, default=0)
    incident_count = db.Column(db.Integer, nullable=False, default=0)
    last_assessment_level = db.Column(db.String(40), nullable=False, default="")
    updated_at = db.Column(db.String(25), nullable=False, default=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))


class DomainEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(80), nullable=False)
    aggregate_id = db.Column(db.String(64), nullable=False)
    payload_json = db.Column(db.Text, nullable=False, default="{}")
    status = db.Column(db.String(20), nullable=False, default=DomainEventStatus.PENDING.value)
    created_at = db.Column(db.String(25), nullable=False, default=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
    processed_at = db.Column(db.String(25), nullable=False, default="")
    error_message = db.Column(db.String(255), nullable=False, default="")


class ApiRequestMetric(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    endpoint = db.Column(db.String(120), nullable=False, index=True)
    request_kind = db.Column(db.String(16), nullable=False)
    duration_ms = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.String(25), nullable=False, default=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))


QUERY_CACHE: dict[str, dict[str, Any]] = {}
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100


def api_error(message: str, status_code: int, code: str | None = None, details: Any | None = None):
    payload: dict[str, Any] = {
        "error": message,  # Backward compatibility for existing APK/desktop clients.
        "code": code or f"HTTP_{status_code}",
        "message": message,
    }
    if details is not None:
        payload["details"] = details
    return jsonify(payload), status_code


def paginate_collection(items: Iterable[Any]) -> tuple[list[Any], dict[str, Any] | None]:
    items_list = list(items)
    pagination_requested = any(name in request.args for name in ("page", "limit", "offset"))
    if not pagination_requested:
        return items_list, None

    page = request.args.get("page", type=int) or 1
    limit = request.args.get("limit", type=int) or DEFAULT_PAGE_SIZE
    offset = request.args.get("offset", type=int)
    page = max(page, 1)
    limit = max(1, min(limit, MAX_PAGE_SIZE))
    if offset is None:
        offset = (page - 1) * limit
    offset = max(offset, 0)

    total = len(items_list)
    sliced = items_list[offset : offset + limit]
    return sliced, {
        "total": total,
        "limit": limit,
        "offset": offset,
        "page": (offset // limit) + 1,
        "has_next": offset + limit < total,
    }


def collection_response(items: Iterable[Any], serializer):
    page_items, pagination = paginate_collection(items)
    data = [serializer(item) for item in page_items]
    if pagination is None:
        return jsonify(data)
    return jsonify({"items": data, "pagination": pagination})


def create_access_token(user: User) -> str:
    payload = {
        "user_id": user.id,
        "role": user.role,
        "exp": datetime.utcnow() + timedelta(hours=8),
    }
    return jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])


def current_user_from_session() -> User | None:
    token = session.get("access_token")
    if not token:
        return None
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        session.pop("access_token", None)
        return None
    user = db.session.get(User, payload["user_id"])
    if not user or not user.is_approved:
        session.pop("access_token", None)
        return None
    return user


def api_auth_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.removeprefix("Bearer ").strip() if auth_header.startswith("Bearer ") else ""
        if not token:
            return api_error("Missing token", 401, "AUTH_TOKEN_MISSING")
        try:
            payload = decode_token(token)
        except jwt.PyJWTError:
            return api_error("Invalid token", 401, "AUTH_TOKEN_INVALID")
        g.api_user = db.session.get(User, payload["user_id"])
        if not g.api_user or not g.api_user.is_approved:
            return api_error("User not found", 401, "AUTH_USER_NOT_FOUND")
        return view(*args, **kwargs)

    return wrapped


def api_roles_required(*roles: str):
    def decorator(view):
        @wraps(view)
        @api_auth_required
        def wrapped(*args, **kwargs):
            if g.api_user.role not in roles:
                return api_error("Forbidden", 403, "ACCESS_FORBIDDEN")
            return view(*args, **kwargs)

        return wrapped

    return decorator


def web_auth_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user_from_session()
        if not user:
            return redirect(url_for("auth_page"))
        g.current_user = user
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    @web_auth_required
    def wrapped(*args, **kwargs):
        if g.current_user.role != Role.ADMIN.value:
            abort(404)
        return view(*args, **kwargs)

    return wrapped


def manager_web_required(view):
    @wraps(view)
    @web_auth_required
    def wrapped(*args, **kwargs):
        if g.current_user.role not in {Role.ADMIN.value, Role.RISK_MANAGER.value}:
            abort(404)
        return view(*args, **kwargs)

    return wrapped


def add_audit_log(user_name: str, action: str, resource: str, status: str) -> None:
    db.session.add(
        AuditLog(
            timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            user_name=user_name,
            action=action,
            resource=resource,
            status=status,
        )
    )


def record_metric(endpoint: str, request_kind: str, duration_ms: int) -> None:
    db.session.add(
        ApiRequestMetric(
            endpoint=endpoint,
            request_kind=request_kind,
            duration_ms=max(0, int(duration_ms)),
        )
    )


def invalidate_query_cache() -> None:
    QUERY_CACHE.clear()


def read_cache_get(key: str, ttl_seconds: int = 15) -> Any | None:
    item = QUERY_CACHE.get(key)
    if not item:
        return None
    if (time.time() - item["ts"]) > ttl_seconds:
        QUERY_CACHE.pop(key, None)
        return None
    return item["value"]


def read_cache_set(key: str, value: Any) -> None:
    QUERY_CACHE[key] = {"value": value, "ts": time.time()}


def queue_domain_event(event_type: str, aggregate_id: str, payload: dict[str, Any] | None = None) -> DomainEvent:
    event = DomainEvent(
        event_type=event_type,
        aggregate_id=aggregate_id,
        payload_json=json.dumps(payload or {}, ensure_ascii=False),
        status=DomainEventStatus.PENDING.value,
    )
    db.session.add(event)
    return event


def rebuild_risk_read_model_for_public_id(public_id: str) -> bool:
    row = db.session.execute(
        text(
            """
            SELECT
                r.public_id AS risk_public_id,
                r.title AS risk_title,
                r.status AS risk_status,
                r.impact_level AS impact_level,
                r.category AS category,
                owner.full_name AS owner_name,
                COALESCE(expert.full_name, '') AS expert_name,
                COUNT(DISTINCT m.id) AS measure_count,
                COUNT(DISTINCT a.id) AS assessment_count,
                COUNT(DISTINCT i.id) AS incident_count,
                COALESCE(
                    (
                        SELECT
                            CASE
                                WHEN (a2.probability * a2.impact_score) >= 20 THEN 'Critical'
                                WHEN (a2.probability * a2.impact_score) >= 12 THEN 'High'
                                WHEN (a2.probability * a2.impact_score) >= 6 THEN 'Medium'
                                ELSE 'Low'
                            END
                        FROM assessment a2
                        WHERE a2.risk_id = r.id
                        ORDER BY a2.id DESC
                        LIMIT 1
                    ),
                    ''
                ) AS last_assessment_level
            FROM risk r
            JOIN user owner ON owner.id = r.owner_id
            LEFT JOIN user expert ON expert.id = r.expert_id
            LEFT JOIN mitigation_measure m ON m.risk_id = r.id
            LEFT JOIN assessment a ON a.risk_id = r.id
            LEFT JOIN incident i ON i.risk_id = r.id
            WHERE r.public_id = :public_id
            GROUP BY r.id, owner.full_name, expert.full_name
            """
        ),
        {"public_id": public_id},
    ).mappings().first()

    existing = db.session.execute(
        db.select(RiskReadModel).where(RiskReadModel.risk_public_id == public_id)
    ).scalar_one_or_none()

    if not row:
        if existing:
            db.session.delete(existing)
            return True
        return False

    if not existing:
        existing = RiskReadModel(risk_public_id=public_id, risk_title=row["risk_title"], risk_status=row["risk_status"], impact_level=row["impact_level"], category=row["category"], owner_name=row["owner_name"])
        db.session.add(existing)

    existing.risk_title = row["risk_title"]
    existing.risk_status = row["risk_status"]
    existing.impact_level = row["impact_level"]
    existing.category = row["category"]
    existing.owner_name = row["owner_name"]
    existing.expert_name = row["expert_name"] or ""
    existing.measure_count = int(row["measure_count"] or 0)
    existing.assessment_count = int(row["assessment_count"] or 0)
    existing.incident_count = int(row["incident_count"] or 0)
    existing.last_assessment_level = row["last_assessment_level"] or ""
    existing.updated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    return True


def process_domain_events(limit: int = 10) -> dict[str, int]:
    pending_events = db.session.execute(
        db.select(DomainEvent)
        .where(DomainEvent.status == DomainEventStatus.PENDING.value)
        .order_by(DomainEvent.id)
        .limit(limit)
    ).scalars().all()

    processed = 0
    failed = 0
    for event in pending_events:
        try:
            payload = json.loads(event.payload_json or "{}")
            public_id = payload.get("risk_public_id") or event.aggregate_id
            rebuild_risk_read_model_for_public_id(public_id)
            event.status = DomainEventStatus.PROCESSED.value
            event.error_message = ""
            event.processed_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            processed += 1
        except Exception as exc:  # noqa: BLE001
            event.status = DomainEventStatus.FAILED.value
            event.error_message = str(exc)[:240]
            event.processed_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            failed += 1

    if pending_events:
        add_audit_log("system", "PROCESS_DOMAIN_EVENTS", "EVENT_QUEUE", "success" if failed == 0 else "failure")
    return {"processed": processed, "failed": failed, "remaining": db.session.scalar(db.select(func.count(DomainEvent.id)).where(DomainEvent.status == DomainEventStatus.PENDING.value)) or 0}


def seed_read_model_from_write_model() -> None:
    risk_ids = db.session.execute(db.select(Risk.public_id)).scalars().all()
    for public_id in risk_ids:
        rebuild_risk_read_model_for_public_id(public_id)


def enqueue_background_task(title: str, description: str, priority: str = "MEDIUM") -> BackgroundTask:
    existing = db.session.execute(
        db.select(BackgroundTask).where(
            BackgroundTask.title == title,
            BackgroundTask.status.in_([TaskStatus.RUNNING.value, TaskStatus.QUEUED.value]),
        )
    ).scalar_one_or_none()
    if existing:
        existing.description = description
        existing.priority = priority
        return existing

    running_exists = db.session.execute(
        db.select(BackgroundTask).where(BackgroundTask.status == TaskStatus.RUNNING.value)
    ).first()
    task = BackgroundTask(
        title=title,
        description=description,
        priority=priority,
        status=TaskStatus.QUEUED.value if running_exists else TaskStatus.RUNNING.value,
        progress=0 if running_exists else 10,
        started_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        eta="",
    )
    db.session.add(task)
    return task


def process_background_queue(actor: User) -> dict[str, str]:
    completed_title = ""
    started_title = ""
    progressed_title = ""
    progress_value = 0

    running_task = db.session.execute(
        db.select(BackgroundTask).where(BackgroundTask.status == TaskStatus.RUNNING.value).order_by(BackgroundTask.id)
    ).scalars().first()
    if running_task:
        # Simulate a real queue worker step: each click advances current task.
        next_progress = min(100, running_task.progress + 20)
        running_task.progress = next_progress
        progressed_title = running_task.title
        progress_value = next_progress
        if next_progress >= 100:
            running_task.status = TaskStatus.COMPLETED.value
            completed_title = running_task.title

            next_task = db.session.execute(
                db.select(BackgroundTask).where(BackgroundTask.status == TaskStatus.QUEUED.value).order_by(BackgroundTask.id)
            ).scalars().first()
            if next_task:
                next_task.status = TaskStatus.RUNNING.value
                next_task.progress = max(next_task.progress, 10)
                next_task.started_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                started_title = next_task.title
    else:
        next_task = db.session.execute(
            db.select(BackgroundTask).where(BackgroundTask.status == TaskStatus.QUEUED.value).order_by(BackgroundTask.id)
        ).scalars().first()
        if next_task:
            next_task.status = TaskStatus.RUNNING.value
            next_task.progress = max(next_task.progress, 10)
            next_task.started_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            started_title = next_task.title

    event_summary = process_domain_events(limit=3)
    add_audit_log(actor.full_name, "PROCESS_BACKGROUND_QUEUE", "TASKS", "success")
    invalidate_query_cache()
    return {
        "completed": completed_title,
        "started": started_title,
        "progressed": progressed_title,
        "progress": str(progress_value),
        "events_processed": str(event_summary["processed"]),
        "events_remaining": str(event_summary["remaining"]),
    }


def can_manage_risk(user: User, risk: Risk) -> bool:
    return user.role in {Role.ADMIN.value, Role.RISK_MANAGER.value} or risk.owner_id == user.id


def can_assess_risk(user: User, risk: Risk) -> bool:
    return user.role in {Role.ADMIN.value, Role.RISK_MANAGER.value} or risk.expert_id == user.id


def _priority_score_by_level(level: str) -> int:
    mapping = {
        "Critical": 5,
        "High": 4,
        "Medium": 3,
        "Low": 2,
    }
    return mapping.get(level, 3)


def _serialize_assessment(assessment: Assessment) -> dict:
    return {
        "id": assessment.id,
        "risk_id": assessment.risk_id,
        "probability": assessment.probability,
        "impact_score": assessment.impact_score,
        "recommendation": assessment.recommendation,
        "severity_level": assessment.severity_level,
        "date": assessment.date.isoformat(),
        "expert_id": assessment.expert_id,
    }


def _serialize_expert_risk(risk: Risk, user: User, include_details: bool = False) -> dict:
    if user.role == Role.EXPERT.value:
        user_assessments = [item for item in risk.assessments if item.expert_id == user.id]
    else:
        user_assessments = list(risk.assessments)
    latest_assessment = max(user_assessments, key=lambda item: item.id) if user_assessments else None

    payload = {
        "id": risk.public_id,
        "title": risk.title,
        "description": risk.description,
        "category": risk.category,
        "status": risk.status,
        "impact_level": risk.impact_level,
        "owner": risk.owner.full_name if risk.owner else "",
        "expert": risk.expert.full_name if risk.expert else None,
        "priority": _priority_score_by_level(risk.impact_level),
        "assigned_date": risk.created_at.isoformat() if risk.created_at else "",
        "incident_count": len(risk.incidents),
        "measure_count": len(risk.measures),
        "assessment_count": len(risk.assessments),
        "my_assessment": _serialize_assessment(latest_assessment) if latest_assessment else None,
    }

    if include_details:
        payload["incidents"] = [incident.description for incident in risk.incidents]
        payload["mitigations"] = [measure.action for measure in risk.measures]
    return payload


def read_model_risks_query(status: str = "", search: str = "") -> list[dict[str, Any]]:
    cache_key = f"read_risks::{status}::{search}".lower()
    cached = read_cache_get(cache_key)
    if cached is not None:
        return cached

    sql = """
        SELECT
            risk_public_id,
            risk_title,
            risk_status,
            impact_level,
            category,
            owner_name,
            expert_name,
            measure_count,
            assessment_count,
            incident_count,
            last_assessment_level,
            updated_at
        FROM risk_read_model
        WHERE 1=1
    """
    params: dict[str, Any] = {}
    if status:
        sql += " AND risk_status = :status"
        params["status"] = status
    if search:
        sql += " AND (LOWER(risk_public_id) LIKE :search OR LOWER(risk_title) LIKE :search)"
        params["search"] = f"%{search.lower()}%"
    sql += " ORDER BY risk_public_id"

    rows = db.session.execute(text(sql), params).mappings().all()
    data = [dict(row) for row in rows]
    read_cache_set(cache_key, data)
    return data


def read_model_risk_by_public_id(public_id: str) -> dict[str, Any] | None:
    cache_key = f"read_risk::{public_id}".lower()
    cached = read_cache_get(cache_key)
    if cached is not None:
        return cached

    row = db.session.execute(
        text(
            """
            SELECT
                risk_public_id,
                risk_title,
                risk_status,
                impact_level,
                category,
                owner_name,
                expert_name,
                measure_count,
                assessment_count,
                incident_count,
                last_assessment_level,
                updated_at
            FROM risk_read_model
            WHERE risk_public_id = :public_id
            """
        ),
        {"public_id": public_id},
    ).mappings().first()
    data = dict(row) if row else None
    if data is not None:
        read_cache_set(cache_key, data)
    return data


def dto_web_risk_list_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["risk_public_id"],
        "title": item["risk_title"],
        "status": item["risk_status"],
        "impact_level": item["impact_level"],
        "owner": item["owner_name"],
        "expert": item["expert_name"],
        "measure_count": int(item["measure_count"]),
        "assessment_count": int(item["assessment_count"]),
        "incident_count": int(item["incident_count"]),
        "updated_at": item["updated_at"],
    }


def dto_mobile_incident_queue_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "risk_id": item["risk_public_id"],
        "title": item["risk_title"],
        "status": item["risk_status"],
        "impact_level": item["impact_level"],
        "owner": item["owner_name"],
    }


def available_actions(user: User) -> list[str]:
    role_map = {
        Role.ADMIN.value: ["Создание риска", "Редактирование любых рисков", "Удаление записей", "Управление ролями"],
        Role.RISK_MANAGER.value: ["Назначение экспертов", "Утверждение планов", "Изменение статусов", "Просмотр отчетов"],
        Role.EXPERT.value: ["Оценка назначенных рисков", "Подготовка рекомендаций", "Формирование аналитики"],
        Role.WORKER.value: ["Регистрация инцидента", "Просмотр своих инцидентов", "Отслеживание статуса"],
    }
    return role_map.get(user.role, ["Просмотр рисков"])


def role_home_endpoint(user: User) -> str:
    return "risk_journal"


def next_public_risk_id() -> str:
    risks = db.session.execute(db.select(Risk.public_id)).scalars().all()
    numeric_ids = []
    for public_id in risks:
        try:
            numeric_ids.append(int(public_id.split("-")[-1]))
        except (ValueError, AttributeError):
            continue
    next_id = (max(numeric_ids) if numeric_ids else 0) + 1
    return f"RISK-{next_id:03d}"


def next_public_incident_id() -> str:
    incidents = db.session.execute(db.select(Incident.public_id)).scalars().all()
    numeric_ids = []
    for public_id in incidents:
        try:
            numeric_ids.append(int(public_id.split("-")[-1]))
        except (ValueError, AttributeError):
            continue
    next_id = (max(numeric_ids) if numeric_ids else 0) + 1
    return f"INC-{next_id:03d}"


def next_public_intake_id() -> str:
    intakes = db.session.execute(db.select(IncidentIntake.public_id)).scalars().all()
    numeric_ids = []
    for public_id in intakes:
        try:
            numeric_ids.append(int(public_id.split("-")[-1]))
        except (ValueError, AttributeError):
            continue
    next_id = (max(numeric_ids) if numeric_ids else 0) + 1
    return f"INQ-{next_id:03d}"


def transition_risk_status(risk: Risk, new_status_value: str, actor: User) -> None:
    current_status = RiskStatus(risk.status)
    try:
        new_status = RiskStatus(new_status_value)
    except ValueError as exc:
        raise ValueError("Unknown status") from exc

    if new_status not in ALLOWED_TRANSITIONS[current_status]:
        raise RuntimeError(f"Transition {current_status.value} -> {new_status.value} is not allowed")
    if new_status == RiskStatus.ACTIVE and not risk.expert_id:
        raise ValueError("Нельзя перевести риск в работу без назначенного эксперта")

    risk.status = new_status.value
    add_audit_log(actor.full_name, "STATUS_CHANGE", risk.public_id, "success")
    queue_domain_event(
        "RiskStatusChanged",
        risk.public_id,
        {
            "risk_public_id": risk.public_id,
            "status": risk.status,
            "actor": actor.full_name,
        },
    )
    invalidate_query_cache()
    if new_status == RiskStatus.ACTIVE:
        enqueue_background_task(
            title=f"Пересчет уровня риска {risk.public_id}",
            description=f"Автоматический пересчет после перевода риска «{risk.title}» в работу",
            priority="HIGH" if risk.impact_level in {"High", "Critical"} else "MEDIUM",
        )


def create_risk_with_measures(data: dict, measures: Iterable[dict], actor: User) -> Risk:
    items = []
    for item in measures:
        action = item["action"].strip()
        responsible_person = item["responsible_person"].strip()
        deadline = item["deadline"].strip()
        priority = item["priority"].strip()
        if not action:
            raise ValueError("Укажите действие для меры")
        if not responsible_person or not deadline or not priority:
            raise ValueError("Для каждой меры укажите ответственного, срок и приоритет")
        items.append(
            {
                "action": action,
                "responsible_person": responsible_person,
                "deadline": deadline,
                "priority": priority,
            }
        )
    if not items:
        raise ValueError("Добавьте хотя бы одну меру минимизации")

    risk = Risk(
        public_id=next_public_risk_id(),
        title=data["title"].strip(),
        description=data["description"].strip(),
        category=data["category"].strip(),
        impact_level=data["impact_level"].strip(),
        status=RiskStatus.CREATED.value,
        owner_id=actor.id,
    )
    if not risk.title or not risk.description:
        raise ValueError("Risk title and description are required")

    with db.session.begin_nested():
        db.session.add(risk)
        db.session.flush()
        for item in items:
            measure = MitigationMeasure(
                risk_id=risk.id,
                action=item["action"],
                responsible_person=item["responsible_person"],
                deadline=item["deadline"],
                priority=item["priority"],
            )
            db.session.add(measure)
        add_audit_log(actor.full_name, "CREATE_RISK", risk.public_id, "success")
        queue_domain_event(
            "RiskCreated",
            risk.public_id,
            {
                "risk_public_id": risk.public_id,
                "actor": actor.full_name,
            },
        )

    invalidate_query_cache()
    db.session.commit()
    return risk


def append_measures_to_risk(risk: Risk, measures: Iterable[dict], actor: User) -> None:
    if risk.status in {RiskStatus.COMPLETED.value, RiskStatus.CANCELLED.value}:
        raise ValueError("Нельзя добавлять меры в завершенный или отмененный риск")

    items = []
    for item in measures:
        action = item["action"].strip()
        responsible_person = item["responsible_person"].strip()
        deadline = item["deadline"].strip()
        priority = item["priority"].strip()
        if not action:
            raise ValueError("Укажите действие для меры")
        if not responsible_person or not deadline or not priority:
            raise ValueError("Для каждой меры укажите ответственного, срок и приоритет")
        items.append(
            {
                "action": action,
                "responsible_person": responsible_person,
                "deadline": deadline,
                "priority": priority,
            }
        )
    if not items:
        raise ValueError("Добавьте хотя бы одну меру минимизации")

    with db.session.begin_nested():
        for item in items:
            db.session.add(
                MitigationMeasure(
                    risk_id=risk.id,
                    action=item["action"],
                    responsible_person=item["responsible_person"],
                    deadline=item["deadline"],
                    priority=item["priority"],
                )
            )
        add_audit_log(actor.full_name, "CREATE_MITIGATION", risk.public_id, "success")
        queue_domain_event(
            "RiskMeasuresUpdated",
            risk.public_id,
            {
                "risk_public_id": risk.public_id,
                "actor": actor.full_name,
            },
        )

    invalidate_query_cache()
    db.session.commit()


def create_incident_intake(data: dict, actor: User) -> IncidentIntake:
    title = data["title"].strip()
    description = data["description"].strip()
    if not title or not description:
        raise ValueError("Необходимо заполнить название и описание инцидента")

    intake = IncidentIntake(
        public_id=next_public_intake_id(),
        title=title,
        description=description,
        category=data["category"].strip(),
        impact_level=data["impact_level"].strip(),
        occurrence_date=data["occurrence_date"].strip(),
        actual_loss=int(data.get("actual_loss") or 0),
        status=IntakeStatus.PENDING.value,
        reporter_id=actor.id,
    )
    db.session.add(intake)
    add_audit_log(actor.full_name, "REGISTER_INCIDENT", intake.public_id, "success")
    queue_domain_event(
        "IncidentIntakeRegistered",
        intake.public_id,
        {
            "incident_intake_id": intake.public_id,
            "actor": actor.full_name,
        },
    )
    db.session.commit()
    return intake


def create_risk_from_incident_intake(intake: IncidentIntake, actor: User) -> Risk:
    if intake.status != IntakeStatus.PENDING.value:
        raise ValueError("Инцидент уже обработан")

    with db.session.begin_nested():
        risk = Risk(
            public_id=next_public_risk_id(),
            title=intake.title,
            description=intake.description,
            category=intake.category,
            impact_level=intake.impact_level,
            status=RiskStatus.CREATED.value,
            owner_id=actor.id,
        )
        db.session.add(risk)
        db.session.flush()

        incident = Incident(
            public_id=next_public_incident_id(),
            risk_id=risk.id,
            occurrence_date=intake.occurrence_date,
            actual_loss=intake.actual_loss,
            description=intake.description,
            reporter_id=intake.reporter_id,
        )
        db.session.add(incident)

        intake.status = IntakeStatus.PROCESSED.value
        intake.linked_risk_id = risk.id
        add_audit_log(actor.full_name, "CREATE_RISK_FROM_INCIDENT", f"{intake.public_id}->{risk.public_id}", "success")
        queue_domain_event(
            "RiskCreatedFromIncidentIntake",
            risk.public_id,
            {
                "risk_public_id": risk.public_id,
                "incident_intake_id": intake.public_id,
                "actor": actor.full_name,
            },
        )

    invalidate_query_cache()
    db.session.commit()
    return risk


def assign_expert_to_risk(risk: Risk, expert: User, actor: User) -> None:
    if risk.status != RiskStatus.CREATED.value:
        raise ValueError("Эксперта можно менять только у рисков в статусе «Создан»")
    if expert.role != Role.EXPERT.value:
        raise ValueError("Выбранный пользователь не является экспертом")
    if not expert.is_approved:
        raise ValueError("Выбранный эксперт еще не одобрен")
    risk.expert_id = expert.id
    add_audit_log(actor.full_name, "ASSIGN_EXPERT", risk.public_id, "success")
    queue_domain_event(
        "RiskExpertAssigned",
        risk.public_id,
        {
            "risk_public_id": risk.public_id,
            "expert_name": expert.full_name,
            "actor": actor.full_name,
        },
    )
    invalidate_query_cache()


def create_assessment(risk: Risk, expert: User, payload: dict) -> Assessment:
    probability = int(payload["probability"])
    impact_score = int(payload["impact_score"])
    recommendation = payload["recommendation"].strip()
    if not recommendation:
        raise ValueError("Recommendation is required")
    if probability < 1 or probability > 5 or impact_score < 1 or impact_score > 5:
        raise ValueError("Probability and impact must be between 1 and 5")

    assessment = Assessment(
        risk_id=risk.id,
        expert_id=expert.id,
        probability=probability,
        impact_score=impact_score,
        recommendation=recommendation,
    )
    db.session.add(assessment)
    risk.impact_level = assessment.severity_level
    add_audit_log(expert.full_name, "CREATE_ASSESSMENT", risk.public_id, "success")
    queue_domain_event(
        "RiskAssessed",
        risk.public_id,
        {
            "risk_public_id": risk.public_id,
            "severity_level": assessment.severity_level,
            "actor": expert.full_name,
        },
    )
    invalidate_query_cache()
    db.session.commit()
    return assessment


@app.before_request
def load_current_user():
    g.request_started_at = time.perf_counter()
    g.current_user = current_user_from_session()


@app.context_processor
def inject_globals():
    return {
        "current_user": getattr(g, "current_user", None),
        "role_label": lambda role: ROLE_LABELS.get(role, role),
        "status_label": status_label_text,
        "task_status_label": lambda status: TASK_STATUS_LABELS.get(status, status),
        "priority_label": lambda priority: PRIORITY_LABELS.get(priority, priority),
        "severity_label": severity_label_text,
        "category_label": category_label_text,
    }


@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", code=404, message="Entity not found"), 404


@app.errorhandler(409)
def conflict(_error):
    return render_template("error.html", code=409, message="Invalid state transition"), 409


@app.route("/")
def home():
    if g.current_user:
        return redirect(url_for(role_home_endpoint(g.current_user)))
    return redirect(url_for("auth_page"))


@app.route("/auth")
def auth_page():
    return render_template("auth.html", auth_mode=request.args.get("mode", "login"))


@app.post("/web/login")
def web_login():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    user = db.session.execute(db.select(User).where(User.email == email)).scalar_one_or_none()
    if not user or not check_password_hash(user.password_hash, password):
        flash("Invalid email or password", "error")
        return redirect(url_for("auth_page", mode="login"))
    if not user.is_approved:
        flash("Аккаунт ожидает одобрения администратором", "error")
        return redirect(url_for("auth_page", mode="login"))
    if user.role not in {Role.ADMIN.value, Role.RISK_MANAGER.value}:
        flash("Веб-кабинет доступен только администратору и риск-менеджеру", "error")
        return redirect(url_for("auth_page", mode="login"))
    session["access_token"] = create_access_token(user)
    flash("С возвращением", "success")
    return redirect(url_for(role_home_endpoint(user)))


@app.post("/web/register")
def web_register():
    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    if not full_name or not email or not password:
        flash("All fields are required", "error")
        return redirect(url_for("auth_page", mode="register"))
    if db.session.execute(db.select(User).where(User.email == email)).scalar_one_or_none():
        flash("User with this email already exists", "error")
        return redirect(url_for("auth_page", mode="register"))
    user = User(
        full_name=full_name,
        email=email,
        password_hash=generate_password_hash(password),
        role=Role.RISK_MANAGER.value,
        is_approved=False,
    )
    db.session.add(user)
    add_audit_log(user.full_name, "ACCESS_REQUEST", "USER", "success")
    db.session.commit()
    flash("Заявка отправлена. Доступ появится после одобрения администратором.", "success")
    return redirect(url_for("auth_page", mode="login"))


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth_page"))


@app.post("/api/v1/auth/register")
@app.post("/auth/register")
def api_register():
    payload = request.get_json(silent=True) or {}
    full_name = (payload.get("full_name") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    role = (payload.get("role") or Role.EXPERT.value).strip()
    if role not in {Role.WORKER.value, Role.EXPERT.value, Role.RISK_MANAGER.value}:
        role = Role.EXPERT.value
    if not full_name or not email or not password:
        return api_error("full_name, email and password are required", 400, "VALIDATION_ERROR")
    if db.session.execute(db.select(User).where(User.email == email)).scalar_one_or_none():
        return api_error("User already exists", 409, "USER_ALREADY_EXISTS")
    user = User(
        full_name=full_name,
        email=email,
        password_hash=generate_password_hash(password),
        role=role,
        is_approved=False,
    )
    db.session.add(user)
    add_audit_log(user.full_name, "ACCESS_REQUEST", "USER", "success")
    db.session.commit()
    return jsonify({"message": "Заявка отправлена на одобрение администратором"}), 201


@app.post("/api/v1/auth/login")
@app.post("/auth/login")
def api_login():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    user = db.session.execute(db.select(User).where(User.email == email)).scalar_one_or_none()
    if not user or not check_password_hash(user.password_hash, password):
        return api_error("Invalid credentials", 401, "INVALID_CREDENTIALS")
    if not user.is_approved:
        return api_error("Account awaits administrator approval", 403, "ACCOUNT_PENDING_APPROVAL")
    return jsonify({"access_token": create_access_token(user), "token_type": "bearer"})


@app.get("/api/v1/ping")
@app.get("/api/ping")
def api_ping():
    return jsonify({"ok": True, "message": "pong"})


@app.get("/api/v1/queries/lag")
@app.get("/api/queries/lag")
@api_roles_required(Role.ADMIN.value, Role.RISK_MANAGER.value, Role.EXPERT.value)
def api_query_lag():
    pending = db.session.scalar(
        db.select(func.count(DomainEvent.id)).where(DomainEvent.status == DomainEventStatus.PENDING.value)
    ) or 0
    failed = db.session.scalar(
        db.select(func.count(DomainEvent.id)).where(DomainEvent.status == DomainEventStatus.FAILED.value)
    ) or 0
    return jsonify({"pending_events": pending, "failed_events": failed, "eventual_consistency": True})


@app.get("/api/v1/queries/risks")
@app.get("/api/queries/risks")
@api_roles_required(Role.ADMIN.value, Role.RISK_MANAGER.value, Role.EXPERT.value)
def api_query_risks():
    status = (request.args.get("status") or "").strip()
    search = (request.args.get("search") or "").strip()
    rows = read_model_risks_query(status=status, search=search)
    if g.api_user.role == Role.EXPERT.value:
        rows = [item for item in rows if item.get("expert_name") == g.api_user.full_name]
    return collection_response(rows, dto_web_risk_list_item)


@app.get("/api/v1/queries/risks/<public_id>")
@app.get("/api/queries/risks/<public_id>")
@api_roles_required(Role.ADMIN.value, Role.RISK_MANAGER.value, Role.EXPERT.value)
def api_query_risk_detail(public_id: str):
    row = read_model_risk_by_public_id(public_id)
    if not row:
        return api_error("Not found", 404, "RISK_NOT_FOUND")
    if g.api_user.role == Role.EXPERT.value and row.get("expert_name") != g.api_user.full_name:
        return api_error("Forbidden", 403, "ACCESS_FORBIDDEN")
    return jsonify(dto_web_risk_list_item(row))


@app.post("/api/v1/commands/risks")
@app.post("/api/commands/risks")
@api_roles_required(Role.RISK_MANAGER.value, Role.ADMIN.value)
def api_command_create_risk():
    payload = request.get_json(silent=True) or {}
    measures = payload.get("measures") or []
    try:
        risk = create_risk_with_measures(payload, measures, g.api_user)
    except ValueError as error:
        db.session.rollback()
        return api_error(str(error), 400, "VALIDATION_ERROR")
    pending_events = db.session.scalar(
        db.select(func.count(DomainEvent.id)).where(DomainEvent.status == DomainEventStatus.PENDING.value)
    ) or 0
    return jsonify({"id": risk.public_id, "status": risk.status, "pending_events": pending_events, "eventual_consistency": True}), 201


@app.patch("/api/v1/commands/risks/<public_id>/status")
@app.patch("/api/commands/risks/<public_id>/status")
@api_roles_required(Role.RISK_MANAGER.value, Role.ADMIN.value)
def api_command_change_risk_status(public_id: str):
    risk = db.session.execute(db.select(Risk).where(Risk.public_id == public_id)).scalar_one_or_none()
    if not risk:
        return api_error("Not found", 404, "RISK_NOT_FOUND")
    if not can_manage_risk(g.api_user, risk):
        return api_error("Forbidden", 403, "ACCESS_FORBIDDEN")
    new_status = (request.get_json(silent=True) or {}).get("status", "")
    try:
        transition_risk_status(risk, new_status, g.api_user)
        db.session.commit()
    except RuntimeError as error:
        db.session.rollback()
        return api_error(str(error), 409, "INVALID_STATUS_TRANSITION")
    except ValueError as error:
        db.session.rollback()
        return api_error(str(error), 400, "VALIDATION_ERROR")
    pending_events = db.session.scalar(
        db.select(func.count(DomainEvent.id)).where(DomainEvent.status == DomainEventStatus.PENDING.value)
    ) or 0
    return jsonify({"id": risk.public_id, "status": risk.status, "pending_events": pending_events, "eventual_consistency": True})


@app.post("/api/v1/commands/risks/<public_id>/assign-expert")
@app.post("/api/commands/risks/<public_id>/assign-expert")
@api_roles_required(Role.RISK_MANAGER.value, Role.ADMIN.value)
def api_command_assign_expert(public_id: str):
    risk = db.session.execute(db.select(Risk).where(Risk.public_id == public_id)).scalar_one_or_none()
    if not risk:
        return api_error("Not found", 404, "RISK_NOT_FOUND")
    if not can_manage_risk(g.api_user, risk):
        return api_error("Forbidden", 403, "ACCESS_FORBIDDEN")
    expert_id = int((request.get_json(silent=True) or {}).get("expert_id") or 0)
    expert = db.session.get(User, expert_id)
    if not expert:
        return api_error("Not found", 404, "EXPERT_NOT_FOUND")
    try:
        assign_expert_to_risk(risk, expert, g.api_user)
        db.session.commit()
    except ValueError as error:
        db.session.rollback()
        return api_error(str(error), 400, "VALIDATION_ERROR")
    pending_events = db.session.scalar(
        db.select(func.count(DomainEvent.id)).where(DomainEvent.status == DomainEventStatus.PENDING.value)
    ) or 0
    return jsonify({"id": risk.public_id, "expert": expert.full_name, "pending_events": pending_events, "eventual_consistency": True})


@app.post("/api/v1/commands/events/process")
@app.post("/api/commands/events/process")
@api_roles_required(Role.RISK_MANAGER.value, Role.ADMIN.value)
def api_command_process_events():
    limit = int((request.get_json(silent=True) or {}).get("limit") or 10)
    limit = max(1, min(limit, 100))
    summary = process_domain_events(limit=limit)
    db.session.commit()
    invalidate_query_cache()
    return jsonify(summary)


@app.get("/api/v1/bff/web/dashboard")
@app.get("/api/bff/web/dashboard")
@api_roles_required(Role.RISK_MANAGER.value, Role.ADMIN.value)
def api_bff_web_dashboard():
    risks = read_model_risks_query()
    status_counts: dict[str, int] = {}
    for risk in risks:
        key = risk["risk_status"]
        status_counts[key] = status_counts.get(key, 0) + 1
    recent_logs = (
        db.session.execute(db.select(AuditLog).order_by(AuditLog.id.desc()).limit(5)).scalars().all()
    )
    pending_events = db.session.scalar(
        db.select(func.count(DomainEvent.id)).where(DomainEvent.status == DomainEventStatus.PENDING.value)
    ) or 0
    return jsonify(
        {
            "summary": {
                "risk_total": len(risks),
                "active_total": status_counts.get(RiskStatus.ACTIVE.value, 0),
                "created_total": status_counts.get(RiskStatus.CREATED.value, 0),
                "completed_total": status_counts.get(RiskStatus.COMPLETED.value, 0),
                "cancelled_total": status_counts.get(RiskStatus.CANCELLED.value, 0),
                "pending_event_total": pending_events,
            },
            "risk_cards": [dto_web_risk_list_item(item) for item in risks[:12]],
            "audit_feed": [
                {
                    "timestamp": item.timestamp,
                    "user_name": item.user_name,
                    "action": item.action,
                    "resource": item.resource,
                    "status": item.status,
                }
                for item in recent_logs
            ],
        }
    )


@app.get("/api/v1/bff/mobile/home")
@app.get("/api/bff/mobile/home")
@api_roles_required(Role.WORKER.value, Role.ADMIN.value)
def api_bff_mobile_home():
    intakes_query = db.select(IncidentIntake).order_by(IncidentIntake.id.desc())
    if g.api_user.role == Role.WORKER.value:
        intakes_query = intakes_query.where(IncidentIntake.reporter_id == g.api_user.id)
    intakes = db.session.execute(intakes_query.limit(5)).scalars().all()
    return jsonify(
        {
            "profile": {
                "full_name": g.api_user.full_name,
                "role": g.api_user.role,
            },
            "incident_queue": [
                {
                    "id": item.public_id,
                    "title": item.title,
                    "status": item.status,
                    "created_at": item.created_at.isoformat() if item.created_at else "",
                }
                for item in intakes
            ],
        }
    )


@app.get("/api/v1/bff/desktop/expert")
@app.get("/api/bff/desktop/expert")
@api_roles_required(Role.EXPERT.value, Role.ADMIN.value)
def api_bff_desktop_expert():
    risks = read_model_risks_query()
    if g.api_user.role == Role.EXPERT.value:
        risks = [item for item in risks if item.get("expert_name") == g.api_user.full_name]

    assessments_query = db.select(Assessment).order_by(Assessment.id.desc())
    if g.api_user.role == Role.EXPERT.value:
        assessments_query = assessments_query.where(Assessment.expert_id == g.api_user.id)
    assessments = db.session.execute(assessments_query.limit(5)).scalars().all()

    return jsonify(
        {
            "expert": {
                "full_name": g.api_user.full_name,
                "email": g.api_user.email,
            },
            "assigned_risks": [dto_mobile_incident_queue_item(item) for item in risks[:20]],
            "latest_assessments": [
                {
                    "id": item.id,
                    "risk_id": item.risk.public_id if item.risk else "",
                    "severity_level": item.severity_level,
                    "date": item.date.isoformat() if item.date else "",
                }
                for item in assessments
            ],
        }
    )


@app.get("/api/v1/heatmap")
@app.get("/api/heatmap")
@api_roles_required(Role.ADMIN.value, Role.RISK_MANAGER.value)
def api_heatmap():
    top_queries = (
        db.session.execute(
            text(
                """
                SELECT endpoint, COUNT(*) AS total_calls, ROUND(AVG(duration_ms), 2) AS avg_ms
                FROM api_request_metric
                WHERE request_kind = 'QUERY'
                GROUP BY endpoint
                ORDER BY total_calls DESC
                LIMIT 8
                """
            )
        )
        .mappings()
        .all()
    )
    top_commands = (
        db.session.execute(
            text(
                """
                SELECT endpoint, COUNT(*) AS total_calls, ROUND(AVG(duration_ms), 2) AS avg_ms
                FROM api_request_metric
                WHERE request_kind = 'COMMAND'
                GROUP BY endpoint
                ORDER BY avg_ms DESC, total_calls DESC
                LIMIT 8
                """
            )
        )
        .mappings()
        .all()
    )
    queue_stats = {
        "pending": db.session.scalar(
            db.select(func.count(DomainEvent.id)).where(DomainEvent.status == DomainEventStatus.PENDING.value)
        ) or 0,
        "failed": db.session.scalar(
            db.select(func.count(DomainEvent.id)).where(DomainEvent.status == DomainEventStatus.FAILED.value)
        ) or 0,
        "processed": db.session.scalar(
            db.select(func.count(DomainEvent.id)).where(DomainEvent.status == DomainEventStatus.PROCESSED.value)
        ) or 0,
    }
    return jsonify(
        {
            "hot_queries": [dict(item) for item in top_queries],
            "hot_commands": [dict(item) for item in top_commands],
            "event_queue": queue_stats,
        }
    )


@app.get("/api/v1/me")
@app.get("/api/me")
@api_auth_required
def api_me():
    return jsonify(
        {
            "id": g.api_user.id,
            "full_name": g.api_user.full_name,
            "email": g.api_user.email,
            "role": g.api_user.role,
            "joined_at": g.api_user.joined_at.isoformat() if g.api_user.joined_at else "",
            "is_approved": bool(g.api_user.is_approved),
        }
    )


@app.get("/api/v1/legacy/risks")
@app.get("/api/legacy/risks")
@api_auth_required
def api_risks():
    if g.api_user.role == Role.WORKER.value:
        return api_error("Forbidden", 403, "ACCESS_FORBIDDEN")
    risks = (
        db.session.execute(
            db.select(Risk)
            .options(joinedload(Risk.owner), joinedload(Risk.expert), joinedload(Risk.measures), joinedload(Risk.assessments))
            .order_by(Risk.id)
        )
        .unique()
        .scalars()
        .all()
    )
    if g.api_user.role == Role.EXPERT.value:
        risks = [risk for risk in risks if risk.expert_id == g.api_user.id]
    return collection_response(
        risks,
        lambda risk: {
            "id": risk.public_id,
            "title": risk.title,
            "description": risk.description,
            "category": risk.category,
            "impact_level": risk.impact_level,
            "owner": risk.owner.full_name,
            "expert": risk.expert.full_name if risk.expert else None,
            "status": risk.status,
            "measure_count": len(risk.measures),
            "assessment_count": len(risk.assessments),
            "incident_count": len(risk.incidents),
        },
    )


@app.get("/api/v1/expert/risks")
@app.get("/api/expert/risks")
@api_roles_required(Role.EXPERT.value, Role.ADMIN.value)
def api_expert_risks():
    query = (
        db.select(Risk)
        .options(
            joinedload(Risk.owner),
            joinedload(Risk.expert),
            joinedload(Risk.assessments),
            joinedload(Risk.incidents),
            joinedload(Risk.measures),
        )
        .order_by(Risk.id)
    )
    if g.api_user.role == Role.EXPERT.value:
        query = query.where(Risk.expert_id == g.api_user.id)
    risks = db.session.execute(query).unique().scalars().all()
    return collection_response(risks, lambda risk: _serialize_expert_risk(risk, g.api_user, include_details=False))


@app.get("/api/v1/expert/risks/<public_id>")
@app.get("/api/expert/risks/<public_id>")
@api_roles_required(Role.EXPERT.value, Role.ADMIN.value)
def api_expert_risk_detail(public_id: str):
    risk = (
        db.session.execute(
            db.select(Risk)
            .where(Risk.public_id == public_id)
            .options(
                joinedload(Risk.owner),
                joinedload(Risk.expert),
                joinedload(Risk.assessments),
                joinedload(Risk.incidents),
                joinedload(Risk.measures),
            )
        )
        .unique()
        .scalar_one_or_none()
    )
    if not risk:
        return api_error("Not found", 404, "RISK_NOT_FOUND")
    if g.api_user.role == Role.EXPERT.value and risk.expert_id != g.api_user.id:
        return api_error("Forbidden", 403, "ACCESS_FORBIDDEN")
    return jsonify(_serialize_expert_risk(risk, g.api_user, include_details=True))


@app.get("/api/v1/expert/assessments")
@app.get("/api/expert/assessments")
@api_roles_required(Role.EXPERT.value, Role.ADMIN.value)
def api_expert_assessments():
    query = db.select(Assessment).options(joinedload(Assessment.risk)).order_by(Assessment.id.desc())
    if g.api_user.role == Role.EXPERT.value:
        query = query.where(Assessment.expert_id == g.api_user.id)
    assessments = db.session.execute(query).scalars().all()
    return collection_response(
        assessments,
        lambda item: {
            "id": item.id,
            "risk_id": item.risk.public_id if item.risk else "",
            "risk_title": item.risk.title if item.risk else "",
            "probability": item.probability,
            "impact_score": item.impact_score,
            "recommendation": item.recommendation,
            "severity_level": item.severity_level,
            "date": item.date.isoformat() if item.date else "",
        },
    )


@app.post("/api/v1/incidents")
@app.post("/api/incidents")
@api_roles_required(Role.WORKER.value, Role.ADMIN.value)
def api_create_incident():
    payload = request.get_json(silent=True) or {}
    try:
        incident = create_incident_intake(payload, g.api_user)
    except (ValueError, KeyError) as error:
        db.session.rollback()
        return api_error(str(error), 400, "VALIDATION_ERROR")
    return jsonify({"id": incident.public_id, "status": incident.status}), 201


@app.post("/api/v1/risks/<public_id>/assessments")
@app.post("/api/risks/<public_id>/assessments")
@api_roles_required(Role.EXPERT.value, Role.ADMIN.value)
def api_create_assessment(public_id: str):
    risk = db.session.execute(db.select(Risk).where(Risk.public_id == public_id)).scalar_one_or_none()
    if not risk:
        return api_error("Not found", 404, "RISK_NOT_FOUND")
    if not can_assess_risk(g.api_user, risk):
        return api_error("Forbidden", 403, "ACCESS_FORBIDDEN")
    try:
        assessment = create_assessment(risk, g.api_user, request.get_json(silent=True) or {})
    except (ValueError, KeyError) as error:
        db.session.rollback()
        return api_error(str(error), 400, "VALIDATION_ERROR")
    return jsonify({"id": assessment.id, "severity_level": assessment.severity_level}), 201


@app.post("/api/v1/legacy/risks")
@app.post("/api/legacy/risks")
@api_roles_required(Role.RISK_MANAGER.value, Role.ADMIN.value)
def api_create_risk():
    payload = request.get_json(silent=True) or {}
    measures = payload.get("measures") or []
    try:
        risk = create_risk_with_measures(payload, measures, g.api_user)
    except ValueError as error:
        db.session.rollback()
        return api_error(str(error), 400, "VALIDATION_ERROR")
    return jsonify({"id": risk.public_id, "status": risk.status}), 201


@app.patch("/api/v1/legacy/risks/<public_id>/status")
@app.patch("/api/legacy/risks/<public_id>/status")
@api_roles_required(Role.RISK_MANAGER.value, Role.ADMIN.value)
def api_change_status(public_id: str):
    risk = db.session.execute(db.select(Risk).where(Risk.public_id == public_id)).scalar_one_or_none()
    if not risk:
        return api_error("Not found", 404, "RISK_NOT_FOUND")
    if not can_manage_risk(g.api_user, risk):
        return api_error("Forbidden", 403, "ACCESS_FORBIDDEN")
    new_status = (request.get_json(silent=True) or {}).get("status", "")
    try:
        transition_risk_status(risk, new_status, g.api_user)
        db.session.commit()
    except RuntimeError as error:
        db.session.rollback()
        return api_error(str(error), 409, "INVALID_STATUS_TRANSITION")
    except ValueError as error:
        db.session.rollback()
        return api_error(str(error), 400, "VALIDATION_ERROR")
    return jsonify({"id": risk.public_id, "status": risk.status})


@app.route("/risk-journal")
@manager_web_required
def risk_journal():
    risks = (
        db.session.execute(db.select(Risk).options(joinedload(Risk.owner), joinedload(Risk.expert), joinedload(Risk.assessments)).order_by(Risk.id))
        .unique()
        .scalars()
        .all()
    )
    experts = (
        db.session.execute(
            db.select(User).where(User.role == Role.EXPERT.value, User.is_approved.is_(True)).order_by(User.full_name)
        )
        .scalars()
        .all()
    )
    unassigned_count = sum(1 for risk in risks if not risk.expert_id and risk.status in {RiskStatus.CREATED.value, RiskStatus.ACTIVE.value})
    active_count = sum(1 for risk in risks if risk.status == RiskStatus.ACTIVE.value)
    critical_count = sum(1 for risk in risks if risk.impact_level in {"High", "Critical"})
    pending_incidents = (
        db.session.execute(
            db.select(IncidentIntake)
            .options(joinedload(IncidentIntake.reporter), joinedload(IncidentIntake.linked_risk))
            .where(IncidentIntake.status == IntakeStatus.PENDING.value)
            .order_by(IncidentIntake.id.desc())
        )
        .scalars()
        .all()
    )
    return render_template(
        "risk_journal.html",
        risks=risks,
        experts=experts,
        pending_incidents=pending_incidents,
        unassigned_count=unassigned_count,
        active_count=active_count,
        critical_count=critical_count,
    )


@app.route("/risks/<public_id>")
@manager_web_required
def risk_detail(public_id: str):
    risk = (
        db.session.execute(
            db.select(Risk)
            .options(
                joinedload(Risk.owner),
                joinedload(Risk.expert),
                joinedload(Risk.assessments).joinedload(Assessment.expert),
                joinedload(Risk.measures),
                joinedload(Risk.incidents).joinedload(Incident.reporter),
            )
            .where(Risk.public_id == public_id)
        )
        .unique()
        .scalar_one_or_none()
    )
    if not risk:
        abort(404)
    logs = (
        db.session.execute(db.select(AuditLog).where(AuditLog.resource == public_id).order_by(AuditLog.id.desc()).limit(8))
        .scalars()
        .all()
    )
    return render_template("risk_detail.html", risk=risk, logs=logs)


@app.route("/admin/users", methods=["GET", "POST"])
@admin_required
def admin_users():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", Role.WORKER.value)
        if role not in {Role.WORKER.value, Role.EXPERT.value, Role.RISK_MANAGER.value, Role.ADMIN.value}:
            role = Role.WORKER.value
        if not full_name or not email or not password:
            flash("Заполните ФИО, email и пароль", "error")
            return redirect(url_for("admin_users"))
        if db.session.execute(db.select(User).where(User.email == email)).scalar_one_or_none():
            flash("Пользователь с таким email уже существует", "error")
            return redirect(url_for("admin_users"))
        user = User(
            full_name=full_name,
            email=email,
            password_hash=generate_password_hash(password),
            role=role,
            is_approved=True,
        )
        db.session.add(user)
        add_audit_log(g.current_user.full_name, "CREATE_USER", email, "success")
        db.session.commit()
        flash("Пользователь создан и одобрен", "success")
        return redirect(url_for("admin_users"))

    users = db.session.execute(db.select(User).order_by(User.is_approved, User.role, User.full_name)).scalars().all()
    pending_count = sum(1 for user in users if not user.is_approved)
    return render_template("admin_users.html", users=users, pending_count=pending_count)


@app.post("/admin/users/<int:user_id>/approve")
@admin_required
def approve_user(user_id: int):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    user.is_approved = True
    add_audit_log(g.current_user.full_name, "APPROVE_USER", user.email, "success")
    db.session.commit()
    flash("Пользователь одобрен", "success")
    return redirect(url_for("admin_users"))


@app.post("/admin/users/<int:user_id>/deactivate")
@admin_required
def deactivate_user(user_id: int):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    if user.id == g.current_user.id:
        flash("Нельзя отключить собственный аккаунт", "error")
        return redirect(url_for("admin_users"))
    user.is_approved = False
    add_audit_log(g.current_user.full_name, "DEACTIVATE_USER", user.email, "success")
    db.session.commit()
    flash("Доступ пользователя отключен", "success")
    return redirect(url_for("admin_users"))


@app.post("/risks/<public_id>/assign-expert")
@manager_web_required
def assign_expert(public_id: str):
    if g.current_user.role not in {Role.ADMIN.value, Role.RISK_MANAGER.value}:
        flash("Назначать экспертов может только администратор или риск-менеджер", "error")
        return redirect(url_for("risk_journal"))
    risk = db.session.execute(db.select(Risk).where(Risk.public_id == public_id)).scalar_one_or_none()
    expert = db.session.get(User, int(request.form.get("expert_id") or 0))
    if not risk or not expert:
        abort(404)
    try:
        assign_expert_to_risk(risk, expert, g.current_user)
        db.session.commit()
        flash(f"{expert.full_name} назначен на {risk.public_id}", "success")
    except ValueError as error:
        db.session.rollback()
        flash(str(error), "error")
    return redirect(url_for("risk_journal"))


@app.post("/incident-intakes/<public_id>/create-risk")
@manager_web_required
def create_risk_from_intake(public_id: str):
    if g.current_user.role not in {Role.ADMIN.value, Role.RISK_MANAGER.value}:
        flash("Создавать риск из инцидента может только администратор или риск-менеджер", "error")
        return redirect(url_for("risk_journal"))
    intake = db.session.execute(db.select(IncidentIntake).where(IncidentIntake.public_id == public_id)).scalar_one_or_none()
    if not intake:
        abort(404)
    try:
        risk = create_risk_from_incident_intake(intake, g.current_user)
        flash(f"Риск {risk.public_id} создан из инцидента {intake.public_id}. Добавьте план минимизации.", "success")
        return redirect(url_for("create_mitigation_plan", risk_public_id=risk.public_id))
    except ValueError as error:
        db.session.rollback()
        flash(str(error), "error")
    return redirect(url_for("risk_journal"))


@app.route("/create-mitigation-plan", methods=["GET", "POST"])
@manager_web_required
def create_mitigation_plan():
    existing_risk = None
    selected_risk_public_id = request.values.get("risk_public_id", "").strip()
    if selected_risk_public_id:
        existing_risk = db.session.execute(
            db.select(Risk)
            .options(joinedload(Risk.owner), joinedload(Risk.measures))
            .where(Risk.public_id == selected_risk_public_id)
        ).unique().scalar_one_or_none()
        if not existing_risk:
            flash("Риск для добавления мер не найден", "error")
            return redirect(url_for("risk_journal"))
        if not can_manage_risk(g.current_user, existing_risk):
            flash("Вы можете добавлять меры только к своим рискам", "error")
            return redirect(url_for("risk_journal"))

    if request.method == "POST":
        actions = request.form.getlist("measure_action")
        people = request.form.getlist("measure_person")
        deadlines = request.form.getlist("measure_deadline")
        priorities = request.form.getlist("measure_priority")
        measures = [
            {
                "action": action,
                "responsible_person": person,
                "deadline": deadline,
                "priority": priority,
            }
            for action, person, deadline, priority in zip(actions, people, deadlines, priorities)
        ]
        try:
            if existing_risk:
                append_measures_to_risk(existing_risk, measures, g.current_user)
                flash(f"Меры добавлены к {existing_risk.public_id}", "success")
                return redirect(url_for("risk_detail", public_id=existing_risk.public_id))

            risk_data = {
                "title": request.form.get("title", ""),
                "description": request.form.get("description", ""),
                "category": request.form.get("category", ""),
                "impact_level": request.form.get("impact_level", ""),
            }
            create_risk_with_measures(risk_data, measures, g.current_user)
            flash("Риск и меры минимизации созданы одной транзакцией", "success")
            return redirect(url_for("risk_journal"))
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "error")
    return render_template("create_plan.html", existing_risk=existing_risk)


@app.post("/risks/<public_id>/status")
@manager_web_required
def change_risk_status(public_id: str):
    risk = db.session.execute(db.select(Risk).where(Risk.public_id == public_id)).scalar_one_or_none()
    if not risk:
        abort(404)
    if not can_manage_risk(g.current_user, risk):
        flash("Вы можете управлять только своими рисками", "error")
        return redirect(url_for("risk_journal"))
    try:
        transition_risk_status(risk, request.form.get("status", ""), g.current_user)
        db.session.commit()
        flash(f"{risk.public_id} переведен в статус «{status_label_text(risk.status)}»", "success")
    except RuntimeError:
        db.session.rollback()
        abort(409)
    except ValueError as error:
        db.session.rollback()
        flash(str(error), "error")
    return redirect(url_for("risk_journal"))


@app.route("/background-tasks")
@manager_web_required
def background_tasks():
    tasks = db.session.execute(db.select(BackgroundTask).order_by(BackgroundTask.id)).scalars().all()
    status_order = {
        TaskStatus.RUNNING.value: 0,
        TaskStatus.QUEUED.value: 1,
        TaskStatus.FAILED.value: 2,
        TaskStatus.COMPLETED.value: 3,
    }
    tasks.sort(key=lambda task: (status_order.get(task.status, 99), task.id))
    logs = db.session.execute(db.select(AuditLog).order_by(AuditLog.id.desc()).limit(8)).scalars().all()
    summary = {
        RiskStatus.ACTIVE.value: db.session.scalar(db.select(func.count(Risk.id)).where(Risk.status == RiskStatus.ACTIVE.value)),
        RiskStatus.CREATED.value: db.session.scalar(db.select(func.count(Risk.id)).where(Risk.status == RiskStatus.CREATED.value)),
        RiskStatus.COMPLETED.value: db.session.scalar(db.select(func.count(Risk.id)).where(Risk.status == RiskStatus.COMPLETED.value)),
        RiskStatus.CANCELLED.value: db.session.scalar(db.select(func.count(Risk.id)).where(Risk.status == RiskStatus.CANCELLED.value)),
    }
    visible_tasks = [task for task in tasks if task.status != TaskStatus.COMPLETED.value]
    return render_template("background_tasks.html", tasks=visible_tasks, logs=logs, summary=summary)


@app.post("/background-tasks/process")
@manager_web_required
def process_background_tasks():
    event_summary = process_domain_events(limit=20)
    add_audit_log(g.current_user.full_name, "REFRESH_RISK_SUMMARY", "RISKS", "success")
    db.session.commit()
    flash(
        f"Сводка рисков обновлена. События: обработано {event_summary['processed']}, ожидает {event_summary['remaining']}",
        "success",
    )
    return redirect(url_for("background_tasks"))


@app.post("/background-tasks/queue-step")
@manager_web_required
def process_background_queue_step():
    result = process_background_queue(g.current_user)
    db.session.commit()

    completed_title = result["completed"]
    started_title = result["started"]
    progressed_title = result["progressed"]
    progress_value = result["progress"]
    events_processed = result["events_processed"]
    events_remaining = result["events_remaining"]

    if completed_title and started_title:
        flash(
            f"Очередь обновлена: «{completed_title}» завершена, «{started_title}» переведена в работу",
            "success",
        )
    elif completed_title:
        flash(f"Очередь обновлена: «{completed_title}» завершена", "success")
    elif progressed_title:
        flash(f"Очередь обновлена: «{progressed_title}» прогресс {progress_value}%", "success")
    elif started_title:
        flash(f"Очередь обновлена: «{started_title}» переведена в работу", "success")
    else:
        flash("Очередь пуста: задач для обработки нет", "error")

    if events_processed != "0":
        flash(f"Read-модель синхронизирована: обработано событий {events_processed}, в очереди осталось {events_remaining}", "success")

    return redirect(url_for("background_tasks"))


@app.route("/incident-portal", methods=["GET", "POST"])
@manager_web_required
def incident_portal():
    flash("Веб-портал инцидентов отключен. Регистрация инцидентов выполняется в APK клиента работника.", "error")
    return redirect(url_for("risk_journal"))


@app.route("/expert-workspace", methods=["GET", "POST"])
@manager_web_required
def expert_workspace():
    if request.method == "POST":
        risk = db.session.execute(db.select(Risk).where(Risk.public_id == request.form.get("risk_id"))).scalar_one_or_none()
        if not risk:
            abort(404)
        if not can_assess_risk(g.current_user, risk):
            flash("You can assess only assigned risks", "error")
            return redirect(url_for("expert_workspace"))
        payload = {
            "probability": request.form.get("probability", ""),
            "impact_score": request.form.get("impact_score", ""),
            "recommendation": request.form.get("recommendation", ""),
        }
        try:
            create_assessment(risk, g.current_user, payload)
            flash("Assessment saved and severity level recalculated", "success")
            return redirect(url_for("expert_workspace"))
        except (ValueError, KeyError) as error:
            db.session.rollback()
            flash(str(error), "error")

    query = db.select(Risk).options(joinedload(Risk.owner), joinedload(Risk.expert), joinedload(Risk.assessments)).order_by(Risk.id)
    if g.current_user.role == Role.EXPERT.value:
        query = query.where(Risk.expert_id == g.current_user.id)
    risks = db.session.execute(query).unique().scalars().all()
    return render_template("expert_workspace.html", risks=risks)


@app.route("/reports")
@manager_web_required
def reports():
    risks = db.session.execute(db.select(Risk).options(joinedload(Risk.assessments))).unique().scalars().all()
    incidents = db.session.execute(db.select(Incident)).scalars().all()
    assessments = db.session.execute(db.select(Assessment)).scalars().all()
    status_counts = dict(db.session.execute(db.select(Risk.status, func.count(Risk.id)).group_by(Risk.status)).all())
    category_counts = dict(db.session.execute(db.select(Risk.category, func.count(Risk.id)).group_by(Risk.category)).all())
    avg_probability = round(sum(item.probability for item in assessments) / len(assessments), 2) if assessments else 0
    avg_impact = round(sum(item.impact_score for item in assessments) / len(assessments), 2) if assessments else 0
    critical_count = sum(1 for risk in risks if risk.impact_level in {"High", "Critical"})
    return render_template(
        "reports.html",
        risks=risks,
        incidents=incidents,
        assessments=assessments,
        status_counts=status_counts,
        category_counts=category_counts,
        avg_probability=avg_probability,
        avg_impact=avg_impact,
        critical_count=critical_count,
    )


@app.route("/reports/export.csv")
@manager_web_required
def export_report_csv():
    risks = (
        db.session.execute(
            db.select(Risk)
            .options(joinedload(Risk.owner), joinedload(Risk.expert), joinedload(Risk.assessments), joinedload(Risk.incidents), joinedload(Risk.measures))
            .order_by(Risk.id)
        )
        .unique()
        .scalars()
        .all()
    )
    buffer = StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(
        [
            "ID",
            "Название",
            "Категория",
            "Статус",
            "Уровень влияния",
            "Владелец",
            "Эксперт",
            "Количество мер",
            "Количество инцидентов",
            "Последняя оценка",
        ]
    )
    for risk in risks:
        latest = risk.assessments[-1].severity_level if risk.assessments else ""
        writer.writerow(
            [
                risk.public_id,
                risk.title,
                category_label_text(risk.category),
                status_label_text(risk.status),
                severity_label_text(risk.impact_level),
                risk.owner.full_name,
                risk.expert.full_name if risk.expert else "",
                len(risk.measures),
                len(risk.incidents),
                severity_label_text(latest) if latest else "",
            ]
        )
    return Response(
        "\ufeff" + buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=risk_report.csv"},
    )


@app.route("/profile")
@manager_web_required
def profile():
    my_risks = (
        db.session.execute(
            db.select(Risk).options(joinedload(Risk.owner)).where(Risk.owner_id == g.current_user.id).order_by(Risk.id)
        )
        .unique()
        .scalars()
        .all()
    )
    foreign_risk = (
        db.session.execute(db.select(Risk).options(joinedload(Risk.owner)).where(Risk.owner_id != g.current_user.id).limit(1))
        .unique()
        .scalar_one_or_none()
    )
    return render_template(
        "profile.html",
        permissions=available_actions(g.current_user),
        my_risks=my_risks,
        foreign_risk=foreign_risk,
    )


def seed_data():
    if db.session.execute(db.select(User)).first():
        return

    maria = User(
        full_name="Maria Rodriguez",
        email="maria.rodriguez@company.com",
        password_hash=generate_password_hash("password123"),
        role=Role.RISK_MANAGER.value,
        is_approved=True,
        joined_at=datetime(2024, 1, 15).date(),
    )
    john = User(
        full_name="John Smith",
        email="john.smith@company.com",
        password_hash=generate_password_hash("password123"),
        role=Role.WORKER.value,
        is_approved=True,
        joined_at=datetime(2024, 2, 12).date(),
    )
    sarah = User(
        full_name="Sarah Chen",
        email="sarah.chen@company.com",
        password_hash=generate_password_hash("password123"),
        role=Role.EXPERT.value,
        is_approved=True,
        joined_at=datetime(2024, 3, 8).date(),
    )
    michael = User(
        full_name="Michael Brown",
        email="michael.brown@company.com",
        password_hash=generate_password_hash("password123"),
        role=Role.ADMIN.value,
        is_approved=True,
        joined_at=datetime(2024, 1, 4).date(),
    )
    db.session.add_all([maria, john, sarah, michael])
    db.session.flush()

    risks = [
        Risk(public_id="RISK-001", title="Data Center Power Failure", description="Risk of power outage at primary data center", category="Infrastructure", impact_level="High", status=RiskStatus.ACTIVE.value, owner_id=maria.id, expert_id=sarah.id, created_at=datetime(2026, 4, 10).date()),
        Risk(public_id="RISK-002", title="Vendor Contract Expiration", description="Critical vendor contract expires in 30 days", category="Compliance", impact_level="Medium", status=RiskStatus.CREATED.value, owner_id=john.id, expert_id=sarah.id, created_at=datetime(2026, 4, 11).date()),
        Risk(public_id="RISK-003", title="API Rate Limit Breach", description="Exceeded API rate limits causing service degradation", category="Technology", impact_level="High", status=RiskStatus.COMPLETED.value, owner_id=john.id, expert_id=sarah.id, created_at=datetime(2026, 4, 8).date()),
        Risk(public_id="RISK-004", title="Security Certificate Renewal", description="SSL certificate renewal process", category="Security", impact_level="Medium", status=RiskStatus.CANCELLED.value, owner_id=michael.id, expert_id=sarah.id, created_at=datetime(2026, 4, 9).date()),
        Risk(public_id="RISK-005", title="Database Migration Delay", description="Potential delays in scheduled database migration", category="Operational", impact_level="High", status=RiskStatus.ACTIVE.value, owner_id=maria.id, expert_id=sarah.id, created_at=datetime(2026, 4, 12).date()),
        Risk(public_id="RISK-007", title="Network Infrastructure Upgrade", description="Upgrade dependencies across branch locations", category="Operational", impact_level="Low", status=RiskStatus.COMPLETED.value, owner_id=maria.id, expert_id=sarah.id, created_at=datetime(2026, 4, 1).date()),
    ]
    db.session.add_all(risks)
    db.session.flush()

    db.session.add_all(
        [
            MitigationMeasure(risk_id=risks[0].id, action="Install redundant UPS capacity", responsible_person="Carlos Vega", deadline="2026-04-22", priority="High"),
            MitigationMeasure(risk_id=risks[0].id, action="Test failover runbook", responsible_person="Maria Rodriguez", deadline="2026-04-25", priority="Medium"),
            MitigationMeasure(risk_id=risks[4].id, action="Replan migration window", responsible_person="Maria Rodriguez", deadline="2026-04-30", priority="High"),
        ]
    )

    db.session.add_all(
        [
            Assessment(risk_id=risks[0].id, probability=4, impact_score=5, recommendation="Run failover drill and increase reserve power capacity.", expert_id=sarah.id, date=datetime(2026, 4, 11).date()),
            Assessment(risk_id=risks[2].id, probability=3, impact_score=4, recommendation="Introduce request throttling and provider fallback.", expert_id=sarah.id, date=datetime(2026, 4, 9).date()),
            Assessment(risk_id=risks[4].id, probability=5, impact_score=4, recommendation="Move migration to low-load window and prepare rollback plan.", expert_id=sarah.id, date=datetime(2026, 4, 13).date()),
        ]
    )

    db.session.add_all(
        [
            Incident(public_id="INC-001", risk_id=risks[0].id, occurrence_date="2026-04-10 09:15", actual_loss=12000, description="Short power interruption in primary data center.", reporter_id=john.id),
            Incident(public_id="INC-002", risk_id=risks[2].id, occurrence_date="2026-04-08 16:40", actual_loss=3000, description="Partner API request limit exceeded during reconciliation.", reporter_id=john.id),
        ]
    )

    db.session.add(
        IncidentIntake(
            public_id="INQ-001",
            title="Подозрение на утечку данных подрядчика",
            description="Работник заметил несоответствие прав доступа во внешнем кабинете поставщика.",
            category="Security",
            impact_level="High",
            occurrence_date="2026-04-13 11:20",
            actual_loss=0,
            status=IntakeStatus.PENDING.value,
            reporter_id=john.id,
        )
    )

    db.session.add_all(
        [
            BackgroundTask(title="Risk Impact Analysis", description="Analyzing potential impact of active operational risks", priority="HIGH", status=TaskStatus.COMPLETED.value, progress=100, started_at="2026-04-13 14:30:00", eta=""),
            BackgroundTask(title="Compliance Report Generation", description="Generating monthly compliance report for Q2 2026", priority="MEDIUM", status=TaskStatus.RUNNING.value, progress=89, started_at="2026-04-13 14:25:00", eta="2026-04-13 15:00:00"),
            BackgroundTask(title="Risk Correlation Detection", description="Identifying patterns and correlations between risks", priority="LOW", status=TaskStatus.QUEUED.value, progress=0, started_at="2026-04-13 14:35:00", eta=""),
            BackgroundTask(title="Automated Risk Scoring", description="Recalculating risk scores based on new data", priority="HIGH", status=TaskStatus.COMPLETED.value, progress=100, started_at="2026-04-13 14:00:00", eta=""),
            BackgroundTask(title="Data Backup Verification", description="Verifying integrity of risk database backups", priority="MEDIUM", status=TaskStatus.FAILED.value, progress=45, started_at="2026-04-13 13:45:00", eta=""),
        ]
    )

    db.session.add_all(
        [
            AuditLog(timestamp="2026-04-13 14:35:22", user_name="Maria Rodriguez", action="STATUS_CHANGE", resource="RISK-001", status="success"),
            AuditLog(timestamp="2026-04-13 14:30:15", user_name="John Smith", action="CREATE_RISK", resource="RISK-006", status="success"),
            AuditLog(timestamp="2026-04-13 14:28:45", user_name="Sarah Chen", action="DELETE_RISK", resource="RISK-003", status="failure"),
            AuditLog(timestamp="2026-04-13 14:25:30", user_name="Maria Rodriguez", action="CREATE_MITIGATION", resource="PLAN-012", status="success"),
            AuditLog(timestamp="2026-04-13 14:20:10", user_name="Michael Brown", action="UPDATE_RISK", resource="RISK-004", status="success"),
        ]
    )
    db.session.commit()


with app.app_context():
    db.create_all()
    seed_data()
    seed_read_model_from_write_model()
    db.session.commit()


if __name__ == "__main__":
    host = os.getenv("RISKGUARD_HOST", "127.0.0.1")
    port = int(os.getenv("RISKGUARD_PORT", "5000"))
    debug = os.getenv("RISKGUARD_DEBUG", "1") == "1"
    app.run(host=host, port=port, debug=debug)
