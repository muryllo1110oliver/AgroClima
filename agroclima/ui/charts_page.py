from datetime import datetime, timedelta
from PySide6.QtWidgets import QHBoxLayout, QComboBox, QCheckBox
from .common import Page, button, label
from .filters import Filters
from ..widgets.chart_card import ChartCard
from .statistics_section import StatisticsSection
from ..services.sampling import sample_rows


class ChartsPage(Page):
    def __init__(self, refresh):
        super().__init__(
            "Gráficos",
            "Explore as tendências dos sensores ambientais ao longo do tempo.",
        )
        self.period = QComboBox()
        self.period.addItems(
            [
                "1 hora",
                "6 horas",
                "24 horas",
                "7 dias",
                "30 dias",
                "Personalizado",
                "Hoje",
                "Semana",
                "Mês",
            ]
        )
        self.period.setCurrentIndex(2)
        h = QHBoxLayout()
        h.addWidget(label("Período", "muted"))
        h.addWidget(self.period)
        h.addStretch()
        h.addWidget(button("Atualizar", refresh))
        self.layout.addLayout(h)
        self.filters = Filters()
        self.layout.addWidget(self.filters)
        self.info = label("", "muted")
        self.layout.addWidget(self.info)
        series = [
            (1, "Solo (%)", "#23835c"),
            (2, "Temperatura (°C)", "#da9852"),
            (3, "Umidade do ar (%)", "#559dd0"),
            (4, "Luminosidade (%)", "#9b85c0"),
        ]
        self.combined = ChartCard(
            "Condições ambientais · escala numérica compartilhada", series, 290
        )
        self.layout.addWidget(self.combined)
        h = QHBoxLayout()
        for key, name, color in series:
            check = QCheckBox(name)
            check.setChecked(True)
            check.toggled.connect(self.combined.curves[key].setVisible)
            h.addWidget(check)
        self.layout.addLayout(h)
        self.charts = []
        for key, name, color in series:
            chart = ChartCard(name, [(key, name, color)], 250)
            self.layout.addWidget(chart)
            self.charts.append(chart)
        self.statistics = StatisticsSection()
        self.layout.addWidget(self.statistics)
        self.period.currentIndexChanged.connect(refresh)
        self.filters.source.currentIndexChanged.connect(refresh)
        for field in (self.filters.start, self.filters.end):
            field.dateChanged.connect(
                lambda _date: (
                    refresh() if self.period.currentText() == "Personalizado" else None
                )
            )

    def values(self):
        index = self.period.currentIndex()
        filters = self.filters.values(validate_dates=index == 5)
        now = datetime.now()
        if index < 5:
            filters.update(
                start=(now - timedelta(hours=[1, 6, 24, 168, 720][index])).isoformat(),
                end=now.isoformat(),
            )
        elif index >= 6:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            if index == 7:
                start -= timedelta(days=now.weekday())
            if index == 8:
                start = start.replace(day=1)
            filters.update(start=start.isoformat(), end=now.isoformat())
        return filters

    def set_rows(self, rows, cfg):
        sampled = sample_rows(rows, cfg.chart_points)
        for c in [self.combined, *self.charts]:
            c.set_rows(sampled)
        self.charts[0].set_limit(cfg.soil_min_pct)
        self.charts[1].set_limit(cfg.temp_critical_c)
        self.charts[3].set_limit(cfg.light_critical_pct)
        self.info.setText(
            f"{len(rows):,} leituras no período · {len(sampled):,} pontos por série · horários locais"
        )
