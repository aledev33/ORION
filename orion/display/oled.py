# orion/display/oled.py
#
# Pantalla OLED SSD1306 128x64 para ORION.
# Animaciones temáticas por estado.
# Fix: lock de estado para evitar conflicto con llamadas externas.

from __future__ import annotations

import math
import threading
import time
from enum import Enum, auto


class OrionEstado(Enum):
    INACTIVO       = auto()
    ESCUCHANDO     = auto()
    PROCESANDO     = auto()
    WEB_SEARCH     = auto()
    OPEN_APP       = auto()
    SYSTEM_CONTROL = auto()
    SMALL_TALK     = auto()
    HABLANDO       = auto()
    TAKE_PHOTO     = auto()
    ERROR          = auto()
    APAGANDO       = auto()


_INTENT_A_ESTADO = {
    "WEB_SEARCH":     OrionEstado.WEB_SEARCH,
    "OPEN_APP":       OrionEstado.OPEN_APP,
    "SYSTEM_CONTROL": OrionEstado.SYSTEM_CONTROL,
    "SMALL_TALK":     OrionEstado.SMALL_TALK,
    "TAKE_PHOTO":     OrionEstado.TAKE_PHOTO,
    "EXIT":           OrionEstado.APAGANDO,
    "UNKNOWN":        OrionEstado.ERROR,
    "LOW_CONFIDENCE": OrionEstado.ERROR,
}


class OrionDisplay:
    def __init__(self, i2c_address: int = 0x3C, i2c_port: int = 1):
        self._device      = None
        self._font_sm     = None
        self._font_md     = None
        self._lock        = threading.Lock()
        self._estado_actual = OrionEstado.INACTIVO
        self._frame       = 0
        self._anim_running = False
        self._anim_thread  = None
        self._reset_timer  = None
        self._locked_until = 0.0  # timestamp hasta cuando está bloqueado
        self._inicializar(i2c_address, i2c_port)

    def _inicializar(self, address, port):
        try:
            from luma.core.interface.serial import i2c
            from luma.oled.device import ssd1306
            from PIL import ImageFont

            serial = i2c(port=port, address=address)
            self._device = ssd1306(serial, width=128, height=64)

            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            try:
                self._font_sm = ImageFont.truetype(font_path, 9)
                self._font_md = ImageFont.truetype(font_path, 12)
            except Exception:
                self._font_sm = ImageFont.load_default()
                self._font_md = ImageFont.load_default()

            print("[Display] OLED inicializada.")
            self._anim_running = True
            self._anim_thread  = threading.Thread(target=self._loop, daemon=True)
            self._anim_thread.start()
            self.set_estado(OrionEstado.INACTIVO)

        except ImportError:
            print("[Display] luma.oled no instalado.")
        except Exception as e:
            print(f"[Display] Error: {e}")

    # ── Loop de animación ─────────────────────────────────────────────────────

    def _loop(self):
        while self._anim_running:
            if self._device:
                # Solo renderizar si no está bloqueado externamente
                if time.time() >= self._locked_until:
                    self._renderizar(self._estado_actual, self._frame)
                    self._frame += 1
            time.sleep(0.15)

    def _renderizar(self, estado, f):
        if not self._device:
            return
        try:
            from luma.core.render import canvas
            with self._lock:
                with canvas(self._device) as draw:
                    self._dibujar(draw, estado, f)
        except Exception as e:
            print(f"[Display] Render error: {e}")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _centro(self, draw, texto, y, font, fill="white"):
        bbox  = draw.textbbox((0, 0), texto, font=font)
        ancho = bbox[2] - bbox[0]
        x     = max(0, (128 - ancho) // 2)
        draw.text((x, y), texto, fill=fill, font=font)

    # ── Despachador ───────────────────────────────────────────────────────────

    def _dibujar(self, draw, estado, f):
        {
            OrionEstado.INACTIVO:       self._inactivo,
            OrionEstado.ESCUCHANDO:     self._escuchando,
            OrionEstado.PROCESANDO:     self._procesando,
            OrionEstado.WEB_SEARCH:     self._web_search,
            OrionEstado.OPEN_APP:       self._open_app,
            OrionEstado.SYSTEM_CONTROL: self._system_control,
            OrionEstado.SMALL_TALK:     self._small_talk,
            OrionEstado.HABLANDO:       self._hablando,
            OrionEstado.TAKE_PHOTO:     self._take_photo,
            OrionEstado.ERROR:          self._error,
            OrionEstado.APAGANDO:       self._apagando,
        }.get(estado, self._inactivo)(draw, f)

    # ── INACTIVO — carita durmiendo ───────────────────────────────────────────
    def _inactivo(self, draw, f):
        # Cara grande centrada
        cx, cy = 64, 28
        draw.ellipse([cx-20, cy-18, cx+20, cy+18], outline="white", width=2)
        # Ojos cerrados (líneas)
        draw.line([cx-10, cy-4, cx-4, cy-4], fill="white", width=2)
        draw.line([cx+4,  cy-4, cx+10, cy-4], fill="white", width=2)
        # Boca dormida
        draw.arc([cx-8, cy+4, cx+8, cy+14], 0, 180, fill="white", width=2)
        # ZZZ animado flotando
        z_y = 10 + int(math.sin(f * 0.15) * 3)
        draw.text((90, z_y),     "z",   fill="white", font=self._font_sm)
        draw.text((96, z_y - 6), "Z",   fill="white", font=self._font_md)
        draw.text((104, z_y-13), "Z",   fill="white", font=self._font_md)
        # Título
        self._centro(draw, "ORION", 54, self._font_sm)

    # ── ESCUCHANDO — ondas de sonido ──────────────────────────────────────────
    def _escuchando(self, draw, f):
        self._centro(draw, "Escuchando...", 2, self._font_sm)
        # Micrófono centrado
        cx, cy = 64, 28
        draw.rounded_rectangle([cx-6, cy-14, cx+6, cy+6], radius=6, outline="white", width=2)
        draw.line([cx, cy+6, cx, cy+14], fill="white", width=2)
        draw.arc([cx-10, cy+4, cx+10, cy+18], 0, 180, fill="white", width=2)
        # Ondas animadas
        r1 = 16 + int(math.sin(f * 0.4) * 3)
        r2 = 24 + int(math.sin(f * 0.4 + 1) * 3)
        draw.arc([cx-r1, cy-r1, cx+r1, cy+r1], -60, 60, fill="white", width=1)
        draw.arc([cx-r1, cy-r1, cx+r1, cy+r1], 120, 240, fill="white", width=1)
        draw.arc([cx-r2, cy-r2, cx+r2, cy+r2], -60, 60, fill="white", width=1)
        draw.arc([cx-r2, cy-r2, cx+r2, cy+r2], 120, 240, fill="white", width=1)

    # ── PROCESANDO — spinner de puntos ────────────────────────────────────────
    def _procesando(self, draw, f):
        self._centro(draw, "Procesando...", 2, self._font_sm)
        cx, cy = 64, 32
        r = 18
        for i in range(8):
            angle  = math.radians(i * 45 - f * 8)
            px     = int(cx + r * math.cos(angle))
            py     = int(cy + r * math.sin(angle))
            size   = 3 if i == 0 else (2 if i == 1 else 1)
            opacity = "white" if i < 3 else "white"
            draw.ellipse([px-size, py-size, px+size, py+size], fill=opacity)
        # Punto central pulsando
        ps = int(3 + math.sin(f * 0.3) * 2)
        draw.ellipse([cx-ps, cy-ps, cx+ps, cy+ps], outline="white", width=1)

    # ── WEB_SEARCH — globo terráqueo + cursor ────────────────────────────────
    def _web_search(self, draw, f):
        self._centro(draw, "Buscando...", 2, self._font_sm)
        cx, cy = 64, 34
        r = 20
        # Globo
        draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline="white", width=2)
        # Meridianos
        draw.ellipse([cx-r//2, cy-r, cx+r//2, cy+r], outline="white", width=1)
        # Ecuador
        draw.line([cx-r, cy, cx+r, cy], fill="white", width=1)
        # Cursor de búsqueda animado (gira alrededor del globo)
        angle = math.radians(f * 5)
        ex = int(cx + (r+6) * math.cos(angle))
        ey = int(cy + (r+6) * math.sin(angle))
        draw.ellipse([ex-3, ey-3, ex+3, ey+3], outline="white", width=2)
        draw.line([ex+2, ey+2, ex+6, ey+6], fill="white", width=2)

    # ── OPEN_APP — ventana con flechas ───────────────────────────────────────
    def _open_app(self, draw, f):
        self._centro(draw, "Abriendo app...", 2, self._font_sm)
        cx, cy = 64, 34
        # Ventana
        draw.rectangle([cx-22, cy-16, cx+22, cy+16], outline="white", width=2)
        draw.line([cx-22, cy-8, cx+22, cy-8], fill="white", width=1)
        # Puntos de la barra de título
        for i, x in enumerate([cx-16, cx-10, cx-4]):
            draw.ellipse([x-2, cy-13, x+2, cy-9], fill="white")
        # Flecha de lanzar animada
        offset = (f * 2) % 12
        arrow_y = cy + 4 - offset
        if cy - 8 <= arrow_y <= cy + 12:
            draw.polygon([
                (cx, arrow_y - 4),
                (cx - 5, arrow_y + 4),
                (cx + 5, arrow_y + 4),
            ], fill="white")

    # ── SYSTEM_CONTROL — engranaje girando ───────────────────────────────────
    def _system_control(self, draw, f):
        self._centro(draw, "Ejecutando...", 2, self._font_sm)
        cx, cy = 64, 34
        r_out, r_in = 18, 10
        dientes = 8
        angulo_base = math.radians(f * 4)
        # Dientes del engranaje
        puntos = []
        for i in range(dientes * 2):
            ang = angulo_base + math.radians(i * 360 / (dientes * 2))
            r   = r_out if i % 2 == 0 else r_out - 5
            puntos.append((int(cx + r * math.cos(ang)), int(cy + r * math.sin(ang))))
        if len(puntos) >= 3:
            draw.polygon(puntos, outline="white")
        # Centro del engranaje
        draw.ellipse([cx-r_in, cy-r_in, cx+r_in, cy+r_in], outline="white", width=2)
        # Punto central
        draw.ellipse([cx-3, cy-3, cx+3, cy+3], fill="white")

    # ── SMALL_TALK — carita hablando con burbuja ──────────────────────────────
    def _small_talk(self, draw, f):
        cx, cy = 45, 32
        # Cara
        draw.ellipse([cx-18, cy-18, cx+18, cy+18], outline="white", width=2)
        # Ojos alegres
        draw.ellipse([cx-9, cy-7, cx-3, cy-1], fill="white")
        draw.ellipse([cx+3, cy-7, cx+9, cy-1], fill="white")
        # Boca hablando (abre y cierra)
        boca_h = int(4 + math.sin(f * 0.4) * 4)
        draw.ellipse([cx-8, cy+4, cx+8, cy+4+boca_h], outline="white", width=2)
        # Burbuja de chat
        draw.rounded_rectangle([70, 14, 122, 42], radius=6, outline="white", width=2)
        # Puntos animados en la burbuja
        dot_idx = (f // 5) % 3
        for i, dx in enumerate([80, 92, 104]):
            if i <= dot_idx:
                draw.ellipse([dx-3, 25, dx+3, 31], fill="white")
        # Cola de la burbuja
        draw.polygon([(70, 35), (64, 42), (76, 42)], fill="white")

    # ── HABLANDO — ondas de audio ─────────────────────────────────────────────
    def _hablando(self, draw, f):
        self._centro(draw, "ORION", 2, self._font_sm)
        # Barras de ecualizador
        base_y = 56
        barras = 12
        ancho_b = 8
        espacio = 2
        total = barras * (ancho_b + espacio) - espacio
        x_start = (128 - total) // 2
        for i in range(barras):
            h = int(8 + 28 * abs(math.sin(f * 0.3 + i * 0.5)))
            x = x_start + i * (ancho_b + espacio)
            draw.rectangle([x, base_y - h, x + ancho_b, base_y], fill="white")

    # ── TAKE_PHOTO — cámara con cuenta regresiva ──────────────────────────────
    def _take_photo(self, draw, f):
        self._centro(draw, "Foto...", 2, self._font_sm)
        cx, cy = 64, 34
        # Cuerpo de la cámara
        draw.rounded_rectangle([cx-24, cy-12, cx+24, cy+14], radius=4, outline="white", width=2)
        # Lente
        draw.ellipse([cx-10, cy-8, cx+10, cy+8], outline="white", width=2)
        draw.ellipse([cx-6, cy-4, cx+6, cy+4], fill="white")
        # Flash
        draw.rectangle([cx+16, cy-14, cx+22, cy-10], fill="white")
        # Parpadeo animado
        if f % 10 < 5:
            draw.ellipse([cx-3, cy-3+2, cx+3, cy+3+2], outline="black", width=1)

    # ── ERROR — carita asustada ────────────────────────────────────────────────
    def _error(self, draw, f):
        # Pantalla invertida parpadeante
        if f % 8 < 4:
            draw.rectangle([0, 0, 127, 63], fill="white")
            fill = "black"
        else:
            fill = "white"
        cx, cy = 64, 28
        draw.ellipse([cx-20, cy-18, cx+20, cy+18], outline=fill, width=2)
        # Ojos asustados (X X)
        for ox in [cx-10, cx+4]:
            draw.line([ox, cy-8, ox+6, cy-2], fill=fill, width=2)
            draw.line([ox+6, cy-8, ox, cy-2], fill=fill, width=2)
        # Boca abierta asustada
        draw.ellipse([cx-8, cy+4, cx+8, cy+14], outline=fill, width=2)
        self._centro(draw, "No entendi", 54, self._font_sm)

    # ── APAGANDO ──────────────────────────────────────────────────────────────
    def _apagando(self, draw, f):
        # Ojos cerrándose
        fase = min(f // 2, 8)
        cx, cy = 64, 28
        draw.ellipse([cx-20, cy-18, cx+20, cy+18], outline="white", width=2)
        ojo_h = max(0, 6 - fase)
        if ojo_h > 0:
            draw.ellipse([cx-12, cy-5, cx-4, cy-5+ojo_h], fill="white")
            draw.ellipse([cx+4,  cy-5, cx+12, cy-5+ojo_h], fill="white")
        else:
            draw.line([cx-12, cy-2, cx-4, cy-2], fill="white", width=2)
            draw.line([cx+4,  cy-2, cx+12, cy-2], fill="white", width=2)
        draw.arc([cx-8, cy+4, cx+8, cy+12], 0, 180, fill="white", width=2)
        puntos = max(0, 5 - f // 3)
        self._centro(draw, "Bye" + "." * puntos, 54, self._font_sm)

    # ── API pública ───────────────────────────────────────────────────────────

    def set_estado(self, estado: OrionEstado, auto_reset_seg: float = 0, lock_seg: float = 0):
        self._estado_actual = estado
        self._frame = 0

        # Lock: bloquear el loop para que no pise este estado
        if lock_seg > 0:
            self._locked_until = time.time() + lock_seg

        if self._reset_timer:
            self._reset_timer.cancel()
            self._reset_timer = None

        if auto_reset_seg > 0:
            self._reset_timer = threading.Timer(
                auto_reset_seg, self.set_estado, args=(OrionEstado.INACTIVO,)
            )
            self._reset_timer.daemon = True
            self._reset_timer.start()

    def set_estado_por_intent(self, intent: str, auto_reset_seg: float = 0):
        estado = _INTENT_A_ESTADO.get(intent, OrionEstado.PROCESANDO)
        self.set_estado(estado, auto_reset_seg=auto_reset_seg)

    def apagar(self):
        self._anim_running = False
        if self._reset_timer:
            self._reset_timer.cancel()
        if self._device:
            try:
                self.set_estado(OrionEstado.APAGANDO)
                time.sleep(1.5)
                self._device.cleanup()
            except Exception:
                pass