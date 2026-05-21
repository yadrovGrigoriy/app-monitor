import asyncio
import threading
import time
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI

from core.database import Database
from core.logger import setup_logger
from api.schemas import ActivityItem, LimitItem, SettingItem, StatusResponse

logger = setup_logger('api.server')


class AppMonitorAPI:
    """FastAPI-сервер для удалённого доступа к данным AppMonitor."""

    def __init__(self, db: Database, host: str = "0.0.0.0", port: int = 8765):
        self.db = db
        self.host = host
        self.port = port
        self._start_time: Optional[float] = None
        self._server: Optional[uvicorn.Server] = None
        self._thread: Optional[threading.Thread] = None

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            self._start_time = time.time()
            logger.info(f"API сервер запущен на {host}:{port}")
            yield
            logger.info("API сервер остановлен")

        self.app = FastAPI(title="AppMonitor API", version="1.0.0", lifespan=lifespan)
        self._register_routes()

    def _register_routes(self):
        app = self.app

        @app.get("/api/status", response_model=StatusResponse)
        async def get_status():
            today_activity = self.db.get_today_activity()
            return StatusResponse(
                status="ok",
                uptime_seconds=int(time.time() - (self._start_time or time.time())),
                monitored_apps=len(today_activity),
            )

        @app.get("/api/activity/today", response_model=list[ActivityItem])
        async def get_today_activity():
            return self.db.get_today_activity()

        @app.get("/api/activity/date/{date}", response_model=list[ActivityItem])
        async def get_activity_by_date(date: str):
            conn = self.db._get_connection()
            try:
                rows = conn.execute(
                    'SELECT * FROM activity WHERE date = ? ORDER BY duration_seconds DESC',
                    (date,)
                ).fetchall()
                return [dict(r) for r in rows]
            finally:
                conn.close()

        @app.get("/api/limits", response_model=list[LimitItem])
        async def get_limits():
            return self.db.get_all_limits()

        @app.post("/api/limits", response_model=LimitItem)
        async def set_limit(limit: LimitItem):
            self.db.set_limit(limit.app_name, limit.limit_minutes, limit.enabled)
            return limit

        @app.delete("/api/limits/{app_name}")
        async def delete_limit(app_name: str):
            self.db.delete_limit(app_name)
            return {"status": "deleted", "app_name": app_name}

        @app.get("/api/settings/{key}", response_model=SettingItem)
        async def get_setting(key: str, default: str = ""):
            value = self.db.get_setting(key, default)
            return SettingItem(key=key, value=value)

        @app.post("/api/settings", response_model=SettingItem)
        async def set_setting(setting: SettingItem):
            self.db.set_setting(setting.key, setting.value)
            return setting

        @app.get("/api/settings", response_model=list[SettingItem])
        async def get_all_settings():
            conn = self.db._get_connection()
            try:
                rows = conn.execute('SELECT * FROM settings').fetchall()
                return [dict(r) for r in rows]
            finally:
                conn.close()

    def start(self):
        """Запускает FastAPI-сервер в фоновом потоке."""
        if self._thread and self._thread.is_alive():
            logger.warning("API сервер уже запущен")
            return

        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="warning",
            access_log=False,
        )
        self._server = uvicorn.Server(config)

        def run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._server.serve())

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()
        logger.info(f"API сервер запущен: http://{self.host}:{self.port}")

    def stop(self):
        """Останавливает сервер."""
        if self._server:
            self._server.should_exit = True
            logger.info("API сервер остановлен")
