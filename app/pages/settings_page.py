import json
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QGroupBox, QLabel, QPlainTextEdit, QPushButton, QMessageBox
from app.widgets import FilePicker
from app.storage import load_settings, save_settings, load_methodology

class SettingsPage(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        title = QLabel("Configuración"); title.setObjectName("PageTitle")
        self.folder = FilePicker("Carpeta de proyectos","",True)
        prefs = QGroupBox("Preferencias")
        form = QFormLayout(prefs); form.addRow("Carpeta de proyectos",self.folder)
        method = QGroupBox("Metodología PPA incorporada")
        ml = QVBoxLayout(method); self.text = QPlainTextEdit(); self.text.setReadOnly(True); ml.addWidget(self.text)
        save = QPushButton("Guardar configuración"); save.setObjectName("PrimaryButton"); save.clicked.connect(self.save)
        layout = QVBoxLayout(self); layout.setContentsMargins(30,30,30,30)
        layout.addWidget(title); layout.addWidget(prefs); layout.addWidget(method,1); layout.addWidget(save)
        self.reload()

    def reload(self):
        self.folder.set_value(load_settings().get("default_projects_folder",""))
        self.text.setPlainText(json.dumps(load_methodology(),ensure_ascii=False,indent=2))

    def save(self):
        s=load_settings(); s["default_projects_folder"]=self.folder.value(); save_settings(s)
        QMessageBox.information(self,"Configuración","Guardada correctamente.")
