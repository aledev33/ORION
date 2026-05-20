# orion/commands/take_photo_command.py
import sys
import time
import threading
import subprocess
from datetime import datetime
from pathlib import Path
from orion.commands.base import BaseCommand, CommandResult

_FOTOS_DIR = Path.home() / "orion_fotos"


def _decir_rapido(texto: str):
    """TTS rápido usando espeak-ng directamente — más rápido que Piper para números."""
    try:
        subprocess.run(
            ["espeak-ng", "-v", "es", "-s", "180", "-a", "150", texto],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
    except Exception:
        pass


def _tomar_foto() -> tuple[bool, str]:
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

    # Warm-up en paralelo
    frame_final = [None]

    def warmup():
        for _ in range(15):
            ret, frame = cap.read()
            if ret and frame is not None:
                frame_final[0] = frame
            time.sleep(0.05)

    t = threading.Thread(target=warmup, daemon=True)
    t.start()

    # Cuenta regresiva rápida con espeak-ng
    _decir_rapido("3")
    time.sleep(0.8)
    _decir_rapido("2")
    time.sleep(0.8)
    _decir_rapido("1")
    time.sleep(0.8)

    # Tomar foto
    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        frame = frame_final[0]

    if frame is None:
        return False, "No se pudo capturar la imagen."

    cv2.imwrite(str(ruta), frame)
    print(f"[TakePhoto] Guardada: {ruta}")
    return True, str(ruta)


class TakePhotoCommand(BaseCommand):
    intent_name = "TAKE_PHOTO"

    def execute(self, context, text: str, payload: str, confidence: float) -> CommandResult:
        ok, resultado = _tomar_foto()

        if ok:
            return CommandResult(
                success=True,
                message="Foto tomada.",
                action="TAKE_PHOTO_OK",
                payload=resultado,
            )
        return CommandResult(
            success=False,
            message=resultado,
            action="TAKE_PHOTO_FAIL",
            payload="",
        )