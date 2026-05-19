# orion/system/controller.py
#
# Controlador del sistema para ORION.
# Maneja screenshots y volumen de forma multiplataforma.
#
#   Windows -> pyautogui (screenshot) + pycaw (volumen)
#   Linux   -> scrot (screenshot)     + pulsectl (volumen)
#
# Todos los imports de hardware se hacen dentro de sus funciones
# para que fallen silenciosamente si el hardware no esta disponible.

from __future__ import annotations

import os
import sys
import time
from pathlib import Path


def _get_volume_backend():
    if sys.platform == "win32":
        return _VolumeBackendWindows()
    else:
        return _VolumeBackendLinux()


# =============================================================================
# Backend Windows — pycaw
# =============================================================================

class _VolumeBackendWindows:
    def __init__(self):
        from pycaw.pycaw import AudioUtilities
        device = AudioUtilities.GetSpeakers()
        self._volume = device.EndpointVolume

    def get(self) -> int:
        scalar = float(self._volume.GetMasterVolumeLevelScalar())
        return int(round(scalar * 100))

    def set(self, porcentaje: int) -> tuple:
        try:
            p = max(0, min(100, int(porcentaje)))
            self._volume.SetMasterVolumeLevelScalar(p / 100.0, None)
            return True, f"Volumen al {p}%"
        except Exception as e:
            return False, f"No pude ajustar volumen: {e}"

    def mute(self) -> tuple:
        try:
            self._volume.SetMute(1, None)
            return True, "Silenciado"
        except Exception as e:
            return False, f"No pude silenciar: {e}"

    def unmute(self) -> tuple:
        try:
            self._volume.SetMute(0, None)
            return True, "Sonido activado"
        except Exception as e:
            return False, f"No pude activar sonido: {e}"


# =============================================================================
# Backend Linux — pulsectl
# =============================================================================

class _VolumeBackendLinux:
    def __init__(self):
        self._pulse = None
        try:
            import pulsectl
            self._pulse = pulsectl.Pulse("orion")
        except Exception as e:
            print(f"[SystemController] pulsectl no disponible: {e}")
            print("                   Control de volumen desactivado.")

    def _sink(self):
        if self._pulse is None:
            raise RuntimeError("pulsectl no inicializado")
        sinks = self._pulse.sink_list()
        if not sinks:
            raise RuntimeError("No se encontro ningun sink de audio")
        return sinks[0]

    def get(self) -> int:
        try:
            sink = self._sink()
            vol = self._pulse.volume_get_all_chans(sink)
            return int(round(vol * 100))
        except Exception:
            return 0

    def set(self, porcentaje: int) -> tuple:
        try:
            p = max(0, min(100, int(porcentaje)))
            sink = self._sink()
            self._pulse.volume_set_all_chans(sink, p / 100.0)
            return True, f"Volumen al {p}%"
        except Exception as e:
            return False, f"No pude ajustar volumen: {e}"

    def mute(self) -> tuple:
        try:
            sink = self._sink()
            self._pulse.mute(sink, True)
            return True, "Silenciado"
        except Exception as e:
            return False, f"No pude silenciar: {e}"

    def unmute(self) -> tuple:
        try:
            sink = self._sink()
            self._pulse.mute(sink, False)
            return True, "Sonido activado"
        except Exception as e:
            return False, f"No pude activar sonido: {e}"


# =============================================================================
# SystemController — interfaz publica
# =============================================================================

class SystemController:
    def __init__(self, screenshots_dir: str = "screenshots"):
        self.screenshots_dir = Path(screenshots_dir)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self._vol = _get_volume_backend()

    def tomar_captura(self) -> tuple:
        try:
            ts   = time.strftime("%Y%m%d-%H%M%S")
            path = self.screenshots_dir / f"screenshot_{ts}.png"

            if sys.platform == "win32":
                import pyautogui
                img = pyautogui.screenshot()
                img.save(path)
                return True, f"Captura guardada en {path}"
            else:
                import subprocess
                display = os.environ.get("DISPLAY", "")
                if not display:
                    return False, "No hay pantalla disponible para captura en modo headless"
                result = subprocess.run(["scrot", str(path)], capture_output=True)
                if result.returncode == 0:
                    return True, f"Captura guardada en {path}"
                else:
                    return False, "scrot fallo. Instalar con: sudo apt install scrot"

        except Exception as e:
            return False, f"No pude tomar captura: {e}"

    def obtener_volumen(self) -> int:
        return self._vol.get()

    def set_volumen(self, porcentaje: int) -> tuple:
        return self._vol.set(porcentaje)

    def subir_volumen(self, delta: int = 10) -> tuple:
        actual = self.obtener_volumen()
        return self.set_volumen(actual + delta)

    def bajar_volumen(self, delta: int = 10) -> tuple:
        actual = self.obtener_volumen()
        return self.set_volumen(actual - delta)

    def mute(self) -> tuple:
        return self._vol.mute()

    def unmute(self) -> tuple:
        return self._vol.unmute()