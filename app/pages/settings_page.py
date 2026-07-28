from __future__ import annotations

import json
import os
from pathlib import Path

from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.config import ROOT_DIR
from app.storage import load_methodology, load_settings, save_settings
from app.widgets import FilePicker


class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        title = QLabel("Configuración")
        title.setObjectName("PageTitle")

        self.folder = FilePicker("Carpeta de proyectos", "", True)
        self.model = QLineEdit()
        self.model.setPlaceholderText("gpt-5-mini")

        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("sk-…")
        self.api_key.setClearButtonEnabled(True)

        prefs = QGroupBox("Preferencias")
        form = QFormLayout(prefs)
        form.addRow("Carpeta de proyectos", self.folder)
        form.addRow("Modelo de OpenAI", self.model)
        form.addRow("Clave API de OpenAI", self.api_key)

        key_note = QLabel(
            "La clave se guarda únicamente en el archivo local .env, "
            "que está excluido de Git."
        )
        key_note.setObjectName("Muted")
        key_note.setWordWrap(True)
        form.addRow("", key_note)

        method = QGroupBox("Metodología PPA incorporada")
        method_layout = QVBoxLayout(method)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        method_layout.addWidget(self.text)

        save = QPushButton("Guardar configuración")
        save.setObjectName("PrimaryButton")
        save.clicked.connect(self.save)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.addWidget(title)
        layout.addWidget(prefs)
        layout.addWidget(method, 1)
        layout.addWidget(save)
        self.reload()

    def reload(self):
        settings = load_settings()
        self.folder.set_value(settings.get("default_projects_folder", ""))
        self.model.setText(settings.get("openai_model", "gpt-5-mini"))
        self.api_key.clear()
        self.text.setPlainText(
            json.dumps(load_methodology(), ensure_ascii=False, indent=2)
        )

    def save(self):
        settings = load_settings()
        settings["default_projects_folder"] = self.folder.value()
        settings["openai_model"] = self.model.text().strip() or "gpt-5-mini"
        save_settings(settings)

        key = self.api_key.text().strip()
        if key:
            env_path = ROOT_DIR / ".env"
            existing: list[str] = []
            if env_path.is_file():
                existing = env_path.read_text(encoding="utf-8").splitlines()

            updated = False
            output: list[str] = []
            for line in existing:
                if line.startswith("OPENAI_API_KEY="):
                    output.append(f"OPENAI_API_KEY={key}")
                    updated = True
                else:
                    output.append(line)
            if not updated:
                output.append(f"OPENAI_API_KEY={key}")
            env_path.write_text("\n".join(output).strip() + "\n", encoding="utf-8")
            os.environ["OPENAI_API_KEY"] = key
            self.api_key.clear()

        QMessageBox.information(
            self,
            "Configuración",
            "Configuración guardada correctamente.",
        )
