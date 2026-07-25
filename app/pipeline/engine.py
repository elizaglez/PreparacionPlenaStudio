from __future__ import annotations

import time
from datetime import datetime
from typing import Callable, Iterable

from app.models import Project
from app.pipeline.execution import PipelineExecution
from app.pipeline.stage import PipelineStage, PipelineStageResult, StageStatus
from app.pipeline.state_store import PipelineStateStore


class PipelineError(RuntimeError):
    pass


StageExecutor = Callable[
    [PipelineStage, PipelineExecution],
    tuple[str, list[str]],
]
StageCallback = Callable[[PipelineStage, PipelineStageResult], None]


class PipelineEngine:
    def __init__(
        self,
        stages: Iterable[PipelineStage],
        executor: StageExecutor,
        *,
        state_store: PipelineStateStore | None = None,
    ):
        self.stages = list(stages)
        self._by_key = {stage.key: stage for stage in self.stages}
        if len(self._by_key) != len(self.stages):
            raise PipelineError("Hay etapas duplicadas en el pipeline.")
        self.executor = executor
        self.state_store = state_store

    def run(
        self,
        project: Project,
        *,
        question_number: int,
        question: str,
        initial_values: dict[str, str] | None = None,
        only_stage: str | None = None,
        callback: StageCallback | None = None,
    ) -> dict[str, PipelineStageResult]:
        execution = PipelineExecution(
            project=project,
            values=dict(initial_values or {}),
        )

        selected = self._select_stages(only_stage)
        for stage in selected:
            missing = [
                key
                for key in stage.dependencies
                if not execution.values.get(key, "").strip()
            ]
            if missing:
                result = PipelineStageResult(
                    key=stage.key,
                    status=StageStatus.FAILED,
                    error="Faltan dependencias: " + ", ".join(missing),
                )
                execution.results[stage.key] = result
                self._persist(question_number, question, result)
                raise PipelineError(
                    f"No se puede ejecutar {stage.label}: {result.error}"
                )

            result = PipelineStageResult(
                key=stage.key,
                status=StageStatus.RUNNING,
                started_at=self._now(),
            )
            execution.results[stage.key] = result
            self._persist(question_number, question, result)
            if callback:
                callback(stage, result)

            started = time.perf_counter()
            try:
                value, notes = self.executor(stage, execution)
                value = str(value).strip()
                if stage.required and not value:
                    raise PipelineError(
                        f"La etapa {stage.label} devolvió contenido vacío."
                    )
                result.value = value
                result.source_notes = [str(item).strip() for item in notes if str(item).strip()]
                result.status = StageStatus.COMPLETED
                execution.values[stage.key] = value
            except Exception as exc:
                result.status = StageStatus.FAILED
                result.error = str(exc)
                raise
            finally:
                result.duration_seconds = round(time.perf_counter() - started, 3)
                result.completed_at = self._now()
                self._persist(question_number, question, result)
                if callback:
                    callback(stage, result)

        return execution.results

    def _select_stages(self, only_stage: str | None) -> list[PipelineStage]:
        if not only_stage:
            return self.stages
        stage = self._by_key.get(only_stage)
        if stage is None:
            raise PipelineError(f"Etapa desconocida: {only_stage}")
        return [stage]

    def _persist(
        self,
        question_number: int,
        question: str,
        result: PipelineStageResult,
    ) -> None:
        if self.state_store:
            self.state_store.update_stage(
                question_number=question_number,
                question=question,
                stage_key=result.key,
                stage_data=result.to_dict(),
            )

    @staticmethod
    def _now() -> str:
        return datetime.now().astimezone().isoformat(timespec="seconds")
