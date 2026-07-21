from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QGroupBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.dialogs import ProcessingDialog
from app.workers import SourceProcessorWorker


class ProjectWorkspace(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.project = None
        self.thread = None
        self.worker = None
        self.processing_dialog = None

        self.title = QLabel("Proyecto")
        self.title.setObjectName("PageTitle")

        self.path = QLabel("")
        self.path.setObjectName("Muted")
        self.path.setWordWrap(True)

        self.status = QLabel("No hay ningún proyecto abierto.")

        source_group = QGroupBox("Fuentes")
        source_layout = QVBoxLayout(source_group)
        self.pdf = QLabel("PDF: —")
        self.audio = QLabel("Audio: —")
        self.bible = QLabel("Citas: —")
        source_layout.addWidget(self.pdf)
        source_layout.addWidget(self.audio)
        source_layout.addWidget(self.bible)

        self.generate = QPushButton("ANALIZAR Y ESTRUCTURAR ARTÍCULO")
        self.generate.setObjectName("PrimaryButton")
        self.generate.setEnabled(False)
        self.generate.clicked.connect(self.process_sources)

        diagnostics_group = QGroupBox("Diagnóstico del artículo")
        diagnostics_layout = QVBoxLayout(diagnostics_group)
        self.diagnostics = QPlainTextEdit()
        self.diagnostics.setReadOnly(True)
        self.diagnostics.setPlaceholderText(
            "Aquí aparecerá la estructura detectada del artículo."
        )
        diagnostics_layout.addWidget(self.diagnostics)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        layout.addWidget(self.title)
        layout.addWidget(self.path)
        layout.addWidget(self.status)
        layout.addWidget(source_group)
        layout.addWidget(self.generate)
        layout.addWidget(diagnostics_group, 1)

    def set_project(self, project: dict) -> None:
        self.project = project
        self.title.setText(project.get("name", "Proyecto"))
        self.path.setText(project.get("root", ""))
        self.status.setText("Proyecto listo para analizar el artículo.")
        sources = project.get("sources", {})
        self.pdf.setText("PDF: " + sources.get("pdf", "—"))
        self.audio.setText("Audio: " + sources.get("audio", "—"))
        self.bible.setText("Citas: " + sources.get("bible", "—"))
        self.generate.setEnabled(True)
        self._load_existing_diagnostics()

    def _load_existing_diagnostics(self) -> None:
        if not self.project:
            return
        summary_path = (
            Path(self.project["root"]) / "trabajo" / "fuentes_resumen.json"
        )
        if summary_path.is_file():
            try:
                data = json.loads(summary_path.read_text(encoding="utf-8"))
                self._show_summary(data)
            except Exception:
                self.diagnostics.setPlainText(
                    "Existe un diagnóstico anterior, pero no se pudo leer."
                )
        else:
            self.diagnostics.clear()

    def process_sources(self) -> None:
        if not self.project:
            return

        self.generate.setEnabled(False)
        self.processing_dialog = ProcessingDialog(self)

        self.thread = QThread(self)
        self.worker = SourceProcessorWorker(self.project)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.processing_dialog.update_progress)
        self.worker.finished.connect(self._processing_finished)
        self.worker.failed.connect(self._processing_failed)

        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self._thread_finished)

        self.thread.start()
        self.processing_dialog.exec()

    def _processing_finished(self, summary: dict) -> None:
        self.status.setText("Artículo analizado y estructurado.")
        self._show_summary(summary)
        if self.processing_dialog:
            self.processing_dialog.mark_finished(
                "Listo. Se creó trabajo/articulo.json con preguntas, "
                "párrafos y referencias bíblicas."
            )

    def _processing_failed(self, message: str) -> None:
        self.status.setText("No se pudo estructurar el artículo.")
        if self.processing_dialog:
            self.processing_dialog.mark_failed(message)
        QMessageBox.critical(
            self,
            "Error al analizar el artículo",
            message,
        )

    def _thread_finished(self) -> None:
        self.generate.setEnabled(True)
        self.thread = None
        self.worker = None

    def _show_summary(self, summary: dict) -> None:
        d = summary.get("diagnostics", {})
        article = summary.get("article", {})
        warnings = article.get("warnings", [])

        lines = [
            f"Título detectado: {article.get('title', '—')}",
            f"Páginas del PDF: {d.get('pdf_pages', 0)}",
            f"Caracteres extraídos: {d.get('pdf_characters', 0)}",
            f"Preguntas detectadas: {d.get('detected_questions', 0)}",
            f"Secciones estructuradas: {d.get('structured_sections', 0)}",
            f"Referencias bíblicas detectadas: {d.get('detected_scripture_references', 0)}",
            f"Párrafos sin asignar: {article.get('unassigned_paragraphs', 0)}",
            f"Advertencias del parser: {d.get('parser_warnings', 0)}",
            "",
            "Archivos creados:",
            "• trabajo/pdf_extraido.txt",
            "• trabajo/citas_extraidas.txt",
            "• trabajo/articulo.json",
            "• trabajo/fuentes_resumen.json",
        ]

        if warnings:
            lines.extend(["", "Advertencias:"])
            lines.extend(f"• {warning}" for warning in warnings)

        self.diagnostics.setPlainText("\n".join(lines))
