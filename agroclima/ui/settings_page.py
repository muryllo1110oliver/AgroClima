from dataclasses import replace
from datetime import datetime
from PySide6.QtWidgets import (
    QFormLayout,
    QDoubleSpinBox,
    QSpinBox,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLineEdit,
)
from .common import Page, card, label, button


class SettingsPage(Page):
    def __init__(self, cfg, save, connect, disconnect, demo, ports, weather_refresh):
        super().__init__(
            "Configurações",
            "Conexão com o Arduino, localização da plantação e parâmetros do AgroClima.",
        )
        self.fields = {}

        c, v = card()
        v.addWidget(
            label("Localização da plantação · previsão meteorológica", "cardTitle")
        )
        form = QFormLayout()
        form.setVerticalSpacing(12)
        self.weather_city = QLineEdit(cfg.weather_city)
        self.weather_city.setPlaceholderText("Ex.: Santos")
        self.weather_state = QLineEdit(cfg.weather_state)
        self.weather_state.setPlaceholderText("Ex.: SP ou São Paulo")
        self.weather_country = QLineEdit(cfg.weather_country_code)
        self.weather_country.setMaxLength(2)
        self.weather_country.setPlaceholderText("BR")
        form.addRow("Cidade", self.weather_city)
        form.addRow("Estado / região", self.weather_state)
        form.addRow("País (código)", self.weather_country)
        update_minutes = QDoubleSpinBox()
        update_minutes.setRange(5, 360)
        update_minutes.setValue(cfg.weather_update_minutes)
        update_minutes.setSuffix(" min")
        self.fields["weather_update_minutes"] = update_minutes
        form.addRow("Atualização automática", update_minutes)
        v.addLayout(form)
        self.weather_auto = QCheckBox("Atualizar a previsão automaticamente")
        self.weather_auto.setChecked(cfg.weather_auto_update)
        v.addWidget(self.weather_auto)
        h = QHBoxLayout()
        h.addWidget(
            button(
                "Buscar cidade e atualizar previsão",
                lambda: weather_refresh(True),
                True,
            )
        )
        h.addStretch()
        v.addLayout(h)
        self.weather_status = label("Previsão ainda não carregada", "cardTitle")
        self.weather_detail = label(
            "Previsão Open-Meteo Best Match para a localização informada. Requer conexão com a internet.",
            "muted",
        )
        self.weather_status.setWordWrap(True)
        self.weather_detail.setWordWrap(True)
        v.addWidget(self.weather_status)
        v.addWidget(self.weather_detail)
        self.layout.addWidget(c)

        c, v = card()
        v.addWidget(label("Arduino · conexão serial", "cardTitle"))
        form = QFormLayout()
        form.setVerticalSpacing(12)
        self.port = QComboBox()
        self.port.setEditable(True)
        self.port.setMinimumWidth(220)
        if cfg.port:
            self.port.addItem(cfg.port)
            self.port.setCurrentText(cfg.port)
        form.addRow("Porta serial", self.port)
        baud = QSpinBox()
        baud.setRange(1200, 2000000)
        baud.setValue(cfg.baudrate)
        self.fields["baudrate"] = baud
        form.addRow("Velocidade serial (baud)", baud)
        v.addLayout(form)
        h = QHBoxLayout()
        h.addWidget(button("Atualizar portas", ports))
        h.addWidget(button("Conectar Arduino", connect, True))
        h.addWidget(button("Desconectar", disconnect))
        h.addWidget(button("Modo demonstração", demo))
        h.addStretch()
        v.addLayout(h)
        self.status = label("Desconectado", "cardTitle")
        self.detail = label("Aguardando comunicação", "muted")
        self.status.setWordWrap(True)
        self.detail.setWordWrap(True)
        v.addWidget(self.status)
        v.addWidget(self.detail)
        self.layout.addWidget(c)

        groups = [
            (
                "Condições ambientais",
                [
                    ("soil_min_pct", "Umidade mínima do solo (%)", 0, 100),
                    ("temp_critical_c", "Temperatura máxima (°C)", -40, 100),
                    ("light_critical_pct", "Luminosidade máxima (%)", 0, 100),
                    ("rain_block_mm", "Chuva prevista relevante (mm / 24h)", 0, 1000),
                ],
            ),
            (
                "Visualização",
                [
                    ("sample_interval_s", "Intervalo de demonstração (s)", 0.1, 60),
                    ("chart_interval_s", "Atualização de gráficos (s)", 0.5, 60),
                    ("chart_points", "Máximo de pontos por gráfico", 10, 100000),
                ],
            ),
        ]
        for title, specs in groups:
            c, v = card()
            v.addWidget(label(title, "cardTitle"))
            form = QFormLayout()
            form.setVerticalSpacing(12)
            for key, title, low, high in specs:
                spin = QSpinBox() if key == "chart_points" else QDoubleSpinBox()
                spin.setRange(low, high)
                spin.setValue(getattr(cfg, key))
                self.fields[key] = spin
                form.addRow(title, spin)
            v.addLayout(form)
            self.layout.addWidget(c)

        c, v = card()
        v.addWidget(label("Aplicativo", "cardTitle"))
        self.auto = QCheckBox("Reconectar automaticamente ao Arduino")
        self.auto.setChecked(cfg.auto_reconnect)
        v.addWidget(self.auto)
        self.theme = QComboBox()
        self.theme.addItems(["Claro"])
        self.units = QComboBox()
        self.units.addItems(["Métrico"])
        form = QFormLayout()
        form.addRow("Tema", self.theme)
        form.addRow("Unidades", self.units)
        v.addLayout(form)
        self.layout.addWidget(c)

        c, v = card()
        v.addWidget(label("Eventos recentes", "cardTitle"))
        self.events = label("Nenhum evento nesta sessão.", "body")
        self.events.setWordWrap(True)
        v.addWidget(self.events)
        self.layout.addWidget(c)

        note = label(
            "A porta e a velocidade serial precisam ser iguais às configuradas no Arduino. O firmware atual do AgroClima usa 115200 baud.",
            "muted",
        )
        note.setWordWrap(True)
        self.layout.addWidget(note)
        self.layout.addWidget(button("Salvar configurações", save, True))
        self.layout.addStretch()

    def weather_query(self):
        return (
            self.weather_city.text().strip(),
            self.weather_state.text().strip(),
            self.weather_country.text().strip().upper() or "BR",
        )

    def set_weather(self, forecast):
        prob = (
            f" · probabilidade máx. {forecast.precipitation_probability_max:.0f}%"
            if forecast.precipitation_probability_max is not None
            else ""
        )
        self.weather_status.setText(
            f"{forecast.location} · {forecast.precipitation_24h_mm:.1f} mm nas próximas 24 h{prob}"
        )
        temp = ""
        if (
            forecast.temperature_min_c is not None
            and forecast.temperature_max_c is not None
        ):
            temp = f" · temperatura {forecast.temperature_min_c:.1f}–{forecast.temperature_max_c:.1f} °C"
        humidity = (
            f"{forecast.humidity_avg_pct:.0f}%"
            if forecast.humidity_avg_pct is not None else "indisponível"
        )
        next_rain = "não prevista nas próximas 24 h"
        if forecast.next_rain_time:
            try:
                next_rain = datetime.fromisoformat(forecast.next_rain_time).strftime('%d/%m %H:%M')
            except (TypeError, ValueError):
                next_rain = "horário indisponível"
        self.weather_detail.setText(
            f"{forecast.provider}{temp} · umidade relativa média {humidity}\n"
            f"Próxima chuva: {next_rain} · horário local da plantação\n"
            f"Atualização: {forecast.updated_at.strftime('%d/%m/%Y %H:%M:%S')}"
        )

    def set_weather_error(self, message):
        self.weather_status.setText("Não foi possível atualizar a previsão")
        self.weather_detail.setText(message)

    def config(self, current):
        cfg = replace(
            current,
            **{k: w.value() for k, w in self.fields.items()},
            port=self.port.currentText().strip(),
            auto_reconnect=self.auto.isChecked(),
            weather_city=self.weather_city.text().strip(),
            weather_state=self.weather_state.text().strip(),
            weather_country_code=self.weather_country.text().strip().upper() or "BR",
            weather_auto_update=self.weather_auto.isChecked(),
        )
        cfg.validate()
        return cfg
