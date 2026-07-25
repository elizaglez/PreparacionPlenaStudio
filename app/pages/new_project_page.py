from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QGroupBox, QLabel, QLineEdit, QPushButton, QMessageBox
from app.widgets import FilePicker
from app.storage import load_settings
from app.project_service import create_project, ProjectError

class NewProjectPage(QWidget):
    project_created = Signal(dict)
    def __init__(self, parent=None):
        super().__init__(parent)
        title = QLabel("Nuevo proyecto")
        title.setObjectName("PageTitle")
        note = QLabel("Selecciona las tres fuentes. La aplicación las copiará a una carpeta independiente.")
        note.setObjectName("Muted")
        note.setWordWrap(True)
        self.name = QLineEdit()
        self.name.setPlaceholderText("Ejemplo: Estudio WT 32-2026")
        self.pdf = FilePicker("Seleccionar PDF","PDF (*.pdf)")
        self.audio = FilePicker("Seleccionar audio","Audio (*.mp3 *.wav *.m4a)")
        self.bible = FilePicker("Seleccionar citas","Documentos (*.txt *.docx *.pdf);;Todos (*.*)")
        self.destination = FilePicker("Carpeta de proyectos","",True)
        self.destination.set_value(load_settings().get("default_projects_folder",""))
        form = QFormLayout()
        form.addRow("Nombre", self.name)
        form.addRow("PDF", self.pdf)
        form.addRow("Audio", self.audio)
        form.addRow("Citas bíblicas", self.bible)
        form.addRow("Destino", self.destination)
        group = QGroupBox("Fuentes")
        group.setLayout(form)
        self.create_button = QPushButton("CREAR PROYECTO")
        self.create_button.setObjectName("PrimaryButton")
        self.create_button.clicked.connect(self.create)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30,30,30,30)
        layout.addWidget(title)
        layout.addWidget(note)
        layout.addWidget(group)
        layout.addWidget(self.create_button)
        layout.addStretch()

    def create(self):
        self.create_button.setEnabled(False)
        try:
            project = create_project(self.name.text(), self.destination.value(), self.pdf.value(), self.audio.value(), self.bible.value())
        except ProjectError as exc:
            QMessageBox.warning(self,"No se pudo crear",str(exc))
        except Exception as exc:
            QMessageBox.critical(self,"Error",str(exc))
        else:
            QMessageBox.information(self,"Proyecto creado",project.root)
            self.project_created.emit(project)
            self.name.clear(); self.pdf.set_value(""); self.audio.set_value(""); self.bible.set_value("")
        finally:
            self.create_button.setEnabled(True)
