import smtplib
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from core.database import Database
from core.logger import setup_logger

logger = setup_logger('core.reporter')

SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587


class EmailReporter:
    def __init__(self, db: Database):
        self.db = db
        logger.debug('EmailReporter создан')

    def _get_settings(self) -> dict:
        return {
            'smtp_server': self.db.get_setting('smtp_server', SMTP_SERVER),
            'smtp_port': int(self.db.get_setting('smtp_port', str(SMTP_PORT))),
            'email_from': self.db.get_setting('email_from', ''),
            'email_password': self.db.get_setting('email_password', ''),
            'email_to': self.db.get_setting('email_to', ''),
            'report_enabled': self.db.get_setting('report_enabled', '0'),
        }

    def is_configured(self) -> bool:
        s = self._get_settings()
        configured = bool(s['email_from'] and s['email_password'] and s['email_to'])
        logger.debug(f'Email настроен: {configured}')
        return configured

    def send_daily_report(self) -> bool:
        if not self.is_configured():
            logger.warning('Email не настроен, отчёт не отправлен')
            return False
        settings = self._get_settings()
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        conn = self.db._get_connection()
        try:
            rows = conn.execute(
                'SELECT a.app_name, d.total_seconds as duration_seconds '
                'FROM daily_activity d '
                'INNER JOIN apps a ON a.id = d.app_id '
                'WHERE d.date = ? AND d.total_seconds > 0 ORDER BY d.total_seconds DESC',
                (yesterday,)
            ).fetchall()
        finally:
            conn.close()
        if not rows:
            logger.info(f'Нет данных за {yesterday}, отчёт не отправлен')
            return False
        html_parts = [f'<h2>Отчет за {yesterday}</h2>', '<table border="1" cellpadding="5"><tr><th>Приложение</th><th>Время</th></tr>']
        for r in rows:
            d = dict(r)
            hours = d['duration_seconds'] // 3600
            minutes = (d['duration_seconds'] % 3600) // 60
            html_parts.append(f'<tr><td>{d["app_name"]}</td><td>{hours} ч {minutes} мин</td></tr>')
        html_parts.append('</table>')
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'Отчет активности за {yesterday}'
        msg['From'] = settings['email_from']
        msg['To'] = settings['email_to']
        msg.attach(MIMEText('\r\n'.join(html_parts), 'html', 'utf-8'))
        try:
            logger.info(f'Отправка отчёта на {settings["email_to"]}...')
            server = smtplib.SMTP(settings['smtp_server'], settings['smtp_port'])
            server.starttls()
            server.login(settings['email_from'], settings['email_password'])
            server.send_message(msg)
            server.quit()
            logger.info('Отчёт успешно отправлен')
            return True
        except Exception as e:
            logger.error(f'Ошибка отправки email: {e}')
            return False
