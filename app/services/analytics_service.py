from collections import defaultdict
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from fastapi import Request
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy import distinct, func, or_
from sqlalchemy.orm import Session

from app.core.security import utc_now
from app.database import engine
from app.models.billing import PaymentOrder
from app.models.web_analytics_event import WebAnalyticsEvent
from app.models.web_analytics_presence import WebAnalyticsPresence
from app.schemas.analytics import TrackHeartbeatRequest, TrackPageViewRequest

SESSION_TIMEOUT_MINUTES = 30
ACTIVE_WINDOW_SECONDS = 90
EVENT_PAGE_VIEW = "page_view"
EVENT_HEARTBEAT = "heartbeat"
PAYMENT_STATUS_PAID = "paid"
POPULAR_PAGE_LABELS = {
    "/": "Landing page",
    "/login": "Login",
    "/teacher": "Teacher",
    "/student": "Student",
    "/teacher/exams": "Teacher exams",
    "/student/exams": "Student exams",
}
POPULAR_PAGE_PATHS = tuple(POPULAR_PAGE_LABELS.keys())
POPULAR_PAGE_ORDER = {path: index for index, path in enumerate(POPULAR_PAGE_PATHS)}


def bootstrap_web_analytics_storage() -> None:
    WebAnalyticsEvent.__table__.create(bind=engine, checkfirst=True)
    WebAnalyticsPresence.__table__.create(bind=engine, checkfirst=True)


def _start_of_day(value: datetime) -> datetime:
    return value.replace(hour=0, minute=0, second=0, microsecond=0)


def _start_of_year(value: datetime) -> datetime:
    return value.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _normalize_path(value: str | None) -> str:
    raw_value = (value or "").strip()
    if not raw_value:
        return "/"

    parsed = urlparse(raw_value)
    path = parsed.path or raw_value
    if not path.startswith("/"):
        path = f"/{path}"

    return path.rstrip("/") or "/"


def _tracked_page_filter(column):
    filters = []
    for path in POPULAR_PAGE_PATHS:
        filters.append(column == path)
        if path == "/":
            filters.append(column.like("/?%"))
            continue
        filters.append(column == f"{path}/")
        filters.append(column.like(f"{path}?%"))
    return or_(*filters)


def _period_window(now: datetime, period: str) -> dict:
    if period == "30d":
        day_count = 30
        current_start = _start_of_day(now) - timedelta(days=day_count - 1)
        previous_start = current_start - timedelta(days=day_count)
        return {
            "period": "30d",
            "label": "30 ngày qua",
            "current_start": current_start,
            "current_end": now,
            "previous_start": previous_start,
            "previous_end": current_start,
            "day_count": day_count,
            "granularity": "day",
        }

    if period == "year":
        current_start = _start_of_year(now)
        previous_start = current_start.replace(year=current_start.year - 1)
        previous_end = previous_start + (now - current_start)
        return {
            "period": "year",
            "label": "năm nay",
            "current_start": current_start,
            "current_end": now,
            "previous_start": previous_start,
            "previous_end": previous_end,
            "day_count": None,
            "granularity": "month",
        }

    day_count = 7
    current_start = _start_of_day(now) - timedelta(days=day_count - 1)
    previous_start = current_start - timedelta(days=day_count)
    return {
        "period": "7d",
        "label": "7 ngày qua",
        "current_start": current_start,
        "current_end": now,
        "previous_start": previous_start,
        "previous_end": current_start,
        "day_count": day_count,
        "granularity": "day",
    }


def _client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip() or None
    return request.client.host if request.client else None


def _clean_text(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized[:max_length]


def _device_type(user_agent: str) -> str:
    ua = user_agent.lower()
    if any(token in ua for token in ("ipad", "tablet")):
        return "tablet"
    if any(token in ua for token in ("mobile", "android", "iphone", "ipod")):
        return "mobile"
    return "desktop"


def _browser(user_agent: str) -> str:
    ua = user_agent.lower()
    if "edg/" in ua:
        return "Edge"
    if "chrome/" in ua and "chromium" not in ua:
        return "Chrome"
    if "firefox/" in ua:
        return "Firefox"
    if "safari/" in ua and "chrome/" not in ua:
        return "Safari"
    return "Other"


def _os(user_agent: str) -> str:
    ua = user_agent.lower()
    if "windows" in ua:
        return "Windows"
    if "mac os" in ua or "macintosh" in ua:
        return "macOS"
    if "android" in ua:
        return "Android"
    if "iphone" in ua or "ipad" in ua:
        return "iOS"
    if "linux" in ua:
        return "Linux"
    return "Other"


def _hostname(value: str | None) -> str:
    if not value:
        return ""
    parsed = urlparse(value)
    return (parsed.hostname or "").lower()


def _traffic_source(referrer: str | None, origin: str | None) -> str:
    referrer_host = _hostname(referrer)
    origin_host = _hostname(origin)
    if not referrer_host:
        return "direct"
    if origin_host and referrer_host == origin_host:
        return "internal"
    if any(
        token in referrer_host
        for token in ("google.", "bing.", "yahoo.", "duckduckgo.", "coccoc.")
    ):
        return "search"
    if any(
        token in referrer_host
        for token in ("facebook.", "tiktok.", "youtube.", "instagram.", "zalo.")
    ):
        return "social"
    return "referral"


def _upsert_presence(
    db: Session,
    *,
    visitor_id: str,
    session_id: str,
    user_id: int | None,
    path: str,
    title: str | None,
    origin: str | None,
    screen_width: int | None,
    screen_height: int | None,
    user_agent: str,
    ip_address: str | None,
    seen_at: datetime,
) -> None:
    values = {
        "visitor_id": visitor_id,
        "session_id": session_id,
        "user_id": user_id,
        "path": path,
        "title": title,
        "origin": origin,
        "device_type": _device_type(user_agent),
        "browser": _browser(user_agent),
        "os": _os(user_agent),
        "screen_width": screen_width,
        "screen_height": screen_height,
        "user_agent": user_agent,
        "ip_address": ip_address,
        "last_seen_at": seen_at,
    }

    bind = db.get_bind()
    if bind is not None and bind.dialect.name == "postgresql":
        update_values = {
            key: value
            for key, value in values.items()
            if key != "session_id"
        }
        statement = (
            postgresql_insert(WebAnalyticsPresence)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[WebAnalyticsPresence.session_id],
                set_=update_values,
            )
        )
        db.execute(statement)
        return

    presence = (
        db.query(WebAnalyticsPresence)
        .filter(WebAnalyticsPresence.session_id == session_id)
        .first()
    )
    if presence is None:
        presence = WebAnalyticsPresence(session_id=session_id)
        db.add(presence)

    for key, value in values.items():
        setattr(presence, key, value)


def record_page_view(
    db: Session,
    payload: TrackPageViewRequest,
    request: Request,
) -> dict:
    user_agent = _clean_text(request.headers.get("user-agent"), 2048) or ""
    referrer = _clean_text(payload.referrer or request.headers.get("referer"), 2048)
    origin = _clean_text(payload.origin or request.headers.get("origin"), 512)
    visitor_id = payload.visitor_id.strip()[:128]
    session_id = payload.session_id.strip()[:128]
    path = _normalize_path(payload.path)[:2048]
    title = _clean_text(payload.title, 512)
    ip_address = _client_ip(request)
    now = utc_now()

    event = WebAnalyticsEvent(
        visitor_id=visitor_id,
        session_id=session_id,
        user_id=payload.user_id,
        event_type=EVENT_PAGE_VIEW,
        path=path,
        title=title,
        referrer=referrer,
        origin=origin,
        source=_traffic_source(referrer, origin),
        device_type=_device_type(user_agent),
        browser=_browser(user_agent),
        os=_os(user_agent),
        screen_width=payload.screen_width,
        screen_height=payload.screen_height,
        user_agent=user_agent,
        ip_address=ip_address,
        created_at=now,
    )
    db.add(event)
    _upsert_presence(
        db,
        visitor_id=visitor_id,
        session_id=session_id,
        user_id=payload.user_id,
        path=path,
        title=title,
        origin=origin,
        screen_width=payload.screen_width,
        screen_height=payload.screen_height,
        user_agent=user_agent,
        ip_address=ip_address,
        seen_at=now,
    )
    db.commit()
    db.refresh(event)
    return {"message": "Page view tracked", "event_id": event.id}


def record_heartbeat(
    db: Session,
    payload: TrackHeartbeatRequest,
    request: Request,
) -> dict:
    user_agent = _clean_text(request.headers.get("user-agent"), 2048) or ""
    origin = _clean_text(payload.origin or request.headers.get("origin"), 512)
    visitor_id = payload.visitor_id.strip()[:128]
    session_id = payload.session_id.strip()[:128]
    path = _normalize_path(payload.path)[:2048]
    title = _clean_text(payload.title, 512)
    ip_address = _client_ip(request)
    now = utc_now()

    event = WebAnalyticsEvent(
        visitor_id=visitor_id,
        session_id=session_id,
        user_id=payload.user_id,
        event_type=EVENT_HEARTBEAT,
        path=path,
        title=title,
        origin=origin,
        source="internal",
        device_type=_device_type(user_agent),
        browser=_browser(user_agent),
        os=_os(user_agent),
        screen_width=payload.screen_width,
        screen_height=payload.screen_height,
        user_agent=user_agent,
        ip_address=ip_address,
        created_at=now,
    )
    db.add(event)
    _upsert_presence(
        db,
        visitor_id=visitor_id,
        session_id=session_id,
        user_id=payload.user_id,
        path=path,
        title=title,
        origin=origin,
        screen_width=payload.screen_width,
        screen_height=payload.screen_height,
        user_agent=user_agent,
        ip_address=ip_address,
        seen_at=now,
    )
    db.commit()
    db.refresh(event)
    return {"message": "Heartbeat tracked", "event_id": event.id}


def _count_page_views(db: Session, start: datetime, end: datetime) -> int:
    return int(
        db.query(func.count(WebAnalyticsEvent.id))
        .filter(
            WebAnalyticsEvent.event_type == EVENT_PAGE_VIEW,
            WebAnalyticsEvent.created_at >= start,
            WebAnalyticsEvent.created_at < end,
            _tracked_page_filter(WebAnalyticsEvent.path),
        )
        .scalar()
        or 0
    )


def _count_unique(db: Session, column, start: datetime, end: datetime) -> int:
    return int(
        db.query(func.count(distinct(column)))
        .filter(
            WebAnalyticsEvent.event_type == EVENT_PAGE_VIEW,
            WebAnalyticsEvent.created_at >= start,
            WebAnalyticsEvent.created_at < end,
            _tracked_page_filter(WebAnalyticsEvent.path),
        )
        .scalar()
        or 0
    )


def _bounce_rate(db: Session, start: datetime, end: datetime) -> float:
    rows = (
        db.query(WebAnalyticsEvent.session_id, func.count(WebAnalyticsEvent.id))
        .filter(
            WebAnalyticsEvent.event_type == EVENT_PAGE_VIEW,
            WebAnalyticsEvent.created_at >= start,
            WebAnalyticsEvent.created_at < end,
            _tracked_page_filter(WebAnalyticsEvent.path),
        )
        .group_by(WebAnalyticsEvent.session_id)
        .all()
    )
    if not rows:
        return 0.0
    bounced = sum(1 for _, count in rows if int(count or 0) <= 1)
    return round((bounced / len(rows)) * 100, 1)


def _format_percent_trend(current: float, previous: float) -> str:
    if previous == 0:
        if current == 0:
            return "0%"
        return "+100%"
    return f"{((current - previous) / previous) * 100:+.1f}%"


def _metric(
    key: str,
    label: str,
    value: float,
    previous: float,
    suffix: str = "",
    subtext: str = "",
    lower_is_better: bool = False,
) -> dict:
    is_up = value >= previous
    if lower_is_better:
        is_up = value <= previous
    return {
        "key": key,
        "label": label,
        "value": value,
        "suffix": suffix,
        "trend": _format_percent_trend(value, previous),
        "is_up": is_up,
        "subtext": subtext,
    }


def _daily_traffic(db: Session, window: dict) -> list[dict]:
    day_count = int(window["day_count"] or 7)
    current_start = window["current_start"]
    previous_start = window["previous_start"]
    current_visitors = [set() for _ in range(day_count)]
    previous_visitors = [set() for _ in range(day_count)]
    current_end = current_start + timedelta(days=day_count)

    rows = (
        db.query(WebAnalyticsEvent.created_at, WebAnalyticsEvent.visitor_id)
        .filter(
            WebAnalyticsEvent.event_type == EVENT_PAGE_VIEW,
            WebAnalyticsEvent.created_at >= previous_start,
            WebAnalyticsEvent.created_at < current_end,
            _tracked_page_filter(WebAnalyticsEvent.path),
        )
        .all()
    )
    for created_at, visitor_id in rows:
        created_at = _normalize_datetime(created_at)
        if current_start <= created_at < current_end:
            current_visitors[(created_at.date() - current_start.date()).days].add(visitor_id)
        elif previous_start <= created_at < current_start:
            previous_visitors[(created_at.date() - previous_start.date()).days].add(visitor_id)

    return [
        {
            "name": (current_start + timedelta(days=index)).strftime("%d/%m"),
            "current": len(current_visitors[index]),
            "last": len(previous_visitors[index]),
        }
        for index in range(day_count)
    ]


def _monthly_traffic(db: Session, now: datetime) -> list[dict]:
    current_year = now.year
    previous_year = current_year - 1
    current_visitors = [set() for _ in range(12)]
    previous_visitors = [set() for _ in range(12)]
    start = datetime(previous_year, 1, 1, tzinfo=now.tzinfo)
    end = datetime(current_year + 1, 1, 1, tzinfo=now.tzinfo)

    rows = (
        db.query(WebAnalyticsEvent.created_at, WebAnalyticsEvent.visitor_id)
        .filter(
            WebAnalyticsEvent.event_type == EVENT_PAGE_VIEW,
            WebAnalyticsEvent.created_at >= start,
            WebAnalyticsEvent.created_at < end,
            _tracked_page_filter(WebAnalyticsEvent.path),
        )
        .all()
    )
    for created_at, visitor_id in rows:
        created_at = _normalize_datetime(created_at)
        if created_at.year == current_year:
            current_visitors[created_at.month - 1].add(visitor_id)
        elif created_at.year == previous_year:
            previous_visitors[created_at.month - 1].add(visitor_id)

    return [
        {
            "name": f"T{month}",
            "current": len(current_visitors[month - 1]),
            "last": len(previous_visitors[month - 1]),
        }
        for month in range(1, 13)
    ]


def _traffic(db: Session, now: datetime, window: dict) -> list[dict]:
    if window["period"] == "year":
        return _monthly_traffic(db, now)
    return _daily_traffic(db, window)


def _paid_order_rows(db: Session, start: datetime, end: datetime) -> list[tuple]:
    return (
        db.query(PaymentOrder.paid_at, PaymentOrder.amount_vnd)
        .filter(
            PaymentOrder.status == PAYMENT_STATUS_PAID,
            PaymentOrder.paid_at.isnot(None),
            PaymentOrder.paid_at >= start,
            PaymentOrder.paid_at < end,
        )
        .all()
    )


def _payment_totals(db: Session, start: datetime, end: datetime) -> tuple[int, int]:
    rows = _paid_order_rows(db, start, end)
    return sum(int(amount or 0) for _, amount in rows), len(rows)


def _daily_cash_flow(db: Session, window: dict) -> list[dict]:
    day_count = int(window["day_count"] or 7)
    current_start = window["current_start"]
    previous_start = window["previous_start"]
    current_end = current_start + timedelta(days=day_count)
    current_amounts = [0] * day_count
    previous_amounts = [0] * day_count
    current_orders = [0] * day_count

    rows = _paid_order_rows(db, previous_start, current_end)
    for paid_at, amount in rows:
        paid_at = _normalize_datetime(paid_at)
        if current_start <= paid_at < current_end:
            index = (paid_at.date() - current_start.date()).days
            current_amounts[index] += int(amount or 0)
            current_orders[index] += 1
        elif previous_start <= paid_at < current_start:
            index = (paid_at.date() - previous_start.date()).days
            previous_amounts[index] += int(amount or 0)

    return [
        {
            "name": (current_start + timedelta(days=index)).strftime("%d/%m"),
            "current": current_amounts[index],
            "last": previous_amounts[index],
            "paid_orders": current_orders[index],
        }
        for index in range(day_count)
    ]


def _monthly_cash_flow(db: Session, now: datetime) -> list[dict]:
    current_year = now.year
    previous_year = current_year - 1
    current_amounts = [0] * 12
    previous_amounts = [0] * 12
    current_orders = [0] * 12
    start = datetime(previous_year, 1, 1, tzinfo=now.tzinfo)
    end = datetime(current_year + 1, 1, 1, tzinfo=now.tzinfo)

    rows = _paid_order_rows(db, start, end)
    for paid_at, amount in rows:
        paid_at = _normalize_datetime(paid_at)
        month_index = paid_at.month - 1
        if paid_at.year == current_year:
            current_amounts[month_index] += int(amount or 0)
            current_orders[month_index] += 1
        elif paid_at.year == previous_year:
            previous_amounts[month_index] += int(amount or 0)

    return [
        {
            "name": f"T{month}",
            "current": current_amounts[month - 1],
            "last": previous_amounts[month - 1],
            "paid_orders": current_orders[month - 1],
        }
        for month in range(1, 13)
    ]


def get_payment_analytics_overview(db: Session, period: str = "7d") -> dict:
    now = utc_now()
    window = _period_window(now, period)
    current_revenue, current_orders = _payment_totals(
        db,
        window["current_start"],
        window["current_end"],
    )
    previous_revenue, previous_orders = _payment_totals(
        db,
        window["previous_start"],
        window["previous_end"],
    )
    current_average = current_revenue / current_orders if current_orders else 0
    previous_average = previous_revenue / previous_orders if previous_orders else 0
    cash_flow = (
        _monthly_cash_flow(db, now)
        if window["period"] == "year"
        else _daily_cash_flow(db, window)
    )

    return {
        "metrics": [
            _metric(
                "revenue",
                "Doanh thu",
                current_revenue,
                previous_revenue,
                suffix="VNĐ",
                subtext=f"{current_orders} đơn đã thanh toán · {window['label']}",
            ),
            _metric(
                "average_order_value",
                "Giá trị trung bình đơn",
                current_average,
                previous_average,
                suffix="VNĐ",
                subtext=window["label"],
            ),
        ],
        "cash_flow": cash_flow,
        "paid_orders": current_orders,
        "last_updated_at": now,
    }


def _breakdown(db: Session, column, start: datetime, end: datetime) -> list[dict]:
    rows = (
        db.query(column, func.count(WebAnalyticsEvent.id))
        .filter(
            WebAnalyticsEvent.event_type == EVENT_PAGE_VIEW,
            WebAnalyticsEvent.created_at >= start,
            WebAnalyticsEvent.created_at < end,
            _tracked_page_filter(WebAnalyticsEvent.path),
        )
        .group_by(column)
        .order_by(func.count(WebAnalyticsEvent.id).desc())
        .all()
    )
    return [{"name": name or "unknown", "value": int(value or 0)} for name, value in rows]


def _popular_pages(db: Session, start: datetime, end: datetime) -> list[dict]:
    rows = (
        db.query(
            WebAnalyticsEvent.path,
            WebAnalyticsEvent.visitor_id,
        )
        .filter(
            WebAnalyticsEvent.event_type == EVENT_PAGE_VIEW,
            WebAnalyticsEvent.created_at >= start,
            WebAnalyticsEvent.created_at < end,
            _tracked_page_filter(WebAnalyticsEvent.path),
        )
        .all()
    )

    views_by_path: dict[str, int] = defaultdict(int)
    visitors_by_path: dict[str, set[str]] = defaultdict(set)
    for raw_path, visitor_id in rows:
        path = _normalize_path(raw_path)
        if path not in POPULAR_PAGE_LABELS:
            continue
        views_by_path[path] += 1
        visitors_by_path[path].add(visitor_id)

    sorted_paths = sorted(
        views_by_path,
        key=lambda path: (-views_by_path[path], POPULAR_PAGE_ORDER[path]),
    )
    return [
        {
            "path": path,
            "title": POPULAR_PAGE_LABELS[path],
            "views": views_by_path[path],
            "unique_visitors": len(visitors_by_path[path]),
        }
        for path in sorted_paths[:10]
    ]


def get_web_realtime_overview(db: Session) -> dict:
    now = utc_now()
    active_after = now - timedelta(seconds=ACTIVE_WINDOW_SECONDS)
    active_filter = WebAnalyticsPresence.last_seen_at >= active_after

    active_users = int(
        db.query(func.count(distinct(WebAnalyticsPresence.visitor_id)))
        .filter(active_filter, _tracked_page_filter(WebAnalyticsPresence.path))
        .scalar()
        or 0
    )
    active_sessions = int(
        db.query(func.count(distinct(WebAnalyticsPresence.session_id)))
        .filter(active_filter, _tracked_page_filter(WebAnalyticsPresence.path))
        .scalar()
        or 0
    )
    active_page_rows = (
        db.query(
            WebAnalyticsPresence.path,
            WebAnalyticsPresence.visitor_id,
        )
        .filter(active_filter, _tracked_page_filter(WebAnalyticsPresence.path))
        .all()
    )

    active_visitors_by_path: dict[str, set[str]] = defaultdict(set)
    for raw_path, visitor_id in active_page_rows:
        path = _normalize_path(raw_path)
        if path not in POPULAR_PAGE_LABELS:
            continue
        active_visitors_by_path[path].add(visitor_id)

    active_pages = sorted(
        active_visitors_by_path,
        key=lambda path: (-len(active_visitors_by_path[path]), POPULAR_PAGE_ORDER[path]),
    )

    return {
        "active_users": active_users,
        "active_sessions": active_sessions,
        "active_pages": [
            {
                "path": path,
                "title": POPULAR_PAGE_LABELS[path],
                "active_users": len(active_visitors_by_path[path]),
            }
            for path in active_pages[:10]
        ],
        "active_window_seconds": ACTIVE_WINDOW_SECONDS,
        "last_updated_at": now,
    }


def get_web_traffic_overview(db: Session, period: str = "7d") -> dict:
    now = utc_now()
    window = _period_window(now, period)
    current_start = window["current_start"]
    current_end = window["current_end"]
    previous_start = window["previous_start"]
    previous_end = window["previous_end"]

    current_views = _count_page_views(db, current_start, current_end)
    previous_views = _count_page_views(db, previous_start, previous_end)
    current_visitors = _count_unique(db, WebAnalyticsEvent.visitor_id, current_start, current_end)
    previous_visitors = _count_unique(db, WebAnalyticsEvent.visitor_id, previous_start, previous_end)
    current_sessions = _count_unique(db, WebAnalyticsEvent.session_id, current_start, current_end)
    previous_sessions = _count_unique(db, WebAnalyticsEvent.session_id, previous_start, previous_end)
    current_bounce_rate = _bounce_rate(db, current_start, current_end)
    previous_bounce_rate = _bounce_rate(db, previous_start, previous_end)
    realtime = get_web_realtime_overview(db)

    return {
        "metrics": [
            _metric("page_views", "Lượt xem trang", current_views, previous_views, subtext=window["label"]),
            _metric("unique_visitors", "Khách truy cập", current_visitors, previous_visitors, subtext=window["label"]),
            _metric("sessions", "Phiên truy cập", current_sessions, previous_sessions, subtext=window["label"]),
            _metric(
                "active_users",
                "NgÆ°á»i dÃ¹ng Ä‘ang truy cáº­p",
                realtime["active_users"],
                realtime["active_users"],
                subtext=f"{ACTIVE_WINDOW_SECONDS} giÃ¢y gáº§n nháº¥t",
            ),
            _metric(
                "bounce_rate",
                "Tỷ lệ thoát",
                current_bounce_rate,
                previous_bounce_rate,
                suffix="%",
                subtext=window["label"],
                lower_is_better=True,
            ),
        ],
        "traffic": _traffic(db, now, window),
        "devices": _breakdown(db, WebAnalyticsEvent.device_type, current_start, current_end),
        "sources": _breakdown(db, WebAnalyticsEvent.source, current_start, current_end),
        "popular_pages": _popular_pages(db, current_start, current_end),
        "realtime": realtime,
        "last_updated_at": now,
    }
