from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)


class ProcessingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Procesando fuentes")
        self.setModal(True)
        self.setMinimumWidth(480)
        self.setWindowFlag(Qt.WindowCloseButtonHint, False)

        self.label = QLabel("Preparando…")
        self.label.setWordWrap(True)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)

        self.close_button = QPushButton("Cerrar")
        self.close_button.setEnabled(False)
        self.close_button.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        layout.addWidget(self.label)
        layout.addWidget(self.progress)
        layout.addWidget(self.close_button)

    def update_progress(self, value: int, message: str) -> None:
        self.progress.setValue(value)
        self.label.setText(message)

    def mark_finished(self, message: str) -> None:
        self.progress.setValue(100)
        self.label.setText(message)
        self.close_button.setEnabled(True)

    def mark_failed(self, message: str) -> None:
        self.label.setText(message)
        self.close_button.setEnabled(True)
