# orion/audio/listener.py
import json
import queue
import re
import numpy as np
import soxr
import sounddevice as sd
from vosk import Model, KaldiRecognizer

_DEVICE_RATE = 44100
_VOSK_RATE   = 16000
_BLOCKSIZE   = int(_DEVICE_RATE * 0.125)  # ~125ms por bloque

_HOTWORDS = ["orion", "orión"]


class Listener:
    def __init__(self, model_path: str, sample_rate: int = 16000, device=None):
        self.model       = Model(model_path)
        self.sample_rate = _VOSK_RATE
        self.device      = device
        self._audio_queue: queue.Queue = queue.Queue()

        if device is not None:
            try:
                info = sd.query_devices(device)
                print(f"[Listener] Micrófono: {info['name']} (device={device}, hw_rate={_DEVICE_RATE}Hz → vosk={_VOSK_RATE}Hz)")
            except Exception:
                print(f"[Listener] Usando device={device}")
        else:
            print("[Listener] Usando dispositivo de audio por defecto")

    # ── Audio callback ────────────────────────────────────────────────────────

    def _callback(self, indata, frames, time_info, status):
        try:
            audio_f32   = indata[:, 0].copy()
            resampled   = soxr.resample(audio_f32, _DEVICE_RATE, _VOSK_RATE)
            audio_int16 = (resampled * 32767).astype(np.int16)
            self._audio_queue.put_nowait(audio_int16.tobytes())
        except Exception:
            pass

    def _clear_queue(self):
        while True:
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break

    # ── Motor base de escucha ─────────────────────────────────────────────────

    def _escuchar_con_recognizer(self, recognizer, segundos_max: int,
                                  max_silencio: int = 8) -> str:
        """
        max_silencio: bloques de silencio antes de cortar (~125ms cada uno)
        Por defecto 8 bloques = ~1s de silencio
        """
        self._clear_queue()
        partes: list[str] = []
        bloques_max      = int(segundos_max / 0.125) + 1
        bloques_silencio = 0

        try:
            with sd.InputStream(
                samplerate=_DEVICE_RATE,
                blocksize=_BLOCKSIZE,
                dtype="float32",
                channels=1,
                device=self.device,
                callback=self._callback,
            ):
                for _ in range(bloques_max):
                    try:
                        data = self._audio_queue.get(timeout=0.5)
                    except queue.Empty:
                        bloques_silencio += 1
                        if partes and bloques_silencio >= max_silencio:
                            break
                        continue

                    bloques_silencio = 0

                    if recognizer.AcceptWaveform(data):
                        result = json.loads(recognizer.Result())
                        texto  = (result.get("text") or "").strip()
                        if texto:
                            partes.append(texto)

                final = json.loads(recognizer.FinalResult())
                texto_final = (final.get("text") or "").strip()
                if texto_final:
                    partes.append(texto_final)

        except Exception as e:
            print(f"[Listener] Error de audio: {e}")
            return ""

        return _deduplicar(" ".join(partes).strip())

    # ── API pública ───────────────────────────────────────────────────────────

    def escuchar(self, segundos_max: int = 7) -> str:
        recognizer = KaldiRecognizer(self.model, self.sample_rate)
        return self._escuchar_con_recognizer(recognizer, segundos_max)

    def escuchar_hasta_texto(self, intentos: int = 3, segundos_por_intento: int = 6) -> str:
        for intento in range(intentos):
            texto = self.escuchar(segundos_max=segundos_por_intento)
            if texto and texto.strip():
                return texto.strip()
            print(f"[Listener] Intento {intento + 1}/{intentos}: sin texto, reintentando...")
        return ""

    def escuchar_con_gramatica(self, palabras_o_frases: list[str], segundos_max: int = 5) -> str:
        grammar_list = list(
            dict.fromkeys([p.strip().lower() for p in palabras_o_frases if p.strip()])
        )
        grammar_list.append("[unk]")
        grammar    = json.dumps(grammar_list, ensure_ascii=False)
        recognizer = KaldiRecognizer(self.model, self.sample_rate, grammar)
        return self._escuchar_con_recognizer(recognizer, segundos_max)

    def escuchar_hotword_y_comando(self, segundos_max: int = 8) -> tuple[bool, str]:
        """
        Escucha continua que detecta hotword + comando en una sola frase.
        Retorna (hotword_detectada, comando).

        Ejemplos:
          "Orion qué es la luna"  → (True, "qué es la luna")
          "Orion"                 → (True, "")
          "hola qué tal"          → (False, "")
        """
        recognizer = KaldiRecognizer(self.model, self.sample_rate)
        # Silencio corto para responder rápido: 6 bloques = ~0.75s
        texto = self._escuchar_con_recognizer(
            recognizer, segundos_max=segundos_max, max_silencio=6
        )

        if not texto:
            return False, ""

        texto_lower = texto.lower().strip()
        hotword_encontrada = any(hw in texto_lower for hw in _HOTWORDS)

        if not hotword_encontrada:
            return False, ""

        # Extraer el comando quitando la hotword del inicio
        comando = texto_lower
        for hw in _HOTWORDS:
            # Quitar hotword al inicio con posible coma/espacio
            comando = re.sub(
                r"^" + hw + r"[,\s]*", "", comando, flags=re.IGNORECASE
            ).strip()

        return True, comando


# ── Utilidades ────────────────────────────────────────────────────────────────

def _deduplicar(texto: str) -> str:
    palabras = texto.split()
    if not palabras:
        return texto
    resultado = [palabras[0]]
    for palabra in palabras[1:]:
        if palabra != resultado[-1]:
            resultado.append(palabra)
    return " ".join(resultado)