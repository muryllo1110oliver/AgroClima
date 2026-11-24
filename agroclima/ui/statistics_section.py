from datetime import datetime, timedelta
from PySide6.QtWidgets import QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel
from .common import label, icon
from ..widgets.status_badge import StatusBadge
from ..services.statistics_service import interpret_variability


def format_count(count):
    return f"{count:,}".replace(",", ".")


class StatisticsCard(QFrame):
    def __init__(self, title, unit, symbol, temperature=False):
        super().__init__()
        self.unit = unit
        self.temperature = temperature
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)
        header = QHBoxLayout()
        image = QLabel()
        image.setPixmap(icon(symbol).pixmap(20, 20))
        header.addWidget(image)
        title_label = label(title, "eyebrow")
        title_label.setWordWrap(True)
        header.addWidget(title_label, 1)
        layout.addLayout(header)
        self.value = label("—", "statisticsValue")
        layout.addWidget(self.value)
        self.badge = StatusBadge("Dados insuficientes")
        self.badge.setWordWrap(True)
        layout.addWidget(self.badge)
        self.count = label("0 leituras válidas", "tiny")
        layout.addWidget(self.count)

    def set_statistics(self, result):
        deviation = result.standard_deviation
        if deviation is None:
            self.value.setText("Dados insuficientes")
            self.value.setObjectName("statisticsEmpty")
        else:
            value = f"{deviation:.1f}".replace(".", ",")
            self.value.setText(f"σ {value} {self.unit}")
            self.value.setObjectName("statisticsValue")
        self.value.style().unpolish(self.value)
        self.value.style().polish(self.value)
        text, tone = interpret_variability(deviation, self.temperature)
        self.badge.update_status(text, tone)
        self.count.setText(f"{format_count(result.count)} leituras válidas")
        self.value.setToolTip(
            "Desvio padrão populacional: raiz da soma dos desvios quadráticos dividida por N."
            + (
                f" Valor sem arredondamento: {deviation!r} {self.unit}."
                if deviation is not None
                else " Requer pelo menos 2 valores válidos."
            )
        )


class StatisticsSection(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(label("Análise Estatística — Desvio Padrão", "cardTitle"))
        layout.addWidget(
            label("Desvio padrão das leituras no período selecionado", "muted")
        )
        self.base = label("Aguardando análise do período selecionado.", "tiny")
        self.base.setWordWrap(True)
        layout.addWidget(self.base)
        row = QHBoxLayout()
        row.setSpacing(12)
        self.cards = {}
        for key, title, unit, symbol in (
            ("soil_moisture", "UMIDADE DO SOLO", "%", "drop"),
            ("air_humidity", "UMIDADE DO AR", "%", "drop"),
            ("air_temp", "TEMPERATURA DO AR", "°C", "temp"),
            ("light_pct", "LUMINOSIDADE", "%", "sun"),
        ):
            card = StatisticsCard(title, unit, symbol, key == "air_temp")
            self.cards[key] = card
            row.addWidget(card, 1)
        layout.addLayout(row)
        self.result = None

    def set_pending(self):
        self.base.setText("Calculando estatísticas do período selecionado…")
        self.result = None
        for card in self.cards.values():
            card.value.setText("—")
            card.badge.update_status("Calculando…", "neutral")
            card.count.setText("Aguardando consulta")

    def set_error(self):
        self.set_pending()
        self.base.setText(
            "Não foi possível analisar o período. Atualize ou verifique os filtros."
        )
        for card in self.cards.values():
            card.badge.update_status("Análise indisponível", "neutral")

    def set_statistics(self, result, filters, period_name):
        self.result = result
        start = datetime.fromisoformat(filters["start"])
        end = datetime.fromisoformat(filters["end"])
        if period_name == "Personalizado":
            # O filtro final é exclusivo e inclui todo o último dia selecionado.
            period = f"entre {start:%d/%m/%Y} e {end - timedelta(days=1):%d/%m/%Y}"
        elif period_name in ("1 hora", "6 horas", "24 horas", "7 dias", "30 dias"):
            prefix = (
                "da última"
                if period_name == "1 hora"
                else "das últimas"
                if "horas" in period_name
                else "dos últimos"
            )
            period = f"{prefix} {period_name}"
        else:
            period = f"entre {start:%d/%m/%Y %H:%M} e {end:%d/%m/%Y %H:%M}"
        source = {
            None: "Todas as fontes",
            "arduino": "Arduino",
            "demo": "Demonstração",
        }[filters["source"]]
        self.base.setText(
            f"Baseado em {format_count(result.reading_count)} leituras {period} · {source}"
        )
        self.base.setToolTip(
            f"SQLite: {filters['start']} ≤ horário < {filters['end']}. Cada card informa N válido da própria variável."
        )
        for key, card in self.cards.items():
            card.set_statistics(result.variables[key])
