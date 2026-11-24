"""Verificação HTTPS no próprio executável distribuído, sem Python externo."""

from dataclasses import asdict
import json
from pathlib import Path
import shutil
import sys

import certifi

from .weather_service import WeatherService


def run_weather_check(output):
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)).resolve()
    certificate = Path(certifi.where()).resolve()
    result = {
        "frozen": bool(getattr(sys, "frozen", False)),
        "executable": sys.executable,
        "certificate": str(certificate),
        "certificate_in_bundle": certificate.is_relative_to(root),
        "external_python_on_path": shutil.which("python"),
        "forecasts": [],
    }
    service = WeatherService()
    try:
        for city in ("Santos", "Pedro de Toledo", "São Paulo"):
            result["forecasts"].append(asdict(service.fetch(city, "São Paulo", "BR")))
        result["ok"] = True
    except Exception as exc:
        result.update(ok=False, error=str(exc))
    finally:
        service.close()
    Path(output).write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    return 0 if result["ok"] else 1
