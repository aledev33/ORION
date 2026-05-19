# orion/commands/take_photo_command.py
#
# Comando TAKE_PHOTO — toma una foto con la cámara USB.
# Cuenta regresiva de 3 segundos y guarda la foto.

import sys
import time
import threading
from datetime import datetime
from pathlib import Path

from orion.commands.base import BaseCommand, CommandResult

_FOTOS_DIR = Path.home() / "orion_fotos"


def _tomar_foto(speaker) -> tuple[bool, str]:
    """Toma foto con cámara USB usando OpenCV."""
    try:
        import cv2
    except ImportError:
        return False, "OpenCV no está instalado."

    _FOTOS_DIR.mkdir(exist_ok=True)
    nombre = f"orion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    ruta   = _FOTOS_DIR / nombre

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return False, "No se pudo acceder a la cámara."

    # Warm-up en hilo separado mientras hace la cuenta regresiva
    frames_listos = []

    def warmup():
        for _ in range(20):
            ret, frame = cap.read()
            if ret and frame is not None:
                frames_listos.append(frame)
            time.sleep(0.05)

    t = threading.Thread(target=warmup, daemon=True)
    t.start()

    # Cuenta regresiva hablada (3 segundos)
    speaker.decir("3")
    time.sleep(0.9)
    speaker.decir("2")
    time.sleep(0.9)
    speaker.decir("1")
    time.sleep(0.9)

    # Tomar foto
    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        if frames_listos:
            frame = frames_listos[-1]
        else:
            return False, "No se pudo capturar la imagen."

    cv2.imwrite(str(ruta), frame)
    print(f"[TakePhoto] Foto guardada: {ruta}")
    return True, str(ruta)


class TakePhotoCommand(BaseCommand):
    intent_name = "TAKE_PHOTO"

    def execute(self, context, text: str, payload: str, confidence: float) -> CommandResult:
        ok, resultado = _tomar_foto(context.speaker)

        if ok:
            context.speaker.decir("Foto tomada.")
            return CommandResult(
                success=True,
                message="Foto tomada y guardada.",
                action="TAKE_PHOTO_OK",
                payload=resultado,
            )
        else:
            return CommandResult(
                success=False,
                message=resultado,
                action="TAKE_PHOTO_FAIL",
                payload="",
            )