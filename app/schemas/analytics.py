from datetime import datetime

from pydantic import BaseModel, Field


class TrackPageViewRequest(BaseModel):
    visitor_id: str = Field(min_length=1, max_length=128)
    session_id: str = Field(min_length=1, max_length=128)
    path: str = Field(min_length=1, max_length=2048)
    title: str | None = Field(default=None, max_length=512)
    referrer: str | None = Field(default=None, max_length=2048)
    origin: str | None = Field(default=None, max_length=512)
    screen_width: int | None = Field(default=None, ge=0)
    screen_height: int | None = Field(default=None, ge=0)
    user_id: int | None = None


class TrackPageViewResponse(BaseModel):
    message: str
    event_id: int


class TrackHeartbeatRequest(BaseModel):
    visitor_id: str = Field(min_length=1, max_length=128)
    session_id: str = Field(min_length=1, max_length=128)
    path: str = Field(min_length=1, max_length=2048)
    title: str | None = Field(default=None, max_length=512)
    origin: str | None = Field(default=None, max_length=512)
    screen_width: int | None = Field(default=None, ge=0)
    screen_height: int | None = Field(default=None, ge=0)
    user_id: int | None = None


class TrackHeartbeatResponse(BaseModel):
    message: str
    event_id: int


class WebTrafficMetricSchema(BaseModel):
    key: str
    label: str
    value: float
    suffix: str = ""
    trend: str
    is_up: bool
    subtext: str = ""


class WebTrafficPointSchema(BaseModel):
    name: str
    current: int
    last: int


class WebTrafficBreakdownItemSchema(BaseModel):
    name: str
    value: int


class WebPopularPageSchema(BaseModel):
    path: str
    title: str | None = None
    views: int
    unique_visitors: int


class WebRealtimePageSchema(BaseModel):
    path: str
    title: str | None = None
    active_users: int


class AdminWebRealtimeResponse(BaseModel):
    active_users: int
    active_sessions: int
    active_pages: list[WebRealtimePageSchema]
    active_window_seconds: int
    last_updated_at: datetime


class AdminWebTrafficOverviewResponse(BaseModel):
    metrics: list[WebTrafficMetricSchema]
    traffic: list[WebTrafficPointSchema]
    devices: list[WebTrafficBreakdownItemSchema]
    sources: list[WebTrafficBreakdownItemSchema]
    popular_pages: list[WebPopularPageSchema]
    realtime: AdminWebRealtimeResponse
    last_updated_at: datetime
