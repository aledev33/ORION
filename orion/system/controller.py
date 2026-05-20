# orion/system/controller.py
from __future__ import annotations
import os
import sys
import time
from pathlib import Path

_VOLUMEN_INICIAL = 60  # % al arrancar


def _get_volume_backend():
    if sys.platform == "win32":
        return _VolumeBackendWindows()
    else:
        return _VolumeBackendLinux()


class _VolumeBackendWindows:
    def __init__(self):
        from pycaw.pycaw import AudioUtilities
        device = AudioUtilities.GetSpeakers()
        self._volume = device.EndpointVolume
        self.set(_VOLUMEN_INICIAL)

    def get(self) -> int:
        return int(round(float(self._volume.GetMasterVolumeLevelScalar()) * 100))

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


class _VolumeBackendLinux:
    def __init__(self):
        self._pulse = None
        try:
            import pulsectl
            self._pulse = pulsectl.Pulse("orion")
            # Iniciar al 60%
            self.set(_VOLUMEN_INICIAL)
        except Exception as e:
            print(f"[SystemController] pulsectl no disponible: {e}")

    def _sink(self):
        if self._pulse is None:
            # Intentar reconectar
            try:
                import pulsectl
                self._pulse = pulsectl.Pulse("orion")
            except Exception as e:
                raise RuntimeError(f"pulsectl no disponible: {e}")
        try:
            sinks = self._pulse.sink_list()
        except Exception:
            # Reconectar si la conexión se perdió
            try:
                import pulsectl
                self._pulse = pulsectl.Pulse("orion")
                sinks = self._pulse.sink_list()
            except Exception as e:
                raise RuntimeError(f"No se pudo reconectar a PulseAudio: {e}")
        if not sinks:
            raise RuntimeError("No se encontro ningun sink de audio")
        return sinks[0]

    def get(self) -> int:
        try:
            sink = self._sink()
            return int(round(self._pulse.volume_get_all_chans(sink) * 100))
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
            self._pulse.mute(self._sink(), True)
            return True, "Silenciado"
        except Exception as e:
            return False, f"No pude silenciar: {e}"

    def unmute(self) -> tuple:
        try:
            self._pulse.mute(self._sink(), False)
            return True, "Sonido activado"
        except Exception as e:
            return False, f"No pude activar sonido: {e}"


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
                pyautogui.screenshot().save(path)
                return True, f"Captura guardada en {path}"
            else:
                import subprocess
                if not os.environ.get("DISPLAY", ""):
                    return False, "No hay pantalla disponible en modo headless"
                result = subprocess.run(["scrot", str(path)], capture_output=True)
                if result.returncode == 0:
                    return True, f"Captura guardada en {path}"
                return False, "scrot falló"
        except Exception as e:
            return False, f"No pude tomar captura: {e}"

    def obtener_volumen(self) -> int:
        return self._vol.get()

    def set_volumen(self, porcentaje: int) -> tuple:
        return self._vol.set(porcentaje)

    def subir_volumen(self, delta: int = 20) -> tuple:
        actual = self.obtener_volumen()
        nuevo  = min(100, actual + delta)
        ok, msg = self.set_volumen(nuevo)
        return ok, f"Volumen al {nuevo}%." if ok else msg

    def bajar_volumen(self, delta: int = 20) -> tuple:
        actual = self.obtener_volumen()
        nuevo  = max(0, actual - delta)
        ok, msg = self.set_volumen(nuevo)
        return ok, f"Volumen al {nuevo}%." if ok else msg

    def mute(self) -> tuple:
        return self._vol.mute()

    def unmute(self) -> tuple:
        return self._vol.unmute()