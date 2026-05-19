# src/listener_win.py
#
# Script de reconocimiento de voz para Windows.
# Electron lo ejecuta como proceso hijo.
# Escucha continuamente y cuando detecta "Orion..." imprime el comando en stdout.
# Electron lee stdout línea por línea y ejecuta el comando.

import json
import queue
import re
import sys
import os
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Agregar el proyecto al path para importar módulos de ORION
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..', '..', '..')
sys.path.insert(0, PROJECT_ROOT)

import numpy as np
import soxr
import sounddevice as sd
from vosk import Model, KaldiRecognizer

MODEL_PATH   = os.path.join(os.path.dirname(__file__), '..', '..', 'models', 'vosk-es')
DEVICE_RATE  = 44100
VOSK_RATE    = 16000
BLOCKSIZE    = int(DEVICE_RATE * 0.125)
HOTWORDS     = ["orion", "orión"]

audio_queue = queue.Queue()


def callback(indata, frames, time_info, status):
    try:
        audio_f32   = indata[:, 0].copy()
        resampled   = soxr.resample(audio_f32, DEVICE_RATE, VOSK_RATE)
        audio_int16 = (resampled * 32767).astype(np.int16)
        audio_queue.put_nowait(audio_int16.tobytes())
    except Exception:
        pass


def main():
    model      = Model(MODEL_PATH)
    recognizer = KaldiRecognizer(model, VOSK_RATE)

    # Imprimir que está listo (Electron lo usa para saber que puede empezar)
    print("READY", flush=True)

    with sd.InputStream(
        samplerate=DEVICE_RATE,
        blocksize=BLOCKSIZE,
        dtype="float32",
        channels=1,
        callback=callback,
    ):
        while True:
            try:
                data = audio_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                texto  = (result.get("text") or "").strip().lower()

                if not texto:
                    continue

                # Verificar si contiene hotword
                tiene_hotword = any(hw in texto for hw in HOTWORDS)
                if not tiene_hotword:
                    continue

                # Extraer comando
                comando = texto
                for hw in HOTWORDS:
                    comando = re.sub(r"^" + hw + r"[,\s]*", "", comando).strip()

                if comando and len(comando) >= 2:
                    print(f"CMD:{comando}", flush=True)
                elif not comando:
                    print("HOTWORD", flush=True)

                # Reiniciar recognizer para limpiar el estado
                recognizer = KaldiRecognizer(model, VOSK_RATE)


if __name__ == "__main__":
    main()