from PySide6.QtWidgets import QFrame, QVBoxLayout, QButtonGroup
from .common import label, button, icon


class Sidebar(QFrame):
    def __init__(self, select):
        super().__init__()
        self.setObjectName("sidebar")
        self.setFixedWidth(205)
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 28, 16, 20)
        v.setSpacing(8)
        v.addWidget(label("AgroClima", "brand"))
        v.addWidget(label("PRECISION AGRICULTURE", "sidebarSub"))
        v.addSpacing(34)
        v.addWidget(label("ÁREA DE TRABALHO", "sidebarSub"))
        v.addSpacing(8)
        self.group = QButtonGroup(self)
        items = [
            ("Dashboard", "dashboard"),
            ("Gráficos", "chart"),
            ("Configurações", "settings"),
        ]
        for i, (name, symbol) in enumerate(items):
            b = button(name)
            b.setIcon(icon(symbol, "#A9C7BA"))
            b.setCheckable(True)
            b.setObjectName("nav")
            self.group.addButton(b, i)
            v.addWidget(b)
        self.group.button(0).setChecked(True)
        self.group.idClicked.connect(select)
        v.addStretch()
        v.addWidget(label("AgroClima Monitor", "sidebarFooter"))
        v.addWidget(label("Versão 2.0  /  Desktop", "sidebarSub"))
