from pydantic import BaseModel
from typing import Optional


class ActivityItem(BaseModel):
    app_name: str
    window_title: Optional[str] = ""
    date: str
    duration_seconds: int
    last_seen: Optional[str] = ""


class LimitItem(BaseModel):
    app_name: str
    limit_minutes: int = 60
    enabled: bool = True


class SettingItem(BaseModel):
    key: str
    value: str


class StatusResponse(BaseModel):
    status: str = "ok"
    uptime_seconds: int = 0
    monitored_apps: int = 0
