from __future__ import annotations
import json
import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class Reading:
    timestamp: datetime
    soil_moisture: float
    air_temp: float
    air_humidity: float
    light_pct: float
    rain_forecast_mm: float = 0.0
    rain_sensor_pct: float = 0.0
    pump: bool = False
    shade: bool = False
    source: str = "serial"
    raw: str = ""

    @staticmethod
    def _num(
        obj: dict[str, Any], names: tuple[str, ...], default: float = 0.0
    ) -> float:
        for name in names:
            if name in obj and obj[name] is not None:
                try:
                    value = float(obj[name])
                    if not math.isfinite(value):
                        raise ValueError("Valor numérico não finito")
                    return value
                except (TypeError, ValueError, OverflowError) as exc:
                    raise ValueError(f"Valor inválido para {name}") from exc
        return default

    @classmethod
    def from_json_line(cls, line: str, source: str = "serial") -> "Reading":
        obj = json.loads(line)
        if not isinstance(obj, dict):
            raise ValueError("A mensagem JSON deve ser um objeto")
        for names in [
            ("soil", "soil_moisture", "umidade_solo"),
            ("air_temp", "temp", "temperatura"),
            ("air_humidity", "humidity", "umidade_ar"),
            ("light", "light_pct", "luminosidade"),
        ]:
            if not any(obj.get(name) is not None for name in names):
                raise ValueError(f"Sensor ausente: {names[0]}")
        soil = cls._num(obj, ("soil", "soil_moisture", "umidade_solo"))
        temp = cls._num(obj, ("air_temp", "temp", "temperatura"))
        hum = cls._num(obj, ("air_humidity", "humidity", "umidade_ar"))
        light = cls._num(obj, ("light", "light_pct", "luminosidade"))
        forecast = cls._num(
            obj, ("rain_forecast", "rain_forecast_mm", "chuva_prevista")
        )
        rain_sensor = cls._num(obj, ("rain_sensor", "rain_sensor_pct", "chuva_sensor"))

        def state(value):
            if value in (False, 0, "0", "false", "False", "OFF", "off"):
                return False
            if value in (True, 1, "1", "true", "True", "ON", "on"):
                return True
            raise ValueError("Estado de atuador inválido")

        pump = state(obj.get("pump", obj.get("bomba", False)))
        shade = state(obj.get("shade", obj.get("sombra", False)))
        for label, value in (
            ("umidade do solo", soil),
            ("umidade do ar", hum),
            ("luminosidade", light),
        ):
            if not 0 <= value <= 100:
                raise ValueError(f"{label} fora da faixa 0–100: {value}")
        if not -40 <= temp <= 100:
            raise ValueError(f"temperatura fora da faixa esperada: {temp}")
        return cls(
            timestamp=datetime.now(),
            soil_moisture=soil,
            air_temp=temp,
            air_humidity=hum,
            light_pct=light,
            rain_forecast_mm=max(0.0, forecast),
            rain_sensor_pct=max(0.0, min(100.0, rain_sensor)),
            pump=pump,
            shade=shade,
            source=source,
            raw=line.strip(),
        )
