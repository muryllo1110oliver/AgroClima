from PySide6.QtWidgets import (
    QWidget,
    QFrame,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
)
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import Qt

PATHS = {
    "sprout": "M12 21v-9M12 16C3 16 3 7 3 7s9-1 9 9M12 12C12 3 21 3 21 3s1 9-9 9",
    "dashboard": "M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z",
    "activity": "M2 12h5l3-8 4 16 3-8h5",
    "chart": "M4 3v17h17M7 15l4-5 4 3 5-7",
    "database": "M4 6c0-4 16-4 16 0s-16 4-16 0v12c0 4 16 4 16 0V6M4 12c0 4 16 4 16 0",
    "file": "M5 3h10l4 4v14H5zM14 3v5h5M8 12h8M8 16h8",
    "settings": "M4 6h16M4 12h16M4 18h16M8 3v6M16 9v6M10 15v6",
    "drop": "M12 3C9 8 5 11 5 15a7 7 0 0 0 14 0c0-4-4-7-7-12z",
    "temp": "M9 14V5a3 3 0 0 1 6 0v9a5 5 0 1 1-6 0M12 8v10",
    "sun": "M12 2v2M12 20v2M2 12h2M20 12h2M5 5l2 2M17 17l2 2M5 19l2-2M17 7l2-2M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0",
    "rain": "M5 15a5 5 0 0 1 0-10 6 6 0 0 1 11-1 5 5 0 0 1 3 10M8 17l-1 4M13 17l-1 4M18 17l-1 4",
}


def icon(name, color="#497567"):
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><path d="{PATHS.get(name, PATHS["activity"])}" fill="none" stroke="{color}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    pix = QPixmap(24, 24)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    QSvgRenderer(svg.encode()).render(painter)
    painter.end()
    return QIcon(pix)


def label(text, role="body"):
    w = QLabel(text)
    w.setObjectName(role)
    return w


def button(text, callback=None, primary=False):
    w = QPushButton(text)
    w.setCursor(Qt.PointingHandCursor)
    if primary:
        w.setObjectName("primary")
    if callback:
        w.clicked.connect(callback)
    return w


def card():
    w = QFrame()
    w.setObjectName("card")
    v = QVBoxLayout(w)
    v.setContentsMargins(20, 16, 20, 16)
    v.setSpacing(10)
    return w, v


class Page(QScrollArea):
    def __init__(self, title, subtitle):
        super().__init__()
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.body = QWidget()
        self.body.setObjectName("pageBody")
        self.setWidget(self.body)
        self.layout = QVBoxLayout(self.body)
        self.layout.setContentsMargins(26, 22, 26, 24)
        self.layout.setSpacing(18)
        self.layout.addWidget(label(title, "pageTitle"))
        self.layout.addWidget(label(subtitle, "muted"))
