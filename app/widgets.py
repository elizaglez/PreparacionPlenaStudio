from pathlib import Path
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton, QFileDialog

class FilePicker(QWidget):
    value_changed = Signal(str)
    def __init__(self, title, file_filter="", select_directory=False, parent=None):
        super().__init__(parent)
        self.title = title
        self.file_filter = file_filter
        self.select_directory = select_directory
        self.edit = QLineEdit()
        self.edit.setPlaceholderText("Seleccionar…")
        self.edit.textChanged.connect(self.value_changed)
        self.button = QPushButton("Examinar")
        self.button.clicked.connect(self.browse)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.edit,1)
        layout.addWidget(self.button)

    def browse(self):
        initial = self.edit.text().strip()
        if initial and Path(initial).is_file():
            initial = str(Path(initial).parent)
        if self.select_directory:
            selected = QFileDialog.getExistingDirectory(self, self.title, initial)
        else:
            selected, _ = QFileDialog.getOpenFileName(self, self.title, initial, self.file_filter)
        if selected:
            self.edit.setText(selected)

    def value(self):
        return self.edit.text().strip()

    def set_value(self, value):
        self.edit.setText(value)
