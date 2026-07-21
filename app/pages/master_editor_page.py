from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.editor import MasterStore
from app.master_generator import regenerate_answer, regenerate_stage


STATUS_LABELS = {
    "pending": "Pendiente",
    "reviewed": "Revisada",
    "approved": "Aprobada",
    "regenerated": "Regenerada",
    "edited": "Editada",
}
LABEL_TO_STATUS = {label: status for status, label in STATUS_LABELS.items()}

STAGE_LABELS = {
    "Respuesta principal": "answer",
    "Explicación bíblica": "scripture_explanation",
    "Comparación": "comparison",
    "Aplicación": "application",
    "Nota de imagen": "image_note",
}


class AnswerCard(QGroupBox):
    changed = Signal()

    def __init__(self, store: MasterStore, answer: dict, project: dict, parent=None):
        super().__init__(parent)
        self.store = store
        self.project = project
        self.number = int(answer.get("number", 0))
        self.setTitle(f"Pregunta {self.number}")

        question = QLabel(answer.get("question", ""))
        question.setWordWrap(True)
        question.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.answer_edit = QPlainTextEdit(answer.get("answer", ""))
        self.scripture_edit = QPlainTextEdit(
            answer.get("scripture_explanation", "")
        )
        self.comparison_edit = QPlainTextEdit(answer.get("comparison", ""))
        self.application_edit = QPlainTextEdit(answer.get("application", ""))
        self.image_edit = QPlainTextEdit(answer.get("image_note", ""))

        for editor in (
            self.answer_edit,
            self.scripture_edit,
            self.comparison_edit,
            self.application_edit,
            self.image_edit,
        ):
            editor.setMinimumHeight(72)

        self.status = QComboBox()
        self.status.addItems(list(LABEL_TO_STATUS))
        self.status.setCurrentText(
            STATUS_LABELS.get(answer.get("status", "pending"), "Pendiente")
        )

        form = QFormLayout()
        form.addRow("Pregunta", question)
        form.addRow("Respuesta", self.answer_edit)
        form.addRow("Explicación bíblica", self.scripture_edit)
        form.addRow("Comparación", self.comparison_edit)
        form.addRow("Aplicación", self.application_edit)
        form.addRow("Nota de imagen", self.image_edit)
        form.addRow("Estado", self.status)

        save = QPushButton("Guardar cambios")
        approve = QPushButton("Aprobar")
        regenerate = QPushButton("Regenerar respuesta completa")
        self.stage_selector = QComboBox()
        self.stage_selector.addItems(list(STAGE_LABELS))
        regenerate_part = QPushButton("Regenerar etapa")
        save.clicked.connect(self.save_changes)
        approve.clicked.connect(self.approve)
        regenerate.clicked.connect(self.regenerate)
        regenerate_part.clicked.connect(self.regenerate_selected_stage)

        buttons = QHBoxLayout()
        buttons.addWidget(save)
        buttons.addWidget(approve)
        buttons.addWidget(regenerate)
        buttons.addWidget(self.stage_selector)
        buttons.addWidget(regenerate_part)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(buttons)

    def fields(self) -> dict:
        return {
            "answer": self.answer_edit.toPlainText(),
            "scripture_explanation": self.scripture_edit.toPlainText(),
            "comparison": self.comparison_edit.toPlainText(),
            "application": self.application_edit.toPlainText(),
            "image_note": self.image_edit.toPlainText(),
        }

    def save_changes(self) -> None:
        try:
            status = LABEL_TO_STATUS[self.status.currentText()]
            if status == "pending":
                status = "edited"
            updated = self.store.update_answer(
                self.number,
                self.fields(),
                status=status,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Error al guardar", str(exc))
            return
        self.status.setCurrentText(
            STATUS_LABELS.get(updated.get("status", "edited"), "Editada")
        )
        self.changed.emit()

    def approve(self) -> None:
        try:
            self.store.update_answer(
                self.number,
                self.fields(),
                status="approved",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Error al aprobar", str(exc))
            return
        self.status.setCurrentText("Aprobada")
        self.changed.emit()

    def regenerate(self) -> None:
        choice = QMessageBox.question(
            self,
            "Regenerar respuesta",
            "Se hará una nueva solicitud a OpenAI para esta pregunta. "
            "El contenido actual será reemplazado. ¿Continuar?",
        )
        if choice != QMessageBox.StandardButton.Yes:
            return

        try:
            updated = regenerate_answer(self.project, self.number)
            self.store.set_status(self.number, "regenerated")
        except Exception as exc:
            QMessageBox.critical(self, "Error al regenerar", str(exc))
            return

        self.answer_edit.setPlainText(updated.get("answer", ""))
        self.scripture_edit.setPlainText(
            updated.get("scripture_explanation", "")
        )
        self.comparison_edit.setPlainText(updated.get("comparison", ""))
        self.application_edit.setPlainText(updated.get("application", ""))
        self.image_edit.setPlainText(updated.get("image_note", ""))
        self.status.setCurrentText("Regenerada")
        self.changed.emit()

    def regenerate_selected_stage(self) -> None:
        label = self.stage_selector.currentText()
        stage_key = STAGE_LABELS[label]
        choice = QMessageBox.question(
            self,
            "Regenerar etapa",
            f"Se reemplazará únicamente: {label}. ¿Continuar?",
        )
        if choice != QMessageBox.StandardButton.Yes:
            return

        try:
            updated = regenerate_stage(self.project, self.number, stage_key)
        except Exception as exc:
            QMessageBox.critical(self, "Error al regenerar etapa", str(exc))
            return

        field_widgets = {
            "answer": self.answer_edit,
            "scripture_explanation": self.scripture_edit,
            "comparison": self.comparison_edit,
            "application": self.application_edit,
            "image_note": self.image_edit,
        }
        field_widgets[stage_key].setPlainText(updated.get(stage_key, ""))
        self.status.setCurrentText("Regenerada")
        self.changed.emit()


class MasterEditorPage(QWidget):
    progress_changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project = None
        self.store = None

        title = QLabel("Editor del MASTER")
        title.setObjectName("PageTitle")
        self.progress = QLabel("No hay ningún MASTER abierto.")
        self.progress.setObjectName("Muted")

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.cards = QVBoxLayout(self.container)
        self.scroll.setWidget(self.container)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.addWidget(title)
        layout.addWidget(self.progress)
        layout.addWidget(self.scroll, 1)

    def set_project(self, project: dict) -> None:
        self.project = project
        self.store = MasterStore(project["root"])
        self.reload()

    def reload(self) -> None:
        while self.cards.count():
            item = self.cards.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if not self.store or not self.project:
            self.cards.addStretch(1)
            return

        try:
            master = self.store.load()
        except Exception as exc:
            self.progress.setText(str(exc))
            self.cards.addStretch(1)
            return

        for answer in master.get("answers", []):
            card = AnswerCard(self.store, answer, self.project)
            card.changed.connect(self.refresh_progress)
            self.cards.addWidget(card)
        self.cards.addStretch(1)
        self.refresh_progress()

    def refresh_progress(self) -> None:
        if not self.store:
            return
        stats = self.store.progress()
        self.progress.setText(
            f"{stats['approved']} de {stats['total']} respuestas aprobadas · "
            f"{stats['reviewed']} revisadas"
        )
        self.progress_changed.emit(stats)
