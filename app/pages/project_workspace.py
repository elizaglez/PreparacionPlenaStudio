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

from app.composition import create_article_content_worker
from app.dialogs import ProcessingDialog
from app.exporters import (
    export_generated_article_to_docx,
    export_master_to_docx,
)
from app.generation.article_generation_plan import (
    ArticleGenerationPlanError,
)
from app.generation.generated_article import GeneratedArticle
from app.persistence.generated_article_repository import (
    JsonGeneratedArticleRepository,
)
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

        self.generate = QPushButton("2. GENERAR CONTENIDO")
        self.generate.setEnabled(False)
        self.generate.clicked.connect(self.generate_article_content)

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
        self.title.setText(project.name)
        self.path.setText(project.root)
        self.status.setText("Proyecto listo.")
        sources = project.sources
        self.pdf.setText("PDF: " + sources.get("pdf", "—"))
        self.audio.setText("Audio: " + sources.get("audio", "—"))
        self.bible.setText("Citas: " + sources.get("bible", "—"))
        self.analyze.setEnabled(True)
        self._refresh_outputs()

    def _resolve_valid_output(
        self,
    ) -> tuple[str, GeneratedArticle | dict] | None:
        if not self.project:
            return None

        work = Path(self.project.root) / "trabajo"
        generated_article_path = work / "articulo_generado.json"
        if generated_article_path.is_file():
            try:
                generated_article = JsonGeneratedArticleRepository(
                    self.project.root
                ).load()
                return "generated_article", generated_article
            except Exception:
                pass

        master_path = work / "master.json"
        if master_path.is_file():
            try:
                master = json.loads(
                    master_path.read_text(encoding="utf-8")
                )
                if isinstance(master, dict):
                    return "master", master
            except Exception:
                pass

        return None

    def _refresh_outputs(self) -> None:
        if not self.project:
            return

        work = Path(self.project.root) / "trabajo"
        article_exists = (work / "articulo.json").is_file()
        generated_article_path = work / "articulo_generado.json"
        master_path = work / "master.json"
        resolved_output = self._resolve_valid_output()

        self.generate.setEnabled(article_exists and self.thread is None)
        self.export.setEnabled(
            resolved_output is not None and self.thread is None
        )

        if resolved_output is not None:
            output_kind, output_data = resolved_output
            if output_kind == "generated_article":
                self._show_generated_article(output_data)
                self.status.setText("Contenido del artículo generado.")
            else:
                master = output_data
                self._show_master(master)
                self.status.setText("MASTER generado, validado y listo para revisar.")
            return

        if generated_article_path.is_file() or master_path.is_file():
            self.export.setEnabled(False)
            self.status.setText("No hay una salida válida para exportar.")
            self.diagnostics.setPlainText(
                "SALIDA NO DISPONIBLE\n\n"
                "No se pudieron leer los archivos generados. "
                "Puedes volver a generar el contenido."
            )
            return

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

    def generate_article_content(self) -> None:
        if self.project:
            resolved_output = self._resolve_valid_output()
            has_generated_article = (
                resolved_output is not None
                and resolved_output[0] == "generated_article"
            )
            if has_generated_article:
                dialog_title = "Regenerar contenido"
                dialog_message = (
                    "Ya existe contenido generado. Si continúas, se reemplazará "
                    "el contenido anterior. Se enviará una solicitud a OpenAI "
                    "por cada pregunta detectada y esto puede generar costos "
                    "de API. ¿Continuar?"
                )
            else:
                dialog_title = "Generar contenido"
                dialog_message = (
                    "Se enviará una solicitud a OpenAI por cada pregunta detectada. "
                    "Esto puede generar costos de API. ¿Continuar?"
                )

            answer = QMessageBox.question(
                self,
                dialog_title,
                dialog_message,
            )
            if answer == QMessageBox.StandardButton.Yes:
                try:
                    worker = create_article_content_worker(self.project)
                except ArticleGenerationPlanError:
                    QMessageBox.critical(
                        self,
                        "Error",
                        "No se detectaron preguntas utilizables. "
                        "Revisa las fuentes y vuelve a analizar el artículo "
                        "antes de generar contenido.",
                    )
                    return
                except Exception:
                    QMessageBox.critical(
                        self,
                        "Error",
                        "No se pudo preparar la generación del artículo.",
                    )
                    return
                self._start_worker(worker, "article_content")

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

    def _operation_finished(self, result: object) -> None:
        if self.current_operation == "analyze":
            self.status.setText("Artículo analizado y estructurado.")
            self._show_source_summary(result)
            message = (
                "Listo. Se creó trabajo/articulo.json con preguntas, "
                "párrafos y referencias bíblicas."
            )
        elif self.current_operation == "article_content":
            self.status.setText("Contenido del artículo generado.")
            self._show_generated_article(result)
            message = (
                "Listo. Se creó trabajo/articulo_generado.json."
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

    def _show_generated_article(
        self,
        article: GeneratedArticle,
    ) -> None:
        question_count = len(article.introduction.questions) + sum(
            len(section.questions)
            for section in article.sections
        )
        answered_count = sum(
            1
            for question in article.introduction.questions
            if question.answer.strip()
        ) + sum(
            1
            for section in article.sections
            for question in section.questions
            if question.answer.strip()
        )
        lines = [
            "CONTENIDO GENERADO",
            "",
            article.title or "Sin título",
            f"Preguntas: {question_count}",
            f"Respuestas generadas: {answered_count}",
        ]

        def append_question(question) -> None:
            question_text = question.question.strip()
            if question_text:
                lines.extend(
                    [
                        "",
                        f"{question.number}. {question_text}",
                    ]
                )
            if question.answer.strip():
                lines.append(f"Respuesta: {question.answer.strip()}")
            if question.application.strip():
                lines.append(
                    f"Aplicación: {question.application.strip()}"
                )

        introduction_paragraphs = [
            str(paragraph.get("text", "")).strip()
            for paragraph in article.introduction.paragraphs
            if str(paragraph.get("text", "")).strip()
        ]
        if introduction_paragraphs or article.introduction.questions:
            lines.extend(["", "INTRODUCCIÓN"])
            lines.extend(introduction_paragraphs)
            for question in article.introduction.questions:
                append_question(question)

        for section in article.sections:
            subtitle = section.subtitle.strip()
            if subtitle:
                lines.extend(["", subtitle])

            if section.heygen_transition and section.heygen_transition.strip():
                lines.append(
                    f"Transición: {section.heygen_transition.strip()}"
                )

            for question in section.questions:
                append_question(question)

            if section.section_summary and section.section_summary.strip():
                lines.extend(
                    [
                        "",
                        f"Resumen: {section.section_summary.strip()}",
                    ]
                )

            for box in section.boxes:
                title = box.title.strip()
                explanation = box.explanation.strip()
                if not title and not explanation:
                    continue
                lines.append("")
                lines.append(
                    f"RECUADRO: {title}" if title else "RECUADRO"
                )
                if explanation:
                    lines.append(explanation)

        review_questions = [
            question.strip()
            for question in article.review_questions
            if question.strip()
        ]
        if review_questions:
            lines.extend(["", "PREGUNTAS DE REPASO"])
            lines.extend(
                f"• {question}"
                for question in review_questions
            )

        lines.extend(
            [
                "",
                "Archivo: trabajo/articulo_generado.json",
            ]
        )
        self.diagnostics.setPlainText("\n".join(lines))

    def _load_and_show_master(self) -> None:
        if not self.project:
            return
        path = Path(self.project.root) / "trabajo" / "master.json"
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

        resolved_output = self._resolve_valid_output()
        if resolved_output is None:
            QMessageBox.critical(
                self,
                "Error al exportar",
                "No hay una salida válida para exportar.",
            )
            return

        try:
            output_kind, _ = resolved_output
            if output_kind == "generated_article":
                path = export_generated_article_to_docx(self.project)
            else:
                path = export_master_to_docx(self.project)
        except Exception as exc:
            QMessageBox.critical(self, "Error al exportar", str(exc))
            return
        self._refresh_outputs()
        QMessageBox.information(
            self,
            "Contenido exportado",
            f"Se creó:\n{path}",
        )
