from datetime import datetime
from PySide6.QtWidgets import QHBoxLayout, QGridLayout
from .common import Page, label, card
from .sensor_card import SensorCard
from ..widgets.chart_card import ChartCard
from ..services.rain_assessment import (
    classify_probability,
    classify_volume,
    irrigation_recommendation,
)
from ..widgets.status_badge import StatusBadge


class Dashboard(Page):
    def __init__(self):
        hour = datetime.now().hour
        super().__init__(
            "Bom dia" if hour < 12 else "Boa tarde" if hour < 18 else "Boa noite",
            "Uma visão clara da sua cultura, em tempo real.",
        )
        self.weather = None
        self.mode = label("Aguardando conexão com o Arduino", "muted")
        self.layout.addWidget(self.mode)
        grid = QGridLayout()
        grid.setSpacing(12)
        self.cards = []
        for i, spec in enumerate(
            [
                ("UMIDADE DO SOLO", "%", "drop"),
                ("UMIDADE DO AR", "%", "drop"),
                ("TEMPERATURA", "°C", "temp"),
                ("LUMINOSIDADE", "%", "sun"),
                ("PREVISÃO DE CHUVA", "mm", "rain"),
            ]
        ):
            c = SensorCard(*spec)
            self.cards.append(c)
            grid.addWidget(c, 0, i)
        self.layout.addLayout(grid)
        rain_card = self.cards[4]
        rain_card.bar.hide()
        rain_card.limit.setText("Próximas 24 h · Aguardando previsão")
        rain_card.trend.setText("Probabilidade máx. horária: indisponível")
        rain_card.volume_badge = StatusBadge("Volume indisponível")
        rain_card.volume_badge.setWordWrap(True)
        rain_card.layout().addWidget(rain_card.volume_badge)
        rain_card.value.setToolTip(
            "Volume acumulado previsto nas próximas 24 horas, em mm."
        )
        rain_card.trend.setToolTip(
            "Maior probabilidade horária nas próximas 24 horas; não representa o volume acumulado nem a probabilidade de todo o período."
        )

        self.weather_line = label(
            "Localização meteorológica não configurada. Defina a cidade em Configurações.",
            "muted",
        )
        self.weather_line.setWordWrap(True)
        self.layout.addWidget(self.weather_line)

        self.chart = ChartCard(
            "Umidade do solo · últimas 24 horas", [(1, "Solo (%)", "#23835c")], 230
        )
        self.layout.addWidget(self.chart)

        h = QHBoxLayout()
        c, v = card()
        v.addWidget(label("Diagnóstico do sistema", "cardTitle"))
        self.diag = label("Aguardando leituras.", "body")
        self.diag.setWordWrap(True)
        v.addWidget(self.diag)
        self.recommend = label("", "recommend")
        self.recommend.setWordWrap(True)
        v.addWidget(self.recommend)
        h.addWidget(c, 3)

        c, v = card()
        v.addWidget(label("Resumo de hoje", "cardTitle"))
        self.summary = label("Sem dados nesta fonte.", "body")
        self.summary.setWordWrap(True)
        v.addWidget(self.summary)
        h.addWidget(c, 2)
        self.layout.addLayout(h)
        self.layout.addStretch()

    def update_weather(self, forecast, cfg):
        self.weather = forecast
        amount = forecast.precipitation_24h_mm
        _, status, tone = classify_probability(forecast.precipitation_probability_max)
        volume, volume_tone = classify_volume(amount)
        self.cards[4].update_reading(
            amount,
            status,
            tone,
            f"Próximas 24 h · {forecast.location}",
            None,
            50,
        )
        probability = (
            f"{forecast.precipitation_probability_max:.0f}%"
            if forecast.precipitation_probability_max is not None
            else "indisponível"
        )
        formatted_amount = f"{amount:.1f}".replace(".", ",")
        self.cards[4].trend.setText(
            f"Probabilidade máx. horária: {probability}\n"
            f"Volume acumulado previsto (24 h): {formatted_amount} mm"
        )
        self.cards[4].volume_badge.update_status(
            f"Volume {volume.lower()}", volume_tone
        )
        temp = ""
        if (
            forecast.temperature_min_c is not None
            and forecast.temperature_max_c is not None
        ):
            temp = f" · {forecast.temperature_min_c:.1f}–{forecast.temperature_max_c:.1f} °C"
        self.weather_line.setText(
            f"Meteorologia: {forecast.location} · {forecast.provider} · {amount:.1f} mm/24 h{temp} · atualizado às {forecast.updated_at.strftime('%H:%M')}"
        )

    def clear_weather(self, message):
        self.weather = None
        rain = self.cards[4]
        rain.value.setText("—")
        rain.badge.update_status("Previsão indisponível", "neutral")
        rain.limit.setText("Próximas 24 h · sem dados válidos")
        rain.trend.setText("Probabilidade máx. horária: indisponível")
        rain.volume_badge.update_status("Volume indisponível", "neutral")
        self.weather_line.setText(message)

    def clear_readings(self):
        for sensor in self.cards[:4]:
            sensor.value.setText("—")
            sensor.badge.update_status("Aguardando leitura", "neutral")
            sensor.trend.setText("Coletando tendência de 10 min")
            sensor.bar.setValue(0)
        self.chart.set_rows([])
        self.diag.setText("Aguardando leituras da nova conexão.")
        self.recommend.setText("")
        self.summary.setText("Aguardando dados desta fonte.")

    def update_data(self, r, cfg, rows, stats):
        older = next(
            (
                x
                for x in reversed(rows)
                if (r.timestamp - datetime.fromisoformat(x[0])).total_seconds() >= 600
            ),
            None,
        )
        specs = [
            (
                r.soil_moisture,
                r.soil_moisture < cfg.soil_min_pct,
                f"Mínimo {cfg.soil_min_pct:g}%",
                1,
            ),
            (r.air_humidity, False, "Escala 0–100%", 3),
            (
                r.air_temp,
                r.air_temp > cfg.temp_critical_c,
                f"Máximo {cfg.temp_critical_c:g} °C",
                2,
            ),
            (
                r.light_pct,
                r.light_pct > cfg.light_critical_pct,
                f"Máximo {cfg.light_critical_pct:g}%",
                4,
            ),
        ]
        for i, (value, alert, limit, col) in enumerate(specs):
            status = (
                "Abaixo do limite"
                if i == 0 and alert
                else "Limite excedido"
                if alert
                else "Monitorado"
                if i == 1
                else "Dentro do limite"
            )
            self.cards[i].update_reading(
                value,
                status,
                "warning" if alert else "ok",
                limit,
                value - older[col] if older else None,
                100,
            )

        messages = [
            "Atenção: solo abaixo do limite"
            if specs[0][1]
            else "Umidade do solo adequada",
            "Temperatura acima do limite"
            if specs[2][1]
            else "Temperatura dentro do limite",
            "Luminosidade acima do limite"
            if specs[3][1]
            else "Luminosidade próxima ao limite"
            if r.light_pct > cfg.light_critical_pct * 0.9
            else "Luminosidade dentro do limite",
        ]
        if self.weather:
            probability, _, _ = classify_probability(
                self.weather.precipitation_probability_max
            )
            volume, _ = classify_volume(self.weather.precipitation_24h_mm)
            soil = "Solo seco" if specs[0][1] else "Umidade do solo adequada"
            probability_text = (
                f"probabilidade horária {probability.lower()} de chuva"
                if self.weather.precipitation_probability_max is not None
                else "probabilidade de chuva indisponível"
            )
            messages[0] = (
                f"{soil}, com {probability_text} e volume {volume.lower()} previsto em 24 h."
            )
            messages.append(
                f"Chuva prevista: {self.weather.precipitation_24h_mm:.1f} mm nas próximas 24 h"
            )
        self.diag.setText("\n".join("•  " + m for m in messages))

        recommendation = irrigation_recommendation(r.soil_moisture, cfg, self.weather)
        self.recommend.setText("RECOMENDAÇÃO  /  " + recommendation)

        self.summary.setText(
            f"{stats['count']:,} leituras hoje\n\n"
            f"Solo atual: {r.soil_moisture:.1f}%   ·   Temperatura: {r.air_temp:.1f} °C\n\n"
            f"Umidade do ar: {r.air_humidity:.1f}%   ·   Luminosidade: {r.light_pct:.1f}%"
        )
