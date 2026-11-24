import threading, queue, time, math, random
import logging
from datetime import datetime
import serial
from serial.tools import list_ports
from ..protocol import Reading


def available_ports():
    return [(p.device, p.description) for p in list_ports.comports()]


class SerialService(threading.Thread):
    def __init__(self, cfg, events, session, factory=None, telemetry_timeout_s=10):
        super().__init__(daemon=True)
        self.cfg = cfg
        self.events = events
        self.session = session
        self.factory = factory or serial.Serial
        self.stopping = threading.Event()
        self.commands = queue.Queue()
        self.telemetry_timeout_s = telemetry_timeout_s

    def emit(self, kind, value):
        self.events.put((self.session, kind, value))

    def stop(self):
        self.stopping.set()

    def send_forecast(self, mm):
        value = float(mm)
        if not math.isfinite(value) or value < 0:
            raise ValueError("A previsão de chuva deve ser finita e não negativa")
        self.commands.put(value)

    def run(self):
        while not self.stopping.is_set():
            self.emit("status", "Reconectando")
            try:
                with self.factory(
                    self.cfg.port, self.cfg.baudrate, timeout=0.25, write_timeout=1
                ) as port:
                    logging.getLogger(__name__).info(
                        "Conexão Arduino aberta a %s baud", self.cfg.baudrate
                    )
                    last = time.monotonic()
                    while not self.stopping.is_set():
                        if time.monotonic() - last > self.telemetry_timeout_s:
                            raise TimeoutError(
                                "Sem telemetria válida no intervalo esperado"
                            )
                        while not self.commands.empty():
                            mm = self.commands.get_nowait()
                            port.write(f"CHUVA={mm:.1f}\n".encode())
                            self.emit(
                                "notice",
                                "Previsão enviada; aguardando confirmação na telemetria.",
                            )
                        raw = port.readline()
                        if raw:
                            line = raw.decode("utf-8", errors="replace").strip()
                            if not line.startswith("{"):
                                continue
                            try:
                                reading = Reading.from_json_line(line, "arduino")
                            except (ValueError, TypeError, OverflowError) as e:
                                self.emit("notice", "Linha ignorada: " + str(e))
                                continue
                            last = time.monotonic()
                            self.emit("status", "Conectado")
                            self.emit("reading", reading)
            except Exception as e:
                logging.getLogger(__name__).error("Erro serial: %s", type(e).__name__)
                if not self.stopping.is_set():
                    self.emit("notice", "Serial: " + str(e))
            if not self.cfg.auto_reconnect or self.stopping.is_set():
                break
            self.emit("status", "Reconectando")
            self.stopping.wait(2)
        self.emit("status", "Desconectado")
        logging.getLogger(__name__).info("Conexão Arduino encerrada")


class DemoService(threading.Thread):
    def __init__(self, cfg, events, session):
        super().__init__(daemon=True)
        self.cfg = cfg
        self.events = events
        self.session = session
        self.stopping = threading.Event()
        self.forecast = 0.0
        self.soil = 48.7
        self.pump = False
        self.last_stop = -10000.0
        self.started = 0.0

    def stop(self):
        self.stopping.set()

    def send_forecast(self, mm):
        value = float(mm)
        if not math.isfinite(value) or value < 0:
            raise ValueError("A previsão de chuva deve ser finita e não negativa")
        self.forecast = value

    def run(self):
        t0 = time.monotonic()
        self.events.put((self.session, "status", "Demonstração"))
        while not self.stopping.is_set():
            t = time.monotonic() - t0
            dt = self.cfg.sample_interval_s
            self.soil = max(
                10,
                min(
                    90,
                    self.soil
                    + (0.55 if self.pump else -0.10) * dt
                    + random.uniform(-0.05, 0.05),
                ),
            )
            allowed = self.forecast < self.cfg.rain_block_mm
            if self.pump and (
                self.soil >= self.cfg.soil_min_pct + 12
                or not allowed
                or t - self.started >= self.cfg.pump_max_s
            ):
                self.pump = False
                self.last_stop = t
            if (
                not self.pump
                and self.soil < self.cfg.soil_min_pct
                and allowed
                and t - self.last_stop >= self.cfg.irrigation_interval_s
            ):
                self.pump = True
                self.started = t
            temp = 28.3 + 5 * math.sin(t / 70)
            hum = 65.5 - 8 * math.sin(t / 70)
            light = 70.5 + 18 * math.sin(t / 60)
            r = Reading(
                datetime.now(),
                self.soil,
                temp,
                hum,
                light,
                self.forecast,
                0,
                self.pump,
                temp > self.cfg.temp_critical_c and light > self.cfg.light_critical_pct,
                "demo",
                "",
            )
            self.events.put((self.session, "reading", r))
            self.stopping.wait(dt)
