from PySide6.QtWidgets import QWidget, QHBoxLayout, QDateEdit, QComboBox
from PySide6.QtCore import QDate
from .common import label


class Filters(QWidget):
    def __init__(self, days=0):
        super().__init__()
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        self.start = QDateEdit(QDate.currentDate().addDays(-days))
        self.end = QDateEdit(QDate.currentDate())
        for field in (self.start, self.end):
            field.setCalendarPopup(True)
            field.setDisplayFormat("dd/MM/yyyy")
        self.source = QComboBox()
        self.source.addItems(["Todas as fontes", "Arduino", "Demonstração"])
        h.addWidget(label("De", "muted"))
        h.addWidget(self.start)
        h.addWidget(label("até", "muted"))
        h.addWidget(self.end)
        h.addWidget(self.source)
        h.addStretch()

    def values(self, validate_dates=True):
        if validate_dates and self.start.date() > self.end.date():
            raise ValueError("A data inicial deve ser anterior à final.")
        return dict(
            start=self.start.date().toString("yyyy-MM-dd"),
            end=self.end.date().addDays(1).toString("yyyy-MM-dd"),
            source=[None, "arduino", "demo"][self.source.currentIndex()],
        )
