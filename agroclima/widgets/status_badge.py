from PySide6.QtWidgets import QLabel


class StatusBadge(QLabel):
    def __init__(self, text="Aguardando", tone="neutral"):
        super().__init__()
        self.setObjectName("badge")
        self.update_status(text, tone)

    def update_status(self, text, tone):
        self.setText("●  " + text)
        self.setProperty("tone", tone)
        self.style().unpolish(self)
        self.style().polish(self)
