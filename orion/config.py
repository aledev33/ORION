# orion/config.py
#
# Configuración central de ORION.
# Válido tanto para laptop (desarrollo/GUI) como para Raspberry Pi (producción).
#
# API_URL es dinámico:
#   - En la RPi siempre apunta a localhost (la API corre en la misma máquina).
#   - En la laptop apunta a la IP Tailscale de la RPi (variable ORION_API_URL en .env).
#   - Si ORION_API_URL no está definido, fallback a localhost (desarrollo local).

import os
import sys
from pathlib import Path

# ── Rutas ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT    = Path(__file__).resolve().parent.parent
MODEL_PATH      = PROJECT_ROOT / "models" / "vosk-es"
SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"

# ── API URL dinámica ───────────────────────────────────────────────────────────
# En RPi:    ORION_API_URL no se define → usa localhost automáticamente.
# En laptop: definir en .env → ORION_API_URL=http://100.x.x.x:8000
#            (IP Tailscale de la RPi, siempre la misma sin importar la red)
API_URL = os.getenv("ORION_API_URL", "http://127.0.0.1:8000")

# ── Hotword ───────────────────────────────────────────────────────────────────
HOTWORD_OPTIONS = ["orion", "orión"]

# ── Umbrales de confianza por intent ─────────────────────────────────────────
INTENT_THRESHOLDS = {
    "OPEN_APP":       0.55,
    "WEB_SEARCH":     0.60,
    "SYSTEM_CONTROL": 0.70,
    "SMALL_TALK":     0.30,
    "UNKNOWN":        1.00,
}

# ── Listener (Vosk / audio) ───────────────────────────────────────────────────
LISTENER_SAMPLE_RATE = 16000

def _detectar_microfono() -> int:
    """
    Detecta automáticamente el micrófono USB disponible.
    Si hay dos conectados, prioriza el último (diadema recién conectada).
    Si no hay ninguno, devuelve 2 como fallback.
    """
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        microfonos_usb = []
        for i, d in enumerate(devices):
            if d['max_input_channels'] > 0:
                nombre = d['name'].lower()
                if 'usb' in nombre or 'pnp' in nombre or 'audio' in nombre:
                    microfonos_usb.append(i)
        if microfonos_usb:
            # Tomar el último — si hay diadema conectada, aparece después
            device = microfonos_usb[-1]
            try:
                nombre = sd.query_devices(device)['name']
                print(f"[Config] Micrófono seleccionado: {nombre} (device={device})")
            except Exception:
                pass
            return device
    except Exception as e:
        print(f"[Config] Error detectando micrófono: {e}")
    return 2  # fallback

LISTENER_DEVICE = _detectar_microfono()

# Tiempo máximo esperando la hotword "ORION" (segundos).
LISTENER_HOTWORD_SECONDS = 4

# Intentos para capturar el comando tras detectar hotword.
LISTENER_COMMAND_ATTEMPTS = 3

# Tiempo máximo por intento de captura de comando.
# 7s permite frases largas como "busca información sobre el clima en Guadalajara".
LISTENER_COMMAND_SECONDS = 7

# ── TTS ───────────────────────────────────────────────────────────────────────
# rate: usado por el backend Windows (pyttsx3).
# Piper (Linux/RPi) controla la velocidad desde el modelo .onnx.
TTS_RATE   = 175
TTS_VOLUME = 1.0

# ── Apps ──────────────────────────────────────────────────────────────────────
APP_MIN_PAYLOAD_LEN = 3
APP_MATCH_THRESHOLD = 0.72

# ── Idioma de respuestas de búsqueda web ──────────────────────────────────────
# "es" → español  |  "en" → inglés
RESPONSE_LANGUAGE = "es"

# ── Pantalla OLED SSD1306 (solo Raspberry Pi) ─────────────────────────────────
# Dirección I2C de la pantalla. Verificar con: sudo i2cdetect -y 1
# Los valores típicos son 0x3C o 0x3D.
OLED_I2C_ADDRESS = 0x3C
OLED_I2C_PORT    = 1     # Siempre 1 en Raspberry Pi 4

# ── Detección de plataforma ───────────────────────────────────────────────────
# Usado internamente por módulos que necesitan comportamiento diferente
# entre laptop (Windows, desarrollo) y RPi (Linux, producción).
IS_RASPBERRY_PI = sys.platform != "win32"