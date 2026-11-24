import queue
from dataclasses import replace
from datetime import datetime, timedelta
from collections import deque
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QStackedWidget,
)
from .config import AppConfig
from .paths import AppPaths
from .services.database_service import Database
from .services.serial_service import SerialService, DemoService, available_ports
from .services.storage_service import StorageService
from .services.weather_service import WeatherService
from .services.tasks import run_task
from .services.statistics_service import calculate_statistics
from .services.sampling import sample_rows
from .ui.sidebar import Sidebar
from .ui.header import Header
from .ui.dashboard import Dashboard
from .ui.charts_page import ChartsPage
from .ui.settings_page import SettingsPage
from .ui.common import label


class MainWindow(QMainWindow):
    def __init__(self, base_dir):
        super().__init__()
        self.paths = AppPaths.discover(base_dir)
        self.base_dir = self.paths.root
        self.cfg_path = self.paths.config
        self.cfg = AppConfig.load(self.cfg_path)
        self.db = Database(self.paths.database)
        self.setWindowTitle("AgroClima Monitor · Smart Agriculture Monitoring Platform")
        self.resize(1366, 768)
        self.setMinimumSize(1150, 680)

        self.incoming = queue.Queue()
        self.outgoing = queue.Queue()
        self.storage = StorageService(self.db, self.incoming, self.outgoing)
        self.storage.start()

        self.reader = None
        self.retiring = []
        self.session = 0
        self.state = "Desconectado"
        self.latest = None
        self.live = deque(maxlen=12000)
        self.log = deque(maxlen=7)
        self.jobs = set()
        self.closed = False
        self.chart_token = 0
        self.total = 0
        self.daily_stats = {"count": 0}
        self.history_rows = []
        self.weather = None
        self._weather_token = 0
        self._pending_weather = None
        self._display_source = "arduino"
        self._shutdown_complete = False
        self._storage_stopping = False
        self.weather_service = WeatherService()

        central = QWidget()
        self.setCentralWidget(central)
        shell = QHBoxLayout(central)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        self.sidebar = Sidebar(self.select_page)
        shell.addWidget(self.sidebar)

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)
        shell.addLayout(right, 1)

        self.header = Header()
        right.addWidget(self.header)

        self.notice = label("", "notice")
        self.notice.setWordWrap(True)
        self.notice.hide()
        right.addWidget(self.notice)

        self.stack = QStackedWidget()
        right.addWidget(self.stack, 1)

        self.dashboard = Dashboard()
        self.charts = ChartsPage(self.refresh_charts)
        self.settings = SettingsPage(
            self.cfg,
            self.save_config,
            self.connect_serial,
            self.disconnect,
            self.start_demo,
            self.refresh_ports,
            self.refresh_weather,
        )

        for page in [self.dashboard, self.charts, self.settings]:
            self.stack.addWidget(page)

        self.footer = label(
            "● Desconectado  |  Sem porta  |  Aguardando leituras", "footer"
        )
        right.addWidget(self.footer)

        self.poll = QTimer(self)
        self.poll.timeout.connect(self.poll_events)
        self.poll.start(100)

        self.refresh = QTimer(self)
        self.refresh.timeout.connect(self.refresh_views)
        self.refresh.start(round(self.cfg.chart_interval_s * 1000))

        self.notice_timer = QTimer(self)
        self.notice_timer.setSingleShot(True)
        self.notice_timer.timeout.connect(self.notice.hide)

        self.weather_timer = QTimer(self)
        self.weather_timer.timeout.connect(self.refresh_weather)
        self.configure_timers()

        self.refresh_ports()
        self.refresh_views()
        if self.cfg.weather_auto_update and self.cfg.weather_city:
            QTimer.singleShot(500, self.refresh_weather)

    def notify(self, message):
        if self.closed:
            return
        self.notice.setText(message)
        self.notice.show()
        self.notice_timer.start(9000)
        self.log.appendleft(datetime.now().strftime("%H:%M:%S") + "  " + message)
        self.settings.events.setText("\n\n".join(self.log))

    def job(self, key, fn, done, failed=None):
        if self.closed or key in self.jobs:
            return
        self.jobs.add(key)

        def success(result):
            self.jobs.discard(key)
            if not self.closed:
                try:
                    done(result)
                except Exception as exc:
                    if failed:
                        failed(str(exc))
                    self.notify(str(exc))

        def failure(error):
            self.jobs.discard(key)
            if not self.closed:
                if failed:
                    failed(error)
                self.notify(error)

        run_task(fn, success, failure)

    def select_page(self, index):
        if not 0 <= index < self.stack.count():
            return
        self.stack.setCurrentIndex(index)
        self.sidebar.group.button(index).setChecked(True)
        if index == 1:
            self.refresh_charts()

    def refresh_ports(self):
        def done(ports):
            current = self.settings.port.currentText() or self.cfg.port
            self.settings.port.clear()
            self.settings.port.addItems([p for p, _ in ports])
            self.settings.port.setCurrentText(current or (ports[0][0] if ports else ""))

        self.job("ports", available_ports, done)

    def refresh_weather(self, from_form=False):
        if self.closed or (not from_form and not self.cfg.weather_auto_update):
            return
        query = self.settings.weather_query() if from_form else self.weather_query()
        if not query[0]:
            if from_form:
                self.notify("Informe a cidade da plantação em Configurações.")
            return
        self._weather_token += 1
        request = (self._weather_token, query, from_form)
        if "weather" in self.jobs:
            self._pending_weather = request
            return
        self.request_weather(request)

    def weather_query(self):
        return (
            self.cfg.weather_city.strip(),
            self.cfg.weather_state.strip(),
            self.cfg.weather_country_code.strip().upper() or "BR",
        )

    def configure_timers(self):
        self.refresh.setInterval(round(self.cfg.chart_interval_s * 1000))
        self.weather_timer.setInterval(round(self.cfg.weather_update_minutes * 60000))
        if self.cfg.weather_auto_update and self.cfg.weather_city.strip():
            self.weather_timer.start()
        else:
            self.weather_timer.stop()

    def request_weather(self, request):
        token, query, from_form = request
        self.jobs.add("weather")

        def is_current():
            return (
                not self.closed
                and token == self._weather_token
                and (not from_form or self.settings.weather_query() == query)
            )

        def finish():
            self.jobs.discard("weather")
            pending = self._pending_weather
            self._pending_weather = None
            if pending and not self.closed and pending[0] == self._weather_token:
                self.request_weather(pending)

        def success(forecast):
            try:
                if not is_current():
                    return
                if from_form:
                    candidate = replace(
                        self.cfg,
                        weather_city=query[0],
                        weather_state=query[1],
                        weather_country_code=query[2],
                    )
                    candidate.save(self.cfg_path)
                    self.cfg = candidate
                    self.configure_timers()
                self.weather = forecast
                self.settings.set_weather(forecast)
                self.dashboard.update_weather(forecast, self.cfg)
                self.update_diagnosis()
                if from_form:
                    self.notify(
                        "Localização encontrada e previsão meteorológica atualizada."
                    )
            except Exception as exc:
                self.clear_weather(str(exc))
                self.notify("Meteorologia: " + str(exc))
            finally:
                finish()

        def failure(error):
            try:
                if is_current():
                    self.clear_weather(error)
                    self.notify("Meteorologia: " + error)
            finally:
                finish()

        run_task(lambda: self.weather_service.fetch(*query), success, failure)

    def update_diagnosis(self):
        if self.latest:
            self.dashboard.update_data(
                self.latest,
                self.cfg,
                self.history_rows or list(self.live),
                self.daily_stats,
            )

    def clear_weather(self, message):
        self.weather = None
        self.settings.set_weather_error(message)
        self.dashboard.clear_weather(message)
        self.update_diagnosis()

    def disconnect(self):
        if self.reader:
            self.reader.stop()
            self.retiring.append(self.reader)
            self.reader = None
        self.session += 1
        self.storage.session = self.session
        self.set_status("Desconectado")
        self.dashboard.mode.setText(
            "DESCONECTADO  /  Valores da última leitura; sem atualização ao vivo"
        )

    def start(self, kind):
        self.disconnect()
        self.latest = None
        self.live.clear()
        self.daily_stats = {"count": 0}
        self.history_rows = []
        self._display_source = "demo" if kind is DemoService else "arduino"
        self.dashboard.clear_readings()
        self.reader = kind(replace(self.cfg), self.incoming, self.session)
        self.reader.start()
        self.set_status("Demonstração" if kind is DemoService else "Reconectando")
        self.dashboard.mode.setText(
            "MODO DEMONSTRAÇÃO  /  Dados simulados"
            if kind is DemoService
            else "TELEMETRIA ARDUINO  /  Dados reais"
        )

    def connect_serial(self):
        port = self.settings.port.currentText().strip()
        if not port:
            self.notify("Selecione ou digite uma porta serial.")
            return
        if any(r.is_alive() and isinstance(r, SerialService) for r in self.retiring):
            self.notify(
                "Aguardando encerramento da conexão anterior. Tente novamente em um instante."
            )
            return
        try:
            candidate = self.settings.config(self.cfg)
            candidate.port = port
            self.apply_config(candidate)
        except (ValueError, OSError) as e:
            self.notify(str(e))
            return
        self.start(SerialService)

    def start_demo(self):
        try:
            self.apply_config(self.settings.config(self.cfg))
        except (ValueError, OSError) as e:
            self.notify(str(e))
            return
        self.start(DemoService)

    def set_status(self, state):
        changed = state != self.state
        self.state = state
        tone = {
            "Conectado": "ok",
            "Desconectado": "danger",
            "Reconectando": "warning",
            "Demonstração": "info",
        }[state]
        self.header.badge.update_status(state, tone)
        self.settings.status.setText(state)
        if changed and state in ("Desconectado", "Reconectando"):
            self.notify(
                "Arduino desconectado."
                if state == "Desconectado"
                else "Tentando estabelecer comunicação com o Arduino..."
            )

    def poll_events(self):
        if self.weather and datetime.now() - self.weather.updated_at > timedelta(
            minutes=max(60, self.cfg.weather_update_minutes * 2)
        ):
            self.clear_weather(
                "Previsão expirada. Atualize a meteorologia em Configurações."
            )
        for _ in range(200):
            try:
                session, kind, value = self.outgoing.get_nowait()
            except queue.Empty:
                break
            if session != self.session:
                continue
            if kind == "status":
                self.set_status(value)
            elif kind == "notice":
                self.notify(value)
            elif kind == "reading":
                old = self.latest
                self.latest = value
                r = value
                row = (
                    r.timestamp.isoformat(timespec="seconds"),
                    r.soil_moisture,
                    r.air_temp,
                    r.air_humidity,
                    r.light_pct,
                    r.rain_forecast_mm,
                    r.rain_sensor_pct,
                    int(r.pump),
                    int(r.shade),
                    r.source,
                )
                self.live.append(row)
                if old:
                    for active, before, msg in [
                        (
                            r.soil_moisture < self.cfg.soil_min_pct,
                            old.soil_moisture < self.cfg.soil_min_pct,
                            "Solo abaixo do limite configurado",
                        ),
                        (
                            r.air_temp > self.cfg.temp_critical_c,
                            old.air_temp > self.cfg.temp_critical_c,
                            "Temperatura elevada",
                        ),
                        (
                            r.light_pct > self.cfg.light_critical_pct,
                            old.light_pct > self.cfg.light_critical_pct,
                            "Luminosidade elevada",
                        ),
                    ]:
                        if active and not before:
                            self.notify(msg)
                self.dashboard.update_data(
                    r, self.cfg, self.history_rows or list(self.live), self.daily_stats
                )

        stamp = self.latest.timestamp.strftime("%H:%M:%S") if self.latest else "—"
        port = (
            "Simulador"
            if self.state == "Demonstração"
            else self.cfg.port or "Sem porta"
        )
        self.header.detail.setText(f"{port}  ·  Última leitura: {stamp}")
        age = (
            f"{(datetime.now() - self.latest.timestamp).total_seconds():.0f} s"
            if self.latest
            else "—"
        )
        self.settings.detail.setText(
            f"{port}  |  {self.cfg.baudrate} baud  |  Última comunicação: {age}"
        )
        self.footer.setText(
            f"● {self.state}   |   {port}   |   {self.cfg.baudrate} baud   |   Última leitura: {stamp}   |   {self.total:,} registros"
        )
        self.retiring = [r for r in self.retiring if r.is_alive()]

    def refresh_views(self):
        source = self._display_source
        session = self.session

        def fetch():
            now = datetime.now()
            rows, _ = self.db.query(
                start=(now - timedelta(hours=24)).isoformat(),
                end=now.isoformat(),
                source=source,
            )
            stats = {"count": self.db.count()}
            return rows, stats

        def done(result):
            if session != self.session:
                return
            rows, stats = result
            self.history_rows = rows
            self.total = stats["count"]
            self.dashboard.chart.set_rows(sample_rows(rows, self.cfg.chart_points))
            self.dashboard.chart.set_limit(self.cfg.soil_min_pct)
            if self.latest:
                today = [
                    r for r in rows if r[0][:10] == datetime.now().date().isoformat()
                ]
                self.daily_stats = {"count": len(today)}
                self.dashboard.update_data(
                    self.latest, self.cfg, rows, self.daily_stats
                )

        self.job("dashboard", fetch, done)
        if self.stack.currentIndex() == 1:
            self.refresh_charts()

    def refresh_charts(self, *args):
        if not hasattr(self, "charts"):
            return
        try:
            filters = self.charts.values()
        except ValueError as e:
            self.chart_token += 1
            self.charts.statistics.set_error()
            self.notify(str(e))
            return
        signature = (
            self.charts.period.currentIndex(),
            tuple(self.charts.filters.values(validate_dates=False).items()),
        )
        if signature != getattr(self, "_chart_signature", None):
            self.chart_token += 1
            self._chart_signature = signature
            self.charts.statistics.set_pending()
        token = self.chart_token
        period_name = self.charts.period.currentText()
        if "charts" in self.jobs:
            return

        def done(result):
            if token != self.chart_token:
                self.refresh_charts()
                return
            self.charts.set_rows(result[0], self.cfg)
            self.charts.statistics.set_statistics(result[2], filters, period_name)

        def fetch():
            rows, count = self.db.query(**filters)
            # Mesmo snapshot dos gráficos, integral e ainda sem amostragem.
            return rows, count, calculate_statistics(rows)

        def failed(_error):
            if token == self.chart_token:
                self.charts.statistics.set_error()
            else:
                self.refresh_charts()

        self.job("charts", fetch, done, failed)

    def apply_config(self, candidate):
        previous_query = self.weather_query()
        previous_auto = self.cfg.weather_auto_update
        candidate.save(self.cfg_path)
        self.cfg = candidate
        self.configure_timers()
        location_changed = previous_query != self.weather_query()
        if location_changed or previous_auto != candidate.weather_auto_update:
            self._weather_token += 1
            self._pending_weather = None
        if location_changed:
            self.clear_weather("Localização alterada. Aguardando uma nova previsão.")

    def save_config(self):
        try:
            self.apply_config(self.settings.config(self.cfg))
            self.notify(
                "Configurações salvas. Reconecte o Arduino ou reinicie a demonstração para aplicar os parâmetros de leitura."
            )
            self.refresh_views()
            if self.cfg.weather_auto_update and self.cfg.weather_city:
                self.refresh_weather()
        except (ValueError, OSError) as exc:
            self.notify(str(exc))

    def closeEvent(self, event):
        if self._shutdown_complete:
            event.accept()
            return
        event.ignore()
        if self.closed:
            return
        self.closed = True
        self._weather_token += 1
        self._pending_weather = None
        self.poll.stop()
        self.refresh.stop()
        self.weather_timer.stop()
        self.notice_timer.stop()
        self.setEnabled(False)
        self.footer.setText("Encerrando conexões e salvando as últimas leituras…")
        if self.reader:
            self.reader.stop()
            self.retiring.append(self.reader)
            self.reader = None
        self.shutdown_timer = QTimer(self)
        self.shutdown_timer.timeout.connect(self.finish_close)
        self.shutdown_timer.start(25)
        self.finish_close()

    def finish_close(self):
        if any(reader.is_alive() for reader in self.retiring):
            return
        if not self._storage_stopping:
            self._storage_stopping = True
            self.incoming.put(None)
        if self.storage.is_alive() or self.jobs:
            return
        self.shutdown_timer.stop()
        self.weather_service.close()
        self._shutdown_complete = True
        self.close()
