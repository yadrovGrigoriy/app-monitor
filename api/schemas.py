from pydantic import BaseModel
from typing import Optional


class ActivityItem(BaseModel):
    app_name: str
    system_id: str = ""
    duration_seconds: int = 0


class LimitItem(BaseModel):
    app_name: str = ""
    system_id: str = ""
    limit_minutes: int = 60
    enabled: bool = True


class SettingItem(BaseModel):
    key: str
    value: str


class StatusResponse(BaseModel):
    status: str = "ok"
    uptime_seconds: int = 0
    monitored_apps: int = 0


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str


class AppItem(BaseModel):
    id: int = 0
    app_name: str = ""
    system_id: str = ""
    is_tracked: bool = False


class TrackedRequest(BaseModel):
    system_id: str
    tracked: bool = True


class PeriodRequest(BaseModel):
    start_date: str
    end_date: str


class StatsResponse(BaseModel):
    total_seconds: int = 0
    apps: list[ActivityItem] = []
