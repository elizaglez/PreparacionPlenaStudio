from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QPushButton

class HomePage(QWidget):
    navigate = Signal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        title = QLabel("Preparación Plena Studio")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Crea y administra proyectos para producir el MASTER con la metodología PPA.")
        subtitle.setObjectName("Muted")
        subtitle.setWordWrap(True)
        grid = QGridLayout()
        items = [
            ("Nuevo proyecto","Carga el PDF, el MP3 y las citas bíblicas.","new"),
            ("Abrir proyecto","Abre una carpeta que contenga proyecto.json.","open"),
            ("Historial","Consulta los proyectos recientes.","history"),
            ("Configuración","Define la carpeta y revisa la metodología.","settings")
        ]
        for i,(name,desc,target) in enumerate(items):
            b = QPushButton(f"{name}\n{desc}")
            b.setMinimumHeight(105)
            b.clicked.connect(lambda checked=False, p=target: self.navigate.emit(p))
            grid.addWidget(b, i//2, i%2)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30,30,30,30)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(15)
        layout.addLayout(grid)
        layout.addStretch()
