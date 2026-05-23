import asyncio
import datetime
import json
import threading
import time
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from core.database import Database
from core.auth import AuthManager
from core.logger import setup_logger
from api.schemas import (
    ActivityItem, LimitItem, SettingItem, StatusResponse,
    LoginRequest, LoginResponse, AppItem, TrackedRequest,
    PeriodRequest, StatsResponse,
)

logger = setup_logger('api.server')


class AppMonitorAPI:
    """FastAPI-сервер для удалённого доступа к данным AppMonitor."""

    def __init__(self, db: Database, host: str = "0.0.0.0", port: int = 8765):
        self.db = db
        self.auth = AuthManager(db)
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

        # CORS — разрешаем доступ с веб-клиентов
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

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
                    'SELECT a.app_name, a.system_id, d.total_seconds as duration_seconds '
                    'FROM daily_activity d '
                    'INNER JOIN apps a ON a.id = d.app_id '
                    'WHERE d.date = ? AND d.total_seconds > 0 '
                    'ORDER BY d.total_seconds DESC',
                    (date,)
                ).fetchall()
                return [dict(r) for r in rows]
            finally:
                conn.close()

        # ─── Аутентификация ────────────────────────────────────────
        @app.post("/api/auth/login", response_model=LoginResponse)
        async def login(req: LoginRequest):
            token = self.auth.login(req.username, req.password)
            if not token:
                from fastapi import HTTPException
                raise HTTPException(status_code=401, detail="Неверный логин или пароль")
            return LoginResponse(token=token, username=req.username)

        @app.post("/api/auth/register", response_model=LoginResponse)
        async def register(req: LoginRequest):
            ok = self.auth.register(req.username, req.password)
            if not ok:
                from fastapi import HTTPException
                raise HTTPException(status_code=409, detail="Администратор уже существует")
            token = self.auth.login(req.username, req.password)
            return LoginResponse(token=token, username=req.username)

        def _require_auth(authorization: str = "") -> str:
            """Проверить токен из заголовка Authorization. Вернуть username или бросить 401."""
            from fastapi import HTTPException
            if not authorization.startswith("Bearer "):
                raise HTTPException(status_code=401, detail="Требуется авторизация")
            token = authorization[7:]
            username = self.auth.validate_token(token)
            if not username:
                raise HTTPException(status_code=401, detail="Недействительный токен")
            return username

        @app.get("/api/limits", response_model=list[LimitItem])
        async def get_limits():
            return self.db.get_all_limits()

        @app.get("/api/limits/{name}", response_model=LimitItem)
        async def get_limit_by_name(name: str):
            limit = self.db.get_limit_by_system_id(name)
            if not limit:
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail=f"Limit for '{name}' not found")
            return limit

        @app.post("/api/limits", response_model=LimitItem)
        async def set_limit(limit: LimitItem, authorization: str = ""):
            _require_auth(authorization)
            self.db.set_limit(limit.system_id, limit.limit_minutes, limit.enabled, app_name=limit.app_name)
            return limit

        @app.delete("/api/limits/{system_id}")
        async def delete_limit(system_id: str, authorization: str = ""):
            _require_auth(authorization)
            self.db.delete_limit_by_system_id(system_id)
            return {"status": "deleted", "system_id": system_id}

        @app.get("/api/settings/{key}", response_model=SettingItem)
        async def get_setting(key: str, default: str = ""):
            value = self.db.get_setting(key, default)
            return SettingItem(key=key, value=value)

        @app.post("/api/settings", response_model=SettingItem)
        async def set_setting(setting: SettingItem, authorization: str = ""):
            _require_auth(authorization)
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

        # ─── Приложения ────────────────────────────────────────────
        @app.get("/api/apps", response_model=list[AppItem])
        async def get_all_apps():
            return self.db.get_all_apps()

        @app.get("/api/apps/tracked", response_model=list[AppItem])
        async def get_tracked_apps():
            return self.db.get_tracked_apps()

        @app.post("/api/apps/tracked", response_model=dict)
        async def set_tracked(req: TrackedRequest, authorization: str = ""):
            _require_auth(authorization)
            if req.tracked:
                self.db.mark_as_tracked(req.system_id)
            else:
                self.db.mark_as_untracked(req.system_id)
            return {"status": "ok", "system_id": req.system_id, "tracked": req.tracked}

        # ─── Статистика за период ──────────────────────────────────
        @app.post("/api/activity/period", response_model=StatsResponse)
        async def get_activity_period(req: PeriodRequest):
            apps = self.db.get_activity_for_period(req.start_date, req.end_date)
            total = sum(a.get("duration_seconds", 0) for a in apps)
            return StatsResponse(total_seconds=total, apps=apps)

        @app.post("/api/activity/tracked/period", response_model=StatsResponse)
        async def get_tracked_activity_period(req: PeriodRequest):
            apps = self.db.get_tracked_activity_for_period(req.start_date, req.end_date)
            total = sum(a.get("duration_seconds", 0) for a in apps)
            return StatsResponse(total_seconds=total, apps=apps)

        @app.get("/api/activity/app/{system_id}")
        async def get_app_activity(system_id: str, start_date: str = "", end_date: str = ""):
            if not start_date:
                start_date = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
            if not end_date:
                end_date = datetime.date.today().isoformat()
            return self.db.get_daily_activity_for_app_by_system_id(system_id, start_date, end_date)

        # ─── Исключения ────────────────────────────────────────────
        @app.get("/api/excluded", response_model=list[AppItem])
        async def get_excluded_apps():
            return self.db.get_excluded_apps()

        @app.post("/api/excluded", response_model=dict)
        async def add_excluded(req: TrackedRequest, authorization: str = ""):
            _require_auth(authorization)
            self.db.add_excluded_app(req.system_id)
            return {"status": "ok", "system_id": req.system_id}

        @app.delete("/api/excluded/{system_id}")
        async def remove_excluded(system_id: str, authorization: str = ""):
            _require_auth(authorization)
            self.db.remove_excluded_app(system_id)
            return {"status": "deleted", "system_id": system_id}

        # ─── WebSocket для real-time обновлений ─────────────────────
        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            logger.info("WebSocket клиент подключён")
            try:
                while True:
                    # Ждём команду от клиента
                    data = await websocket.receive_text()
                    msg = json.loads(data)
                    action = msg.get("action", "")

                    if action == "get_today":
                        activity = self.db.get_today_activity()
                        await websocket.send_json({
                            "type": "activity",
                            "date": datetime.date.today().isoformat(),
                            "data": activity,
                        })
                    elif action == "get_date":
                        date = msg.get("date", datetime.date.today().isoformat())
                        conn = self.db._get_connection()
                        try:
                            rows = conn.execute(
                                'SELECT a.app_name, a.system_id, d.total_seconds as duration_seconds '
                                'FROM daily_activity d '
                                'INNER JOIN apps a ON a.id = d.app_id '
                                'WHERE d.date = ? AND d.total_seconds > 0 '
                                'ORDER BY d.total_seconds DESC',
                                (date,)
                            ).fetchall()
                            await websocket.send_json({
                                "type": "activity",
                                "date": date,
                                "data": [dict(r) for r in rows],
                            })
                        finally:
                            conn.close()
                    elif action == "get_limits":
                        limits = self.db.get_all_limits()
                        await websocket.send_json({
                            "type": "limits",
                            "data": limits,
                        })
                    elif action == "ping":
                        await websocket.send_json({"type": "pong"})
            except WebSocketDisconnect:
                logger.info("WebSocket клиент отключён")
            except Exception as e:
                logger.error(f"WebSocket ошибка: {e}")

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
