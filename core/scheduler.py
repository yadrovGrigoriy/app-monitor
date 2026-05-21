import threading
import time
import schedule
from core.database import Database
from core.reporter import EmailReporter


class DailyScheduler:
    def __init__(self, db: Database):
        self.db = db
        self.reporter = EmailReporter(db)
        self._running = False
        self._thread = None

    def start(self):
        if self._running:
            return
        self._running = True
        schedule.every().day.at('00:05').do(self._daily_reset_and_report)
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _run_loop(self):
        while self._running:
            schedule.run_pending()
            time.sleep(30)

    def _daily_reset_and_report(self):
        if self.reporter.is_configured():
            self.reporter.send_daily_report()
        self.db.reset_today()
