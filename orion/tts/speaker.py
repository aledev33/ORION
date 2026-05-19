# orion/tts/speaker.py
#
# TTS multiplataforma para ORION.
# Detecta el sistema operativo automáticamente y usa el backend correcto:
#   Windows  → pyttsx3 (SAPI5, sin dependencias extra)
#   Linux    → Piper TTS (offline, voz natural) con fallback a espeak-ng
#
# En Raspberry Pi el backend Linux usa Piper.
# En laptop Windows el backend Windows usa pyttsx3 igual que antes.

from __future__ import annotations

import io
import os
import subprocess
import sys
import wave
from pathlib import Path


# ── Ruta al modelo Piper (solo Linux/RPi) ────────────────────────────────────
_DEFAULT_MODEL = Path.home() / "piper-voices" / "es_MX-claude-high.onnx"
_MODEL_PATH    = Path(os.getenv("PIPER_MODEL_PATH", str(_DEFAULT_MODEL)))


# =============================================================================
# Backend Windows — pyttsx3 / SAPI5
# =============================================================================

class _SpeakerWindows:
    """
    Backend TTS para Windows usando pyttsx3 (SAPI5).
    Crea un engine nuevo por cada decir() para evitar
    el error 'run loop already started' en loops.
    """

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


# =============================================================================
# Backend Linux — Piper TTS con fallback a espeak-ng
# =============================================================================

class _SpeakerLinux:
    """
    Backend TTS para Linux / Raspberry Pi usando Piper.
    Si Piper no está disponible, cae a espeak-ng como último recurso.
    """

    def __init__(self, rate: int, volume: float):
        self.rate      = rate
        self.volume    = volume
        self._piper_ok = self._verificar_piper()

        if not self._piper_ok:
            print(
                "[Speaker][Linux] Piper no disponible. "
                "Usando espeak-ng como fallback.\n"
                "  → Instalar Piper: ver orion/tts/speaker.py para instrucciones."
            )

    # ── Verificación ──────────────────────────────────────────────────────────

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
            print(
                f"[Speaker][Linux] Modelo Piper no encontrado en: {_MODEL_PATH}\n"
                f"  Descárgalo con:\n"
                f"  mkdir -p ~/piper-voices\n"
                f"  wget -P ~/piper-voices https://huggingface.co/rhasspy/piper-voices"
                f"/resolve/v1.0.0/es/es_MX/claude/high/es_MX-claude-high.onnx?download=true\n"
                f"  wget -P ~/piper-voices https://huggingface.co/rhasspy/piper-voices"
                f"/resolve/v1.0.0/es/es_MX/claude/high/es_MX-claude-high.onnx.json?download=true"
            )
            return False

        return True

    # ── Reproducción ──────────────────────────────────────────────────────────

    def _reproducir_con_aplay(self, audio_bytes: bytes):
        """Reproduce bytes WAV directamente con aplay (sin archivo temporal)."""
        proc = subprocess.Popen(
            ["aplay", "--quiet", "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        proc.communicate(input=audio_bytes)

    def _decir_piper(self, texto: str):
        """Genera audio con Piper y lo reproduce con aplay."""
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
        """Fallback: espeak-ng."""
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


# =============================================================================
# Speaker — interfaz pública (el resto del proyecto no cambia)
# =============================================================================

class Speaker:
    """
    Interfaz única de TTS para ORION.
    Selecciona el backend correcto según el sistema operativo en tiempo de
    inicialización. El resto del proyecto solo llama a decir() y cerrar().
    """

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