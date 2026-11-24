from dataclasses import dataclass, asdict
import json
import math


@dataclass
class AppConfig:
    baudrate: int = 115200
    soil_min_pct: float = 30.0
    temp_critical_c: float = 32.0
    light_critical_pct: float = 75.0
    rain_block_mm: float = 8.0
    sample_interval_s: float = 1.0
    chart_points: int = 180
    port: str = ""
    auto_reconnect: bool = True
    pump_max_s: float = 120
    irrigation_interval_s: float = 300
    chart_interval_s: float = 2
    theme: str = "Claro"
    units: str = "Métrico"
    weather_city: str = ""
    weather_state: str = ""
    weather_country_code: str = "BR"
    weather_auto_update: bool = True
    weather_update_minutes: float = 30.0

    @classmethod
    def load(cls, path):
        if not path.exists():
            obj = cls()
            obj.save(path)
            return obj
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("config.json deve conter um objeto de configurações")
        obj = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        obj.validate()
        return obj

    def validate(self):
        for key in (
            "baudrate",
            "soil_min_pct",
            "temp_critical_c",
            "light_critical_pct",
            "rain_block_mm",
            "sample_interval_s",
            "chart_points",
            "pump_max_s",
            "irrigation_interval_s",
            "chart_interval_s",
            "weather_update_minutes",
        ):
            value = getattr(self, key)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise ValueError(key + " deve ser um número finito")
        for key in ("baudrate", "chart_points"):
            if not isinstance(getattr(self, key), int):
                raise ValueError(key + " deve ser inteiro")
        for key in ("auto_reconnect", "weather_auto_update"):
            if not isinstance(getattr(self, key), bool):
                raise ValueError(key + " deve ser verdadeiro ou falso")
        for key in (
            "port",
            "weather_city",
            "weather_state",
            "weather_country_code",
            "theme",
            "units",
        ):
            if not isinstance(getattr(self, key), str):
                raise ValueError(key + " deve ser texto")
        for key in ("chart_interval_s", "weather_update_minutes"):
            factor = 1000 if key == "chart_interval_s" else 60000
            if not 1 <= round(getattr(self, key) * factor) <= 2147483647:
                raise ValueError(key + " fora da faixa suportada pelo temporizador")
        for key in ("soil_min_pct", "light_critical_pct"):
            if not 0 <= getattr(self, key) <= 100:
                raise ValueError(key + " deve estar entre 0 e 100")
        if not -40 <= self.temp_critical_c <= 100:
            raise ValueError("Temperatura inválida")
        for key in (
            "baudrate",
            "sample_interval_s",
            "chart_points",
            "chart_interval_s",
            "pump_max_s",
            "irrigation_interval_s",
            "weather_update_minutes",
        ):
            if getattr(self, key) <= 0:
                raise ValueError(key + " deve ser positivo")
        if self.rain_block_mm < 0:
            raise ValueError("Chuva não pode ser negativa")
        if self.weather_country_code and (
            len(self.weather_country_code.strip()) != 2
            or not self.weather_country_code.strip().isascii()
            or not self.weather_country_code.strip().isalpha()
        ):
            raise ValueError("País deve usar código de 2 letras, por exemplo BR")

    def save(self, path):
        self.validate()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        tmp.replace(path)
