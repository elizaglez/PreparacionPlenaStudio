from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.dialogs import ProcessingDialog
from app.exporters import export_master_to_docx
from app.workers import MasterGeneratorWorker, SourceProcessorWorker


class ProjectWorkspace(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.project = None
        self.thread = None
        self.worker = None
        self.processing_dialog = None
        self.current_operation = ""

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

        actions = QHBoxLayout()
        self.analyze = QPushButton("1. ANALIZAR ARTÍCULO")
        self.analyze.setObjectName("PrimaryButton")
        self.analyze.setEnabled(False)
        self.analyze.clicked.connect(self.process_sources)

        self.generate = QPushButton("2. GENERAR MASTER")
        self.generate.setEnabled(False)
        self.generate.clicked.connect(self.generate_master)

        self.export = QPushButton("3. EXPORTAR A WORD")
        self.export.setEnabled(False)
        self.export.clicked.connect(self.export_word)

        actions.addWidget(self.analyze)
        actions.addWidget(self.generate)
        actions.addWidget(self.export)

        diagnostics_group = QGroupBox("Estado del proyecto")
        diagnostics_layout = QVBoxLayout(diagnostics_group)
        self.diagnostics = QPlainTextEdit()
        self.diagnostics.setReadOnly(True)
        self.diagnostics.setPlaceholderText(
            "Aquí aparecerán el diagnóstico y el estado del MASTER."
        )
        diagnostics_layout.addWidget(self.diagnostics)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        layout.addWidget(self.title)
        layout.addWidget(self.path)
        layout.addWidget(self.status)
        layout.addWidget(source_group)
        layout.addLayout(actions)
        layout.addWidget(diagnostics_group, 1)

    def set_project(self, project: dict) -> None:
        self.project = project
        self.title.setText(project.get("name", "Proyecto"))
        self.path.setText(project.get("root", ""))
        self.status.setText("Proyecto listo.")
        sources = project.get("sources", {})
        self.pdf.setText("PDF: " + sources.get("pdf", "—"))
        self.audio.setText("Audio: " + sources.get("audio", "—"))
        self.bible.setText("Citas: " + sources.get("bible", "—"))
        self.analyze.setEnabled(True)
        self._refresh_outputs()

    def _refresh_outputs(self) -> None:
        if not self.project:
            return
        work = Path(self.project["root"]) / "trabajo"
        article_exists = (work / "articulo.json").is_file()
        master_exists = (work / "master.json").is_file()
        self.generate.setEnabled(article_exists and self.thread is None)
        self.export.setEnabled(master_exists and self.thread is None)

        if master_exists:
            try:
                master = json.loads(
                    (work / "master.json").read_text(encoding="utf-8")
                )
                self._show_master(master)
                self.status.setText("MASTER generado, validado y listo para revisar.")
                return
            except Exception:
                pass

        summary_path = work / "fuentes_resumen.json"
        if summary_path.is_file():
            try:
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
                self._show_source_summary(summary)
                return
            except Exception:
                pass
        self.diagnostics.clear()

    def _start_worker(self, worker, operation: str) -> None:
        self.current_operation = operation
        self.analyze.setEnabled(False)
        self.generate.setEnabled(False)
        self.export.setEnabled(False)
        self.processing_dialog = ProcessingDialog(self)

        self.thread = QThread(self)
        self.worker = worker
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.processing_dialog.update_progress)
        self.worker.finished.connect(self._operation_finished)
        self.worker.failed.connect(self._operation_failed)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self._thread_finished)

        self.thread.start()
        self.processing_dialog.exec()

    def process_sources(self) -> None:
        if self.project:
            self._start_worker(
                SourceProcessorWorker(self.project),
                "analyze",
            )

    def generate_master(self) -> None:
        if self.project:
            answer = QMessageBox.question(
                self,
                "Generar MASTER",
                "Se enviará una solicitud a OpenAI por cada pregunta detectada. "
                "Esto puede generar costos de API. ¿Continuar?",
            )
            if answer == QMessageBox.StandardButton.Yes:
                self._start_worker(
                    MasterGeneratorWorker(self.project),
                    "master",
                )

    def _operation_finished(self, result: dict) -> None:
        if self.current_operation == "analyze":
            self.status.setText("Artículo analizado y estructurado.")
            self._show_source_summary(result)
            message = (
                "Listo. Se creó trabajo/articulo.json con preguntas, "
                "párrafos y referencias bíblicas."
            )
        else:
            self.status.setText("MASTER generado, validado y listo para revisar.")
            self._load_and_show_master()
            message = (
                "Listo. Se creó trabajo/master.json. "
                "Ya puedes exportarlo a Word."
            )

        if self.processing_dialog:
            self.processing_dialog.mark_finished(message)

    def _operation_failed(self, message: str) -> None:
        self.status.setText("La operación no pudo completarse.")
        if self.processing_dialog:
            self.processing_dialog.mark_failed(message)
        QMessageBox.critical(self, "Error", message)

    def _thread_finished(self) -> None:
        self.thread = None
        self.worker = None
        self.current_operation = ""
        self.analyze.setEnabled(True)
        self._refresh_outputs()

    def _show_source_summary(self, summary: dict) -> None:
        diagnostics = summary.get("diagnostics", {})
        article = summary.get("article", {})
        warnings = article.get("warnings", [])
        lines = [
            "ARTÍCULO ESTRUCTURADO",
            "",
            f"Título: {article.get('title', '—')}",
            f"Preguntas: {diagnostics.get('structured_sections', 0)}",
            f"Referencias bíblicas: "
            f"{diagnostics.get('detected_scripture_references', 0)}",
            f"Párrafos sin asignar: "
            f"{article.get('unassigned_paragraphs', 0)}",
            "",
            "Archivo: trabajo/articulo.json",
        ]
        if warnings:
            lines.extend(["", "Advertencias:"])
            lines.extend(f"• {warning}" for warning in warnings)
        self.diagnostics.setPlainText("\n".join(lines))

    def _load_and_show_master(self) -> None:
        if not self.project:
            return
        path = Path(self.project["root"]) / "trabajo" / "master.json"
        try:
            master = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return
        self._show_master(master)

    def _show_master(self, master: dict) -> None:
        lines = [
            "MASTER",
            "",
            master.get("title", "Sin título"),
            f"Modelo: {master.get('model', '—')}",
            f"Respuestas: {len(master.get('answers', []))}",
            "Validación: superada",
            "",
        ]
        for item in master.get("answers", []):
            lines.append(item.get("question", ""))
            lines.append(item.get("answer", ""))
            lines.append("")
        self.diagnostics.setPlainText("\n".join(lines).strip())

    def export_word(self) -> None:
        if not self.project:
            return
        try:
            path = export_master_to_docx(self.project)
        except Exception as exc:
            QMessageBox.critical(self, "Error al exportar", str(exc))
            return
        self._refresh_outputs()
        QMessageBox.information(
            self,
            "MASTER exportado",
            f"Se creó:\n{path}",
        )
