from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from .common import label, icon
from ..widgets.status_badge import StatusBadge


class SensorCard(QFrame):
    def __init__(self, title, unit, symbol):
        super().__init__()
        self.unit = unit
        self.setObjectName("card")
        self.setMinimumWidth(160)
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 16, 16, 14)
        v.setSpacing(10)
        row = QHBoxLayout()
        image = QLabel()
        image.setPixmap(icon(symbol).pixmap(22, 22))
        row.addWidget(image)
        row.addWidget(label(title, "eyebrow"))
        row.addStretch()
        v.addLayout(row)
        self.value = label("—", "sensorValue")
        v.addWidget(self.value)
        self.badge = StatusBadge()
        v.addWidget(self.badge)
        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setRange(0, 100)
        self.bar.setFixedHeight(5)
        v.addWidget(self.bar)
        self.limit = label("Aguardando leitura", "tiny")
        v.addWidget(self.limit)
        self.trend = label("Tendência indisponível", "tiny")
        v.addWidget(self.trend)
        for text in self.findChildren(QLabel):
            if text is not self.value:
                text.setWordWrap(True)

    def update_reading(self, value, status, tone, limit, delta=None, maximum=100):
        self.value.setText(
            f"{value:.1f}".replace(".", ",")
            + f' <span style="font-size:15px;color:#7b8781">{self.unit}</span>'
        )
        self.badge.update_status(status, tone)
        self.bar.setValue(round(max(0, min(100, value / maximum * 100))))
        self.limit.setText(limit)
        self.trend.setText(
            "Coletando tendência de 10 min"
            if delta is None
            else f"{'↑' if delta >= 0 else '↓'} {abs(delta):.1f} {self.unit} em 10 min"
        )
