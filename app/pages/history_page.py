from pathlib import Path
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton
from app.storage import load_recent_projects

class HistoryPage(QWidget):
    open_project = Signal(str)
    def __init__(self,parent=None):
        super().__init__(parent)
        title = QLabel("Historial"); title.setObjectName("PageTitle")
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(self.open_item)
        refresh = QPushButton("Actualizar"); refresh.clicked.connect(self.refresh)
        layout = QVBoxLayout(self); layout.setContentsMargins(30,30,30,30)
        layout.addWidget(title); layout.addWidget(self.list,1); layout.addWidget(refresh)
        self.refresh()

    def refresh(self):
        self.list.clear()
        for p in load_recent_projects():
            root = p.get("root","")
            text = f"{p.get('name','Proyecto')}\n{root}"
            if not Path(root).exists(): text += "\n(No disponible)"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, root)
            self.list.addItem(item)

    def open_item(self,item):
        root = item.data(Qt.UserRole)
        if root: self.open_project.emit(root)
