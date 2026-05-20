# orion/tts/speaker.py
from __future__ import annotations

import io
import os
import subprocess
import sys
import threading
import wave
from pathlib import Path

_DEFAULT_MODEL = Path.home() / "piper-voices" / "es_MX-claude-high.onnx"
_MODEL_PATH    = Path(os.getenv("PIPER_MODEL_PATH", str(_DEFAULT_MODEL)))


class _SpeakerWindows:
    def __init__(self, rate: int, volume: float):
        self.rate   = rate
        self.volume = volume

    def decir(self, texto: str):
        if not texto or not texto.strip():
            return
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate",   self.rate)
            engine.setProperty("volume", self.volume)
            engine.say(texto)
            engine.runAndWait()
            engine.stop()
        except Exception as e:
            print(f"[Speaker][Windows] Error TTS: {e}")

    def cerrar(self):
        pass


class _SpeakerLinux:
    def __init__(self, rate: int, volume: float):
        self.rate      = rate
        self.volume    = volume
        self._piper_ok = self._verificar_piper()
        self._lock     = threading.Lock()  # evitar llamadas simultáneas a Piper

        if not self._piper_ok:
            print("[Speaker][Linux] Piper no disponible. Usando espeak-ng.")
        else:
            # Precalentar Piper en background para reducir latencia del primer uso
            threading.Thread(target=self._precalentar, daemon=True).start()

    def _precalentar(self):
        """Lanza Piper con texto vacío para que cargue el modelo en memoria."""
        try:
            proc = subprocess.Popen(
                ["piper-tts", "--model", str(_MODEL_PATH), "--output-raw"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            proc.communicate(input=b" ", timeout=10)
            print("[Speaker][Linux] Piper precalentado.")
        except Exception:
            pass

    def _verificar_piper(self) -> bool:
        try:
            result = subprocess.run(
                ["piper-tts", "--version"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode != 0:
                return False
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

        if not _MODEL_PATH.exists():
            print(f"[Speaker][Linux] Modelo Piper no encontrado en: {_MODEL_PATH}")
            return False

        return True

    def _reproducir_con_aplay(self, audio_bytes: bytes):
        proc = subprocess.Popen(
            ["aplay", "--quiet", "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        proc.communicate(input=audio_bytes)

    def _decir_piper(self, texto: str):
        with self._lock:
            proc_piper = subprocess.Popen(
                ["piper-tts", "--model", str(_MODEL_PATH), "--output-raw"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            pcm_data, _ = proc_piper.communicate(input=texto.encode("utf-8"))

        if not pcm_data:
            return

        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(22050)
            wf.writeframes(pcm_data)

        self._reproducir_con_aplay(wav_buffer.getvalue())

    def _decir_espeak(self, texto: str):
        subprocess.run(
            ["espeak-ng", "-v", "es", "-s", "150", texto],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def decir(self, texto: str):
        if not texto or not texto.strip():
            return
        try:
            if self._piper_ok:
                self._decir_piper(texto.strip())
            else:
                self._decir_espeak(texto.strip())
        except Exception as e:
            print(f"[Speaker][Linux] Error TTS: {e}")

    def cerrar(self):
        pass


class Speaker:
    def __init__(self, rate: int = 175, volume: float = 1.0):
        if sys.platform == "win32":
            print("[Speaker] Backend: Windows (pyttsx3)")
            self._backend = _SpeakerWindows(rate=rate, volume=volume)
        else:
            print("[Speaker] Backend: Linux (Piper TTS)")
            self._backend = _SpeakerLinux(rate=rate, volume=volume)

    def decir(self, texto: str):
        self._backend.decir(texto)

    def cerrar(self):
        self._backend.cerrar()