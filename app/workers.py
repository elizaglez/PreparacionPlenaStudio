from __future__ import annotations

import traceback

from PySide6.QtCore import QObject, Signal, Slot

from app.master_generator import generate_master
from app.source_processor import process_project_sources


class SourceProcessorWorker(QObject):
    progress = Signal(int, str)
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, project: dict):
        super().__init__()
        self.project = project

    @Slot()
    def run(self) -> None:
        try:
            result = process_project_sources(
                self.project,
                lambda value, message: self.progress.emit(value, message),
            )
        except Exception as exc:
            details = traceback.format_exc()
            self.failed.emit(f"{exc}\n\nDetalles técnicos:\n{details}")
        else:
            self.finished.emit(result)


class MasterGeneratorWorker(QObject):
    progress = Signal(int, str)
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, project: dict):
        super().__init__()
        self.project = project

    @Slot()
    def run(self) -> None:
        try:
            result = generate_master(
                self.project,
                lambda value, message: self.progress.emit(value, message),
            )
        except Exception as exc:
            details = traceback.format_exc()
            self.failed.emit(f"{exc}\n\nDetalles técnicos:\n{details}")
        else:
            self.finished.emit(result)
