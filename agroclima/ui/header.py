from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout
from .common import label
from ..widgets.status_badge import StatusBadge


class Header(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("header")
        h = QHBoxLayout(self)
        h.setContentsMargins(26, 16, 26, 16)
        v = QVBoxLayout()
        v.addWidget(label("AgroClima Monitor", "headerTitle"))
        v.addWidget(label("Sistema Inteligente de Monitoramento Agrícola", "muted"))
        h.addLayout(v)
        h.addStretch()
        self.badge = StatusBadge("Desconectado", "danger")
        h.addWidget(self.badge)
        self.detail = label("Sem porta  •  Última leitura: —", "tiny")
        h.addSpacing(15)
        h.addWidget(self.detail)
