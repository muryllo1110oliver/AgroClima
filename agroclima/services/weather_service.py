from __future__ import annotations

import logging
import math
import socket
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import certifi
import requests

logger = logging.getLogger(__name__)


class WeatherError(RuntimeError):
    """Mensagem segura para a interface, com causa técnica preservada."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def is_dns_error(error):
    pending, seen = [error], set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, socket.gaierror):
            return True
        pending.extend(
            item
            for item in (
                getattr(current, "__cause__", None),
                getattr(current, "__context__", None),
                getattr(current, "reason", None),
                *getattr(current, "args", ()),
            )
            if isinstance(item, BaseException)
        )
    return False


BRAZIL_STATES = dict(
    zip(
        [
            "AC",
            "AL",
            "AP",
            "AM",
            "BA",
            "CE",
            "DF",
            "ES",
            "GO",
            "MA",
            "MT",
            "MS",
            "MG",
            "PA",
            "PB",
            "PR",
            "PE",
            "PI",
            "RJ",
            "RN",
            "RS",
            "RO",
            "RR",
            "SC",
            "SP",
            "SE",
            "TO",
        ],
        [
            "Acre",
            "Alagoas",
            "Amapá",
            "Amazonas",
            "Bahia",
            "Ceará",
            "Distrito Federal",
            "Espírito Santo",
            "Goiás",
            "Maranhão",
            "Mato Grosso",
            "Mato Grosso do Sul",
            "Minas Gerais",
            "Pará",
            "Paraíba",
            "Paraná",
            "Pernambuco",
            "Piauí",
            "Rio de Janeiro",
            "Rio Grande do Norte",
            "Rio Grande do Sul",
            "Rondônia",
            "Roraima",
            "Santa Catarina",
            "São Paulo",
            "Sergipe",
            "Tocantins",
        ],
    )
)


def normalized(text):
    return "".join(
        c
        for c in unicodedata.normalize("NFD", str(text).strip().casefold())
        if not unicodedata.combining(c)
    )


def numeric_values(values, label, minimum=None, maximum=None, required=False):
    result = []
    for value in values:
        if value is None and not required:
            continue
        try:
            if value is None or isinstance(value, bool):
                raise ValueError()
            number = float(value)
            if (
                not math.isfinite(number)
                or (minimum is not None and number < minimum)
                or (maximum is not None and number > maximum)
            ):
                raise ValueError()
        except (TypeError, ValueError, OverflowError) as exc:
            raise RuntimeError(
                f"Previsão inválida: {label}. Tente atualizar novamente."
            ) from exc
        result.append(number)
    return result


@dataclass(frozen=True)
class WeatherForecast:
    location: str
    latitude: float
    longitude: float
    timezone: str
    precipitation_24h_mm: float
    precipitation_probability_max: float | None
    temperature_min_c: float | None
    temperature_max_c: float | None
    humidity_avg_pct: float | None
    next_rain_time: str | None
    updated_at: datetime
    provider: str = "Open-Meteo Best Match"


class WeatherService:
    GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, timeout: float = 12.0, session=None):
        self.timeout = timeout
        self.session = session if session is not None else requests.Session()
        # CA/proxy/netrc de outras instalações não podem mudar este transporte.
        self.session.trust_env = False
        self.session.headers.update({"User-Agent": "AgroClima-Monitor/2.0"})
        self.session.verify = certifi.where()

    def close(self):
        self.session.close()

    def _get_json(self, url: str, params: dict) -> dict:
        logger.info(
            "Consulta meteorológica: %s",
            "geocodificação" if url == self.GEOCODING_URL else "previsão",
        )
        try:
            if not Path(self.session.verify).is_file():
                raise FileNotFoundError("Bundle de certificados ausente")
            with self.session.get(
                url,
                params=params,
                timeout=(self.timeout, self.timeout),
                verify=self.session.verify,
            ) as response:
                response.raise_for_status()
                data = response.json()
        except requests.exceptions.SSLError as exc:
            logger.warning("Meteorologia: erro SSL")
            raise WeatherError(
                "ssl",
                "Falha na validação da conexão segura com o serviço meteorológico.",
            ) from exc
        except requests.exceptions.Timeout as exc:
            logger.warning("Meteorologia: timeout")
            raise WeatherError(
                "timeout",
                "O serviço meteorológico demorou para responder. Tente novamente.",
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            logger.warning(
                "Meteorologia: erro DNS"
                if is_dns_error(exc)
                else "Meteorologia: erro de conexão"
            )
            if is_dns_error(exc):
                raise WeatherError(
                    "dns",
                    "Não foi possível localizar o serviço meteorológico. Verifique sua conexão com a internet.",
                ) from exc
            raise WeatherError(
                "connection",
                "Não foi possível acessar o serviço meteorológico. Verifique sua conexão com a internet.",
            ) from exc
        except requests.exceptions.HTTPError as exc:
            logger.warning("Meteorologia: erro HTTP")
            status = exc.response.status_code if exc.response is not None else None
            message = (
                "O serviço meteorológico está temporariamente indisponível. Tente novamente."
                if status is not None and status >= 500
                else "O serviço meteorológico não pôde atender à consulta. Tente novamente mais tarde."
            )
            raise WeatherError("http", message) from exc
        except ValueError as exc:
            logger.warning("Meteorologia: JSON inválido")
            raise WeatherError(
                "json",
                "O serviço meteorológico enviou uma resposta inválida. Tente novamente.",
            ) from exc
        except requests.exceptions.RequestException as exc:
            logger.warning("Meteorologia: falha de rede")
            raise WeatherError(
                "request",
                "Não foi possível acessar o serviço meteorológico. Tente novamente.",
            ) from exc
        except OSError as exc:
            logger.exception("Falha local ao preparar a conexão meteorológica")
            raise WeatherError(
                "ssl_bundle",
                "Não foi possível carregar os certificados de conexão segura. Extraia novamente a pasta completa do aplicativo.",
            ) from exc
        if not isinstance(data, dict):
            raise RuntimeError("Resposta inválida do serviço meteorológico")
        if data.get("error"):
            raise WeatherError(
                "api",
                "O serviço meteorológico não pôde atender à consulta. Confira a localização e tente novamente.",
            )
        return data

    def geocode(self, city: str, state: str = "", country_code: str = "BR") -> dict:
        city = city.strip()
        state = state.strip()
        country_code = country_code.strip().upper()
        if not city:
            raise ValueError("Informe a cidade da plantação.")

        query = city + (f", {state}" if state else "")
        params = {
            "name": query,
            "count": 10,
            "language": "pt",
            "format": "json",
        }
        if country_code:
            params["countryCode"] = country_code

        data = self._get_json(self.GEOCODING_URL, params)
        results = data.get("results") or []
        if not results and state:
            params["name"] = city
            data = self._get_json(self.GEOCODING_URL, params)
            results = data.get("results") or []
        if not results:
            raise ValueError(f"Cidade não encontrada: {query}")

        if state:
            wanted = normalized(
                BRAZIL_STATES.get(state.upper(), state)
                if country_code == "BR"
                else state
            )
            preferred = [
                item for item in results if wanted == normalized(item.get("admin1", ""))
            ]
            if not preferred:
                raise ValueError(
                    f"Cidade não encontrada no estado/região informado: {query}"
                )
            results = preferred

        if country_code:
            results = [
                item
                for item in results
                if not item.get("country_code")
                or item["country_code"].upper() == country_code
            ]
        if not results:
            raise ValueError(f"Cidade não encontrada no país informado: {query}")

        return results[0]

    def fetch(
        self, city: str, state: str = "", country_code: str = "BR"
    ) -> WeatherForecast:
        place = self.geocode(city, state, country_code)
        lat = float(place["latitude"])
        lon = float(place["longitude"])
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,precipitation_probability",
            "forecast_hours": 48,
            "timezone": "auto",
            "temperature_unit": "celsius",
            "precipitation_unit": "mm",
            "models": "best_match",
        }
        data = self._get_json(self.FORECAST_URL, params)
        hourly = data.get("hourly") or {}
        times = hourly.get("time") or []
        precipitation = hourly.get("precipitation") or []
        probability = hourly.get("precipitation_probability") or []
        temperatures = hourly.get("temperature_2m") or []
        humidity = hourly.get("relative_humidity_2m") or []

        count = 24
        if len(times) < count or len(precipitation) < count:
            raise RuntimeError(
                "Previsão incompleta: não há 24 horas de precipitação disponíveis."
            )

        precip_values = numeric_values(
            precipitation[:count], "precipitação", minimum=0, required=True
        )
        probability_values = numeric_values(
            probability[:count], "probabilidade", 0, 100
        )
        temperature_values = numeric_values(temperatures[:count], "temperatura")
        humidity_values = numeric_values(humidity[:count], "umidade", 0, 100)

        next_rain_time = None
        for when, amount in zip(times[:count], precip_values):
            if amount >= 0.1:
                next_rain_time = when
                break

        location_parts = [place.get("name")]
        admin1 = place.get("admin1")
        country = place.get("country")
        if admin1 and admin1 != place.get("name"):
            location_parts.append(admin1)
        if country:
            location_parts.append(country)
        location = ", ".join(str(x) for x in location_parts if x)

        return WeatherForecast(
            location=location,
            latitude=lat,
            longitude=lon,
            timezone=str(data.get("timezone") or place.get("timezone") or "auto"),
            precipitation_24h_mm=round(sum(precip_values), 1),
            precipitation_probability_max=(
                round(max(probability_values), 0) if probability_values else None
            ),
            temperature_min_c=(
                round(min(temperature_values), 1) if temperature_values else None
            ),
            temperature_max_c=(
                round(max(temperature_values), 1) if temperature_values else None
            ),
            humidity_avg_pct=(
                round(sum(humidity_values) / len(humidity_values), 1)
                if humidity_values
                else None
            ),
            next_rain_time=next_rain_time,
            updated_at=datetime.now(),
        )
