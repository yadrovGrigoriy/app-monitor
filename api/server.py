import asyncio
import datetime
import json
import os
import sys
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Header, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from core.database import Database
from core.auth import AuthManager
from core.logger import setup_logger
from api.schemas import (
    ActivityItem, LimitItem, SettingItem, StatusResponse,
    LoginRequest, LoginResponse, AppItem, TrackedRequest,
    PeriodRequest, StatsResponse, UpdateCheckResponse,
)

# mDNS-объявление сервиса для автообнаружения в локальной сети
_MDNS_SERVICE_TYPE = "_appmonitor._tcp.local."
_MDNS_SERVICE_NAME = None  # будет задан при запуске
_mdns_thread: Optional[threading.Thread] = None
_mdns_server = None

logger = setup_logger('api.server')


class AppMonitorAPI:
    """FastAPI-сервер для удалённого доступа к данным AppMonitor."""

    def __init__(self, db: Database, host: str = "0.0.0.0", port: int = 8765,
                 ssl_certfile: Optional[str] = None, ssl_keyfile: Optional[str] = None):
        self.db = db
        self.auth = AuthManager(db)
        self.host = host
        self.port = port
        self.ssl_certfile = ssl_certfile
        self.ssl_keyfile = ssl_keyfile
        self._start_time: Optional[float] = None
        self._server: Optional[uvicorn.Server] = None
        self._thread: Optional[threading.Thread] = None
        self._message_counter: int = 0

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
        self._mount_web_ui()

    def _mount_web_ui(self):
        """Подключить веб-интерфейс администратора."""
        # Поиск папки web в нескольких местах:
        #   1. _MEIPASS/api/web  (PyInstaller --onedir)
        #   2. _MEIPASS/web      (PyInstaller --onefile, данные в корне)
        #   3. api/web/          (разработка, рядом с server.py)
        #   4. ../api/web/       (запуск из корня проекта)
        meipass = Path(getattr(sys, '_MEIPASS', ''))
        script_dir = Path(__file__).resolve().parent
        candidates = [
            meipass / "api" / "web",
            meipass / "web",
            script_dir / "web",
            script_dir.parent / "api" / "web",
        ]
        web_dir = None
        for c in candidates:
            if c.is_dir():
                web_dir = c
                break
        if web_dir is None:
            logger.warning(f"Папка веб-интерфейса не найдена. Искали: {candidates}")
            return

        # Раздаём статику (CSS, JS) — html=True для SPA-навигации
        self.app.mount("/web", StaticFiles(directory=str(web_dir), html=True), name="web")

        # SPA-редирект через middleware: все не-API пути отдаём index.html
        # Используем middleware вместо маршрута, чтобы не конфликтовать с mount
        @self.app.middleware("http")
        async def spa_redirect_middleware(request, call_next):
            path = request.url.path
            # Пропускаем API-запросы и статику
            if path.startswith("/api/") or path.startswith("/web/"):
                return await call_next(request)
            # Если файл существует — отдаём как есть
            full_path = web_dir / path.lstrip("/")
            if full_path.is_file():
                return await call_next(request)
            # Всё остальное — index.html для SPA
            index_path = web_dir / "index.html"
            if index_path.is_file():
                return FileResponse(str(index_path))
            return await call_next(request)

        logger.info(f"Веб-интерфейс подключён: {web_dir}")

    def _register_routes(self):
        app = self.app

        @app.get("/api/messages/pending")
        async def get_pending_messages():
            """Получить непрочитанные сообщения для клиента."""
            pending = self.db.get_pending_messages()
            return {"messages": pending, "count": len(pending)}

        @app.post("/api/message/send")
        async def send_message_to_client(data: dict):
            """Отправить сообщение клиенту AppMonitor."""
            text = data.get("text", "").strip()
            if not text:
                raise HTTPException(status_code=400, detail="Текст сообщения не может быть пустым")
            msg = self.db.add_message(text, "admin")
            logger.info(f"Сообщение #{msg['id']} отправлено клиенту: {msg['text'][:50]}...")
            return {"status": "ok", "message": msg}

        @app.post("/api/messages/{message_id}/read")
        async def mark_message_read(message_id: int):
            """Отметить сообщение как прочитанное."""
            self.db.mark_message_as_read(message_id)
            return {"status": "ok"}

        @app.get("/api/messages/history")
        async def get_message_history(limit: int = 100):
            """Получить историю сообщений."""
            history = self.db.get_message_history(limit)
            return {"messages": history, "count": len(history)}

        @app.post("/api/messages/reply")
        async def reply_from_client(data: dict):
            """Отправить ответ от клиента (пользователя)."""
            text = data.get("text", "").strip()
            if not text:
                raise HTTPException(status_code=400, detail="Текст сообщения не может быть пустым")
            msg = self.db.add_message(text, "user")
            logger.info(f"Ответ от пользователя #{msg['id']}: {msg['text'][:50]}...")
            return {"status": "ok", "message": msg}

        @app.get("/api/status", response_model=StatusResponse)
        async def get_status():
            from core.updater import APP_VERSION
            today_activity = self.db.get_today_activity()
            return StatusResponse(
                status="ok",
                version=APP_VERSION,
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

        @app.get("/api/activity/period")
        async def get_activity_for_period(start: str, end: str):
            """Активность за период (включая обе даты)."""
            conn = self.db._get_connection()
            try:
                rows = conn.execute(
                    'SELECT a.app_name, a.system_id, SUM(d.total_seconds) as duration_seconds '
                    'FROM daily_activity d '
                    'INNER JOIN apps a ON a.id = d.app_id '
                    'WHERE d.date >= ? AND d.date <= ? AND d.total_seconds > 0 '
                    'GROUP BY a.app_name, a.system_id '
                    'ORDER BY duration_seconds DESC',
                    (start, end)
                ).fetchall()
                apps_list = [dict(r) for r in rows]
                total = sum(a['duration_seconds'] for a in apps_list)
                return {'total_seconds': total, 'apps': apps_list}
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
        async def set_limit(limit: LimitItem, authorization: str = Header("")):
            _require_auth(authorization)
            self.db.set_limit(limit.system_id, limit.limit_minutes, limit.enabled, app_name=limit.app_name)
            return limit

        @app.delete("/api/limits/{system_id}")
        async def delete_limit(system_id: str, authorization: str = Header("")):
            _require_auth(authorization)
            self.db.delete_limit_by_system_id(system_id)
            return {"status": "deleted", "system_id": system_id}

        @app.get("/api/settings/{key}", response_model=SettingItem)
        async def get_setting(key: str, default: str = ""):
            value = self.db.get_setting(key, default)
            return SettingItem(key=key, value=value)

        @app.post("/api/settings", response_model=SettingItem)
        async def set_setting(setting: SettingItem, authorization: str = Header("")):
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
        async def set_tracked(req: TrackedRequest, authorization: str = Header("")):
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
        async def add_excluded(req: TrackedRequest, authorization: str = Header("")):
            _require_auth(authorization)
            self.db.add_excluded_app(req.system_id)
            return {"status": "ok", "system_id": req.system_id}

        @app.delete("/api/excluded/{system_id}")
        async def remove_excluded(system_id: str, authorization: str = Header("")):
            _require_auth(authorization)
            self.db.remove_excluded_app(system_id)
            return {"status": "deleted", "system_id": system_id}

        # ─── Администраторы ────────────────────────────────────────
        @app.get("/api/admins")
        async def get_admins(authorization: str = Header("")):
            _require_auth(authorization)
            return self.db.get_all_admins()

        @app.post("/api/admins")
        async def add_admin(req: dict, authorization: str = Header("")):
            _require_auth(authorization)
            username = req.get('username', '').strip()
            password = req.get('password', '')
            if not username or not password:
                raise HTTPException(status_code=400, detail='Логин и пароль обязательны')
            if self.db.get_admin(username):
                raise HTTPException(status_code=409, detail='Администратор уже существует')
            from core.auth import hash_password
            self.db.add_admin(username, hash_password(password))
            logger.info(f'Администратор добавлен через API: {username}')
            return {"status": "ok", "username": username}

        @app.delete("/api/admins/{username}")
        async def delete_admin(username: str, authorization: str = Header("")):
            _require_auth(authorization)
            admins = self.db.get_all_admins()
            if len(admins) <= 1:
                raise HTTPException(status_code=400, detail='Нельзя удалить последнего администратора')
            conn = self.db._get_connection()
            try:
                conn.execute('DELETE FROM admins WHERE username = ?', (username,))
                conn.commit()
                logger.info(f'Администратор удалён через API: {username}')
            finally:
                conn.close()
            return {"status": "deleted", "username": username}

        @app.post("/api/admins/sync")
        async def sync_admins(admins: list[dict], authorization: str = Header("")):
            _require_auth(authorization)
            self.db.sync_admins(admins)
            return {"status": "synced", "count": len(admins)}

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

        # ─── Обновления ────────────────────────────────────────────
        @app.get("/api/update/check", response_model=UpdateCheckResponse)
        async def check_update():
            """Проверить наличие обновления на сервере."""
            from core.updater import APP_VERSION, is_newer_version

            # Путь к установщику рядом с сервером
            installer_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dist")
            installer_pattern = f"AppMonitor_Setup_*.exe"
            import glob
            installers = sorted(glob.glob(os.path.join(installer_dir, installer_pattern)))

            latest_version = APP_VERSION
            download_url = ""
            file_size = 0

            if installers:
                # Берём последний установщик, извлекаем версию из имени
                latest_installer = installers[-1]
                file_size = os.path.getsize(latest_installer)
                fname = os.path.basename(latest_installer)
                # AppMonitor_Setup_1.1.0.exe -> 1.1.0
                version_part = fname.replace("AppMonitor_Setup_", "").replace(".exe", "")
                if version_part:
                    latest_version = version_part
                download_url = f"/api/update/download/{latest_version}"

            has_update = is_newer_version(APP_VERSION, latest_version)

            return UpdateCheckResponse(
                latest_version=latest_version,
                current_version=APP_VERSION,
                has_update=has_update,
                download_url=download_url,
                release_notes=f"Доступна версия {latest_version}",
                file_size=file_size,
            )

        @app.get("/api/update/download/{version}")
        async def download_update(version: str):
            """Скачать установщик указанной версии."""
            from fastapi.responses import FileResponse
            from fastapi import HTTPException

            installer_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dist")
            installer_path = os.path.join(installer_dir, f"AppMonitor_Setup_{version}.exe")

            if not os.path.isfile(installer_path):
                raise HTTPException(status_code=404, detail=f"Установщик версии {version} не найден")

            return FileResponse(
                path=installer_path,
                filename=f"AppMonitor_Setup_{version}.exe",
                media_type="application/x-msdownload",
            )

        # ─── История обновлений ────────────────────────────────────
        @app.get("/api/update/history")
        async def get_update_history(limit: int = 50):
            """Получить историю обновлений."""
            records = self.db.get_update_history(limit)
            return {
                "records": records,
                "count": len(records),
                "last_update": records[0] if records else None,
            }

        @app.post("/api/update/history")
        async def add_update_record(req: dict, authorization: str = Header("")):
            """Добавить запись об обновлении."""
            _require_auth(authorization)
            old_version = req.get("old_version", "")
            new_version = req.get("new_version", "")
            if not old_version or not new_version:
                raise HTTPException(status_code=400, detail="old_version и new_version обязательны")
            self.db.add_update_record(old_version, new_version)
            last = self.db.get_last_update()
            return last or {"status": "ok"}

        # ─── Загрузка обновления ────────────────────────────────────
        @app.post("/api/update/upload")
        async def upload_update(file: UploadFile = File(...), authorization: str = Header("")):
            """Загрузить установщик обновления на сервер."""
            _require_auth(authorization)

            if not file.filename or not file.filename.endswith(".exe"):
                raise HTTPException(status_code=400, detail="Требуется .exe файл")

            # Сохраняем рядом с исполняемым файлом (туда же смотрит apply_local_update)
            installer_dir = os.path.dirname(sys.executable)
            os.makedirs(installer_dir, exist_ok=True)

            # Извлекаем версию из имени файла: AppMonitor_Setup_X.X.X.exe
            fname = file.filename
            version_part = fname.replace("AppMonitor_Setup_", "").replace(".exe", "")
            dest_path = os.path.join(installer_dir, fname)

            # Сохраняем файл чанками
            file_size = 0
            with open(dest_path, "wb") as f:
                while True:
                    chunk = await file.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
                    file_size += len(chunk)

            logger.info(f"Установщик загружен: {dest_path} ({file_size / 1024 / 1024:.1f} МБ)")

            return {
                "status": "ok",
                "filename": fname,
                "version": version_part if version_part != fname else "",
                "file_size": file_size,
            }

        # ─── Очистка данных ────────────────────────────────────────
        @app.post("/api/data/clear")
        async def clear_data(authorization: str = Header("")):
            _require_auth(authorization)
            self.db.clear_data()
            return {"status": "ok", "message": "Все данные очищены"}

        # ─── Логи приложения ────────────────────────────────────────
        @app.get("/api/logs")
        async def list_logs():
            """Список доступных лог-файлов."""
            log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
            if not os.path.isdir(log_dir):
                return {"logs": [], "count": 0}
            files = []
            for f in sorted(os.listdir(log_dir), reverse=True):
                fpath = os.path.join(log_dir, f)
                if os.path.isfile(fpath):
                    files.append({
                        "filename": f,
                        "size_bytes": os.path.getsize(fpath),
                        "modified": datetime.datetime.fromtimestamp(os.path.getmtime(fpath)).isoformat(),
                    })
            return {"logs": files, "count": len(files), "log_dir": log_dir}

        @app.get("/api/logs/{filename}")
        async def read_log(filename: str, tail: int = 0):
            """Прочитать содержимое лог-файла."""
            safe_name = os.path.basename(filename)
            log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
            fpath = os.path.join(log_dir, safe_name)
            if not os.path.isfile(fpath):
                raise HTTPException(status_code=404, detail=f"Лог-файл '{safe_name}' не найден")
            try:
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                total = len(lines)
                if tail > 0:
                    lines = lines[-tail:]
                return {
                    "filename": safe_name,
                    "path": fpath,
                    "total_lines": total,
                    "returned_lines": len(lines),
                    "content": "".join(lines),
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Ошибка чтения лог-файла: {e}")

    def start(self):
        """Запускает FastAPI-сервер в фоновом потоке."""
        if self._thread and self._thread.is_alive():
            logger.warning("API сервер уже запущен")
            return

        ssl_kwargs = {}
        if self.ssl_certfile and self.ssl_keyfile:
            ssl_kwargs["ssl_certfile"] = self.ssl_certfile
            ssl_kwargs["ssl_keyfile"] = self.ssl_keyfile

        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="warning",
            access_log=False,
            log_config=None,
            **ssl_kwargs,
        )
        self._server = uvicorn.Server(config)

        def run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._server.serve())

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()
        logger.info(f"API сервер запущен: http://{self.host}:{self.port}")

        # Регистрируем mDNS-сервис для автообнаружения
        _start_mdns_service(self.port)

    def stop(self):
        """Останавливает сервер."""
        _stop_mdns_service()
        if self._server:
            self._server.should_exit = True
            # Подавляем ошибки asyncio при принудительном закрытии сокетов
            import logging
            logging.getLogger('asyncio').setLevel(logging.CRITICAL)
            logger.info("API сервер остановлен")


# ─── mDNS-объявление сервиса ────────────────────────────────────────


def _start_mdns_service(port: int):
    """Запустить mDNS-сервис для автообнаружения в локальной сети."""
    global _mdns_thread, _mdns_server, _MDNS_SERVICE_NAME
    try:
        from zeroconf import Zeroconf, ServiceInfo
        import socket

        hostname = socket.gethostname()
        _MDNS_SERVICE_NAME = f"AppMonitor-{hostname}.{_MDNS_SERVICE_TYPE}"

        local_ip = _get_local_ip()
        if not local_ip:
            logger.warning("Не удалось определить локальный IP, mDNS не запущен")
            return

        info = ServiceInfo(
            type_=_MDNS_SERVICE_TYPE,
            name=_MDNS_SERVICE_NAME,
            addresses=[socket.inet_aton(local_ip)],
            port=port,
            properties={"hostname": hostname, "version": "1.0"},
        )

        zeroconf = Zeroconf()
        zeroconf.register_service(info)
        _mdns_server = zeroconf
        logger.info(f"mDNS сервис зарегистрирован: {_MDNS_SERVICE_NAME} -> {local_ip}:{port}")
    except ImportError:
        logger.debug("zeroconf не установлен, mDNS недоступен")
    except Exception as e:
        logger.warning(f"Ошибка регистрации mDNS: {e}")


def _stop_mdns_service():
    """Остановить mDNS-сервис."""
    global _mdns_server
    if _mdns_server:
        try:
            _mdns_server.unregister_all_services()
            _mdns_server.close()
        except Exception as e:
            logger.warning(f"Ошибка остановки mDNS: {e}")
        _mdns_server = None


def _get_local_ip() -> Optional[str]:
    """Получить локальный IP-адрес (не 127.0.0.1)."""
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None
