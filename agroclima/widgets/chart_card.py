import pyqtgraph as pg
from PySide6.QtWidgets import QFrame, QVBoxLayout
from ..ui.common import label

pg.setConfigOptions(antialias=True, background="w", foreground="#78857e")


class ChartCard(QFrame):
    def __init__(self, title, series, height=250):
        super().__init__()
        self.setObjectName("card")
        v = QVBoxLayout(self)
        v.setContentsMargins(18, 16, 18, 14)
        v.addWidget(label(title, "cardTitle"))
        self.plot = pg.PlotWidget(axisItems={"bottom": pg.DateAxisItem()})
        self.plot.setFixedHeight(height)
        self.plot.showGrid(x=False, y=True, alpha=0.12)
        self.plot.setMenuEnabled(False)
        self.plot.hideButtons()
        self.plot.setClipToView(True)
        self.plot.addLegend(offset=(10, 8), brush=(255, 255, 255, 230), pen=None)
        v.addWidget(self.plot)
        self.curves = {}
        self.threshold = None
        for key, title, color in series:
            self.curves[key] = self.plot.plot(
                [], [], pen=pg.mkPen(color, width=2.2), name=title
            )

    def set_rows(self, rows):
        from datetime import datetime

        x = [datetime.fromisoformat(r[0]).timestamp() for r in rows]
        for key, curve in self.curves.items():
            curve.setData(x, [r[key] for r in rows])

    def set_limit(self, value):
        if self.threshold is None:
            from PySide6.QtCore import Qt

            self.threshold = pg.InfiniteLine(
                value,
                angle=0,
                pen=pg.mkPen("#D4A251", style=Qt.DashLine),
                label="Limite {value:.0f}",
            )
            self.plot.addItem(self.threshold)
        self.threshold.setValue(value)
