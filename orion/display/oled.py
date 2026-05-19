# orion/display/oled.py
#
# Módulo de pantalla OLED SSD1306 para ORION Robot.
# Cada estado tiene una animación visualmente distinta.
# Pantalla 128x64 monocromática (franja amarilla ~16px arriba, azul resto).
#
# Estados y su diseño visual:
#   INACTIVO       → cara durmiendo, ojos parpadeando lento, zZz flotante
#   ESCUCHANDO     → cara atenta, ondas de sonido animadas
#   PROCESANDO     → cara pensativa, spinner de puntos rotando
#   WEB_SEARCH     → cara curiosa, barra de progreso animada + lupa
#   OPEN_APP       → cara emocionada, flechas animadas apuntando arriba
#   SYSTEM_CONTROL → pantalla INVERTIDA, cara técnica, bordes parpadeando
#   SMALL_TALK     → cara feliz, corazones/estrellas flotando
#   HABLANDO       → cara con boca animada, ondas de audio laterales
#   ERROR          → pantalla INVERTIDA, cara asustada, X parpadeando
#   APAGANDO       → cara cerrando ojos gradualmente, fade de puntos

from __future__ import annotations

import threading
import time
import math
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
    ERROR          = auto()
    APAGANDO       = auto()


_INTENT_A_ESTADO = {
    "WEB_SEARCH":     OrionEstado.WEB_SEARCH,
    "OPEN_APP":       OrionEstado.OPEN_APP,
    "SYSTEM_CONTROL": OrionEstado.SYSTEM_CONTROL,
    "SMALL_TALK":     OrionEstado.SMALL_TALK,
    "EXIT":           OrionEstado.APAGANDO,
    "UNKNOWN":        OrionEstado.ERROR,
    "LOW_CONFIDENCE": OrionEstado.ERROR,
}

# Zona amarilla: filas 0-15 (header)
# Zona azul:    filas 16-63 (cara + animación)
_HEADER_Y   = 4    # y del texto en zona amarilla
_CARA_Y     = 22   # y base de la cara
_ANIM_Y     = 46   # y base de la animación


class OrionDisplay:
    """
    Controlador OLED SSD1306 con animaciones por estado.
    Tolerante a fallos: si no hay pantalla, ORION sigue funcionando.
    """

    def __init__(self, i2c_address: int = 0x3C, i2c_port: int = 1):
        self._device       = None
        self._font_sm      = None   # 9px — texto normal
        self._font_md      = None   # 12px — cara
        self._lock         = threading.Lock()
        self._estado_actual = OrionEstado.INACTIVO
        self._frame        = 0      # contador de frames para animaciones
        self._anim_thread  = None
        self._anim_running = False
        self._reset_timer  = None
        self._inicializar(i2c_address, i2c_port)

    # ─────────────────────────────────────────────────────────────────────────
    # Inicialización
    # ─────────────────────────────────────────────────────────────────────────

    def _inicializar(self, address: int, port: int):
        try:
            from luma.core.interface.serial import i2c
            from luma.oled.device import ssd1306
            from PIL import ImageFont

            serial = i2c(port=port, address=address)
            self._device = ssd1306(serial, width=128, height=64)

            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            try:
                self._font_sm = ImageFont.truetype(font_path, 9)
                self._font_md = ImageFont.truetype(font_path, 11)
            except Exception:
                self._font_sm = ImageFont.load_default()
                self._font_md = ImageFont.load_default()

            print("[Display] OLED SSD1306 inicializada.")
            self._iniciar_animacion()
            self.set_estado(OrionEstado.INACTIVO)

        except ImportError:
            print("[Display] luma.oled no instalado. OLED no disponible.")
        except Exception as e:
            print(f"[Display] No se pudo inicializar OLED: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # Loop de animación (hilo dedicado)
    # ─────────────────────────────────────────────────────────────────────────

    def _iniciar_animacion(self):
        self._anim_running = True
        self._anim_thread = threading.Thread(
            target=self._loop_animacion, daemon=True
        )
        self._anim_thread.start()

    def _loop_animacion(self):
        while self._anim_running:
            if self._device is not None:
                self._renderizar(self._estado_actual, self._frame)
                self._frame += 1
            time.sleep(0.18)   # ~5.5 fps — suave pero no agresivo

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers de dibujo
    # ─────────────────────────────────────────────────────────────────────────

    def _centrar_texto(self, draw, texto: str, y: int, font, fill="white"):
        bbox  = draw.textbbox((0, 0), texto, font=font)
        ancho = bbox[2] - bbox[0]
        x     = max(0, (128 - ancho) // 2)
        draw.text((x, y), texto, fill=fill, font=font)

    def _dibujar_cara(self, draw, ojo_izq: str, ojo_der: str,
                      boca: str, y_base: int, font, fill="white"):
        """Dibuja una cara estilo ASCII centrada."""
        cara = f"({ojo_izq}.{ojo_der})"
        self._centrar_texto(draw, cara, y_base, font, fill)
        self._centrar_texto(draw, boca, y_base + 13, font, fill)

    # ─────────────────────────────────────────────────────────────────────────
    # Renderizador por estado
    # ─────────────────────────────────────────────────────────────────────────

    def _renderizar(self, estado: OrionEstado, frame: int):
        if self._device is None:
            return
        try:
            from luma.core.render import canvas
            with self._lock:
                with canvas(self._device) as draw:
                    self._dibujar_estado(draw, estado, frame)
        except Exception as e:
            print(f"[Display] Error render: {e}")

    def _dibujar_estado(self, draw, estado: OrionEstado, f: int):
        """Despachador principal — cada estado tiene su propia función."""
        fn = {
            OrionEstado.INACTIVO:       self._estado_inactivo,
            OrionEstado.ESCUCHANDO:     self._estado_escuchando,
            OrionEstado.PROCESANDO:     self._estado_procesando,
            OrionEstado.WEB_SEARCH:     self._estado_web_search,
            OrionEstado.OPEN_APP:       self._estado_open_app,
            OrionEstado.SYSTEM_CONTROL: self._estado_system_control,
            OrionEstado.SMALL_TALK:     self._estado_small_talk,
            OrionEstado.HABLANDO:       self._estado_hablando,
            OrionEstado.ERROR:          self._estado_error,
            OrionEstado.APAGANDO:       self._estado_apagando,
        }.get(estado, self._estado_inactivo)
        fn(draw, f)

    # ── INACTIVO ─────────────────────────────────────────────────────────────
    # Cara durmiendo, ojos parpadeando muy lento, zZz flotando
    def _estado_inactivo(self, draw, f: int):
        self._centrar_texto(draw, "ORION", _HEADER_Y, self._font_sm)
        # Ojos: abiertos la mayoría del tiempo, cerrados cada 20 frames
        if f % 20 < 2:
            ojo = "—"
        else:
            ojo = "-"
        self._dibujar_cara(draw, ojo, ojo, "  ~~~  ", _CARA_Y, self._font_md)
        # zZz flotando (sube y baja)
        z_texts = ["z", "zZ", "zZz"]
        z_idx   = (f // 8) % 3
        z_y     = _ANIM_Y + int(math.sin(f * 0.3) * 3)
        self._centrar_texto(draw, z_texts[z_idx], z_y, self._font_sm)

    # ── ESCUCHANDO ───────────────────────────────────────────────────────────
    # Cara atenta, ondas de sonido animadas a los lados
    def _estado_escuchando(self, draw, f: int):
        self._centrar_texto(draw, "ORION", _HEADER_Y, self._font_sm)
        self._dibujar_cara(draw, "o", "o", " Escucho ", _CARA_Y, self._font_md)
        # Ondas de sonido: barras verticales que pulsan
        alturas = [3, 6, 9, 6, 3]
        base_y  = _ANIM_Y + 8
        x_start = 24
        for i, h_base in enumerate(alturas):
            h = h_base + int(math.sin(f * 0.4 + i * 0.7) * 3)
            x = x_start + i * 6
            draw.rectangle([x, base_y - h, x + 3, base_y], fill="white")
        # Lado derecho (espejo)
        x_start_r = 128 - 24 - 5 * 6
        for i, h_base in enumerate(alturas):
            h = h_base + int(math.sin(f * 0.4 + i * 0.7 + math.pi) * 3)
            x = x_start_r + i * 6
            draw.rectangle([x, base_y - h, x + 3, base_y], fill="white")

    # ── PROCESANDO ───────────────────────────────────────────────────────────
    # Cara pensativa, spinner de puntos orbitando
    def _estado_procesando(self, draw, f: int):
        self._centrar_texto(draw, "ORION", _HEADER_Y, self._font_sm)
        self._dibujar_cara(draw, "*", "*", " . . . ", _CARA_Y, self._font_md)
        # Spinner circular de 6 puntos
        cx, cy = 64, _ANIM_Y + 6
        r = 7
        for i in range(6):
            angle   = (f * 0.2 + i * math.pi / 3)
            px      = int(cx + r * math.cos(angle))
            py      = int(cy + r * math.sin(angle))
            # Los puntos más "adelante" son más grandes
            size = 2 if i == (f // 3) % 6 else 1
            draw.ellipse([px - size, py - size, px + size, py + size], fill="white")

    # ── WEB_SEARCH ───────────────────────────────────────────────────────────
    # Cara curiosa, barra de progreso corriendo + lupa
    def _estado_web_search(self, draw, f: int):
        self._centrar_texto(draw, "ORION", _HEADER_Y, self._font_sm)
        self._dibujar_cara(draw, "^", "^", "Buscando", _CARA_Y, self._font_md)
        # Barra de progreso animada
        bx, by = 10, _ANIM_Y + 4
        bw, bh = 108, 6
        draw.rectangle([bx, by, bx + bw, by + bh], outline="white")
        prog = (f * 4) % (bw + 20) - 10   # bloque que corre
        x1   = max(bx + 1, bx + prog)
        x2   = min(bx + bw - 1, bx + prog + 25)
        if x1 < x2:
            draw.rectangle([x1, by + 1, x2, by + bh - 1], fill="white")
        # Lupa pequeña a la derecha
        draw.ellipse([100, _ANIM_Y - 2, 112, _ANIM_Y + 10], outline="white")
        draw.line([111, _ANIM_Y + 9, 115, _ANIM_Y + 13], fill="white", width=2)

    # ── OPEN_APP ─────────────────────────────────────────────────────────────
    # Cara emocionada, flechas subiendo animadas
    def _estado_open_app(self, draw, f: int):
        self._centrar_texto(draw, "ORION", _HEADER_Y, self._font_sm)
        self._dibujar_cara(draw, ">", "<", "Abriendo", _CARA_Y, self._font_md)
        # 3 flechas subiendo con offset de fase
        for i, x in enumerate([30, 60, 90]):
            offset = (f * 2 + i * 8) % 18
            y      = _ANIM_Y + 12 - offset
            if _ANIM_Y <= y <= _ANIM_Y + 12:
                draw.text((x - 3, y), "^", fill="white", font=self._font_sm)

    # ── SYSTEM_CONTROL ───────────────────────────────────────────────────────
    # Pantalla INVERTIDA, cara técnica, bordes parpadeantes
    def _estado_system_control(self, draw, f: int):
        # Fondo blanco (invertido)
        draw.rectangle([0, 0, 127, 63], fill="white")
        self._centrar_texto(draw, "ORION", _HEADER_Y, self._font_sm, fill="black")
        # Cara en negro sobre blanco
        cara = "(#.#)"
        self._centrar_texto(draw, cara, _CARA_Y, self._font_md, fill="black")
        self._centrar_texto(draw, "SISTEMA", _CARA_Y + 13, self._font_sm, fill="black")
        # Bordes parpadeando
        if f % 6 < 3:
            draw.rectangle([0, 0, 127, 63], outline="black")
            draw.rectangle([2, 2, 125, 61], outline="black")
        # Texto técnico parpadeante
        if f % 4 < 2:
            draw.text((4, _ANIM_Y + 2), ">>>", fill="black", font=self._font_sm)
            draw.text((90, _ANIM_Y + 2), "<<<", fill="black", font=self._font_sm)

    # ── SMALL_TALK ───────────────────────────────────────────────────────────
    # Cara feliz, estrellas/destellos flotando
    def _estado_small_talk(self, draw, f: int):
        self._centrar_texto(draw, "ORION", _HEADER_Y, self._font_sm)
        # Boca alternando entre sonrisa y super-sonrisa
        boca = " \\___/ " if f % 10 < 5 else "  ~~~  "
        self._dibujar_cara(draw, "^", "^", boca, _CARA_Y, self._font_md)
        # Estrellitas flotando en 3 posiciones fijas con fase distinta
        estrellas = [(15, _ANIM_Y), (64, _ANIM_Y - 4), (110, _ANIM_Y)]
        simbolos  = ["*", "+", "*"]
        for i, (sx, sy) in enumerate(estrellas):
            fase = (f + i * 7) % 14
            if fase < 7:
                draw.text((sx, sy + fase // 2), simbolos[i],
                          fill="white", font=self._font_sm)

    # ── HABLANDO ─────────────────────────────────────────────────────────────
    # Cara con boca animada, ondas de audio a ambos lados
    def _estado_hablando(self, draw, f: int):
        self._centrar_texto(draw, "ORION", _HEADER_Y, self._font_sm)
        # Boca animada: abre y cierra
        bocas = [" ----- ", " ~---~ ", " ~~~~~ ", " ~---~ "]
        boca  = bocas[f % 4]
        self._dibujar_cara(draw, "o", "o", boca, _CARA_Y, self._font_md)
        # Ondas de audio simétricas más dinámicas que ESCUCHANDO
        base_y = _ANIM_Y + 9
        for i in range(7):
            h = int(4 + 5 * abs(math.sin(f * 0.5 + i * 0.5)))
            x = 10 + i * 6
            draw.rectangle([x, base_y - h, x + 4, base_y], fill="white")
        for i in range(7):
            h = int(4 + 5 * abs(math.sin(f * 0.5 + i * 0.5 + 1.0)))
            x = 128 - 14 - i * 6
            draw.rectangle([x, base_y - h, x + 4, base_y], fill="white")

    # ── ERROR ────────────────────────────────────────────────────────────────
    # Pantalla INVERTIDA, cara asustada, X parpadeando en esquinas
    def _estado_error(self, draw, f: int):
        draw.rectangle([0, 0, 127, 63], fill="white")
        self._centrar_texto(draw, "ORION", _HEADER_Y, self._font_sm, fill="black")
        self._dibujar_cara(draw, "x", "x", "No entendi", _CARA_Y, self._font_md, fill="black")
        # X parpadeante en las 4 esquinas
        if f % 4 < 2:
            for pos in [(2, 18), (118, 18), (2, 50), (118, 50)]:
                draw.text(pos, "X", fill="black", font=self._font_sm)

    # ── APAGANDO ─────────────────────────────────────────────────────────────
    # Ojos cerrándose gradualmente, puntos desvaneciéndose
    def _estado_apagando(self, draw, f: int):
        self._centrar_texto(draw, "ORION", _HEADER_Y, self._font_sm)
        # Ojos cerrándose: pasan de 'o' a '-' gradualmente
        ojos_seq = ["o", "o", "-", "-", "·", "·", " ", " "]
        ojo = ojos_seq[min(f // 3, len(ojos_seq) - 1)]
        self._dibujar_cara(draw, ojo, ojo, "  Bye...  ", _CARA_Y, self._font_md)
        # Puntos que se apagan uno a uno
        puntos_total = max(0, 5 - f // 4)
        texto_puntos = "· " * puntos_total
        self._centrar_texto(draw, texto_puntos, _ANIM_Y + 2, self._font_sm)

    # ─────────────────────────────────────────────────────────────────────────
    # API pública
    # ─────────────────────────────────────────────────────────────────────────

    def set_estado(self, estado: OrionEstado, auto_reset_seg: float = 0):
        self._estado_actual = estado
        self._frame = 0   # reinicia animación al cambiar estado

        if self._reset_timer is not None:
            self._reset_timer.cancel()
            self._reset_timer = None

        if auto_reset_seg > 0:
            self._reset_timer = threading.Timer(
                auto_reset_seg,
                self.set_estado,
                args=(OrionEstado.INACTIVO,),
            )
            self._reset_timer.daemon = True
            self._reset_timer.start()

    def set_estado_por_intent(self, intent: str, auto_reset_seg: float = 5.0):
        estado = _INTENT_A_ESTADO.get(intent, OrionEstado.PROCESANDO)
        self.set_estado(estado, auto_reset_seg=auto_reset_seg)

    def apagar(self):
        self._anim_running = False
        if self._reset_timer is not None:
            self._reset_timer.cancel()
        if self._device is not None:
            try:
                self.set_estado(OrionEstado.APAGANDO)
                time.sleep(1.5)
                self._device.cleanup()
            except Exception:
                pass