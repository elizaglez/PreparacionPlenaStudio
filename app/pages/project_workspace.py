from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox, QPushButton

class ProjectWorkspace(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.title=QLabel("Proyecto"); self.title.setObjectName("PageTitle")
        self.path=QLabel(""); self.path.setObjectName("Muted"); self.path.setWordWrap(True)
        self.status=QLabel("No hay ningún proyecto abierto.")
        group=QGroupBox("Fuentes"); gl=QVBoxLayout(group)
        self.pdf=QLabel("PDF: —"); self.audio=QLabel("Audio: —"); self.bible=QLabel("Citas: —")
        gl.addWidget(self.pdf); gl.addWidget(self.audio); gl.addWidget(self.bible)
        self.generate=QPushButton("GENERAR MASTER"); self.generate.setObjectName("PrimaryButton"); self.generate.setEnabled(False)
        self.generate.setToolTip("Se activará en la Entrega 2.")
        layout=QVBoxLayout(self); layout.setContentsMargins(30,30,30,30)
        layout.addWidget(self.title); layout.addWidget(self.path); layout.addWidget(self.status); layout.addWidget(group); layout.addWidget(self.generate); layout.addStretch()

    def set_project(self,p):
        self.title.setText(p.get("name","Proyecto"))
        self.path.setText(p.get("root",""))
        self.status.setText("Proyecto listo. Las fuentes se copiaron correctamente.")
        s=p.get("sources",{})
        self.pdf.setText("PDF: "+s.get("pdf","—"))
        self.audio.setText("Audio: "+s.get("audio","—"))
        self.bible.setText("Citas: "+s.get("bible","—"))
