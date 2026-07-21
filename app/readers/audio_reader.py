from __future__ import annotations

import wave
from pathlib import Path
from typing import Any


class AudioReadError(RuntimeError):
    pass


def inspect_audio(path: str | Path) -> dict[str, Any]:
    audio_path = Path(path)
    if not audio_path.is_file():
        raise AudioReadError("No se encontró el archivo de audio.")

    suffix = audio_path.suffix.lower()
    result: dict[str, Any] = {
        "file": str(audio_path.resolve()),
        "format": suffix.lstrip("."),
        "size_bytes": audio_path.stat().st_size,
        "duration_seconds": None,
        "transcription_status": "pendiente",
        "note": (
            "La transcripción se conectará al motor de IA en una entrega posterior. "
            "En esta entrega se valida y registra el archivo."
        ),
    }

    if suffix == ".wav":
        try:
            with wave.open(str(audio_path), "rb") as wav:
                frames = wav.getnframes()
                rate = wav.getframerate()
                if rate:
                    result["duration_seconds"] = round(frames / rate, 2)
        except Exception:
            pass

    if suffix not in {".mp3", ".wav", ".m4a"}:
        raise AudioReadError("El audio debe ser MP3, WAV o M4A.")

    if result["size_bytes"] == 0:
        raise AudioReadError("El archivo de audio está vacío.")

    return result
