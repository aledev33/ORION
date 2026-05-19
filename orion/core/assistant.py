# orion/core/assistant.py
#
# Nucleo de ORION Robot — modo headless para Raspberry Pi.
# Integra: Listener (Vosk), Speaker (Piper/espeak), Display (OLED),
#          SearchManager, SystemController, CommandRouter y ConversationLogger.

from __future__ import annotations

import sys

from orion.tts.speaker import Speaker
from orion.db.logger import ConversationLogger
from orion.nlu.classifier import IntentClassifier
from orion.core.brain import limpiar_texto, detectar_hotword, decidir_accion_ml
from orion.core.context import OrionContext
from orion.core.router import CommandRouter
from orion.system.controller import SystemController
from orion.web.search_manager import SearchManager
from orion.web.providers.wikipedia_provider import WikipediaProvider
from orion.web.providers.tavily_provider import TavilyProvider
from orion.web.providers.serper_provider import SerperProvider
from orion.web.providers.local_provider import LocalProvider
from orion.commands.registry import load_commands
from orion.commands.base import CommandResult
from orion.os_apps.app_matcher import refresh_catalogo
from orion.display.oled import OrionDisplay, OrionEstado
import orion.config as config


class OrionAssistant:
    def __init__(self, modo_dev: bool = False):
        """
        Args:
            modo_dev: Si True, no inicializa el Listener (no necesita microfono).
                      Usado por main_robot.py --dev para pruebas por teclado.
        """
        self._modo_dev = modo_dev

        # ── Listener (solo en modo produccion) ───────────────────────────────
        if not modo_dev:
            from orion.audio.listener import Listener
            listener = Listener(
                model_path=str(config.MODEL_PATH),
                sample_rate=config.LISTENER_SAMPLE_RATE,
                device=config.LISTENER_DEVICE,
            )
        else:
            listener = None

        # ── Speaker ───────────────────────────────────────────────────────────
        speaker = Speaker(rate=config.TTS_RATE, volume=config.TTS_VOLUME)

        # ── Logger ────────────────────────────────────────────────────────────
        logger = ConversationLogger(api_url=config.API_URL)

        # ── Control del sistema ───────────────────────────────────────────────
        sysctl = SystemController(screenshots_dir=str(config.SCREENSHOTS_DIR))

        # ── Busqueda web ──────────────────────────────────────────────────────
        search_manager = SearchManager([
            WikipediaProvider(),   # primero: gratuito, siempre en español
            TavilyProvider(),      # segundo: para clima, noticias, precios
            SerperProvider(),      # tercero: fallback general
            LocalProvider(),       # último: base de conocimiento local
        ])

        # ── Pantalla OLED ─────────────────────────────────────────────────────
        self.display = OrionDisplay(
            i2c_address=config.OLED_I2C_ADDRESS,
            i2c_port=config.OLED_I2C_PORT,
        )

        # ── Contexto compartido ───────────────────────────────────────────────
        self.context = OrionContext(
            listener=listener,
            speaker=speaker,
            logger=logger,
            sysctl=sysctl,
            search_manager=search_manager,
        )

        # ── Clasificador ML ───────────────────────────────────────────────────
        self.clf = IntentClassifier()

        # ── Comandos ──────────────────────────────────────────────────────────
        loaded_commands = load_commands()
        print("[DEBUG] Comandos cargados:", [c.__class__.__name__ for c in loaded_commands])
        self.router = CommandRouter(loaded_commands)

        # ── Catalogo de apps ──────────────────────────────────────────────────
        from orion.os_apps.app_matcher import _catalogo_cache
        if _catalogo_cache is None:
            refresh_catalogo()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def confidence_ok(self, intent: str, conf: float) -> bool:
        return conf >= config.INTENT_THRESHOLDS.get(intent, 0.65)

    # ── Procesamiento de texto ────────────────────────────────────────────────

    def process_text(self, comando: str, speak: bool = False) -> CommandResult:
        comando_limpio = limpiar_texto(comando)

        if len(comando_limpio) < 2:
            result = CommandResult(
                success=False,
                message="No entendi bien. Di algo mas claro.",
                action="COMMAND_TOO_SHORT",
                payload=comando,
            )
            self.context.logger.guardar(frase=comando, accion=result.action)
            self.display.set_estado(OrionEstado.ERROR, auto_reset_seg=3.0)
            if speak:
                self.context.speaker.decir(result.message)
            return result

        # Muestra PROCESANDO mientras clasifica el intent
        self.display.set_estado(OrionEstado.PROCESANDO)
        intent, payload, conf = decidir_accion_ml(comando, self.clf)
        print(f"[DEBUG] intent={intent} payload={payload!r} conf={conf:.2f}")

        if intent == "EXIT":
            result = CommandResult(
                success=True,
                message="Hasta luego.",
                action="EXIT",
                payload="",
            )
            self.context.logger.guardar(frase=comando, accion="EXIT")
            self.display.set_estado(OrionEstado.APAGANDO)
            if speak:
                self.context.speaker.decir(result.message)
            return result

        if intent == "UNKNOWN":
            result = CommandResult(
                success=False,
                message="No entendi. Puedes pedirme buscar algo, controlar el sistema o charlar.",
                action="UNKNOWN",
                payload=payload,
            )
            self.context.logger.guardar(
                frase=comando,
                accion=f"UNKNOWN|CONF:{conf:.2f}|PAYLOAD:{payload}",
            )
            self.display.set_estado(OrionEstado.ERROR, auto_reset_seg=3.0)
            if speak:
                self.context.speaker.decir(result.message)
            return result

        if not self.confidence_ok(intent, conf):
            result = CommandResult(
                success=False,
                message="No estoy seguro de lo que quieres. Puedes repetirlo mas claro.",
                action="LOW_CONFIDENCE",
                payload=payload,
            )
            self.context.logger.guardar(
                frase=comando,
                accion=f"LOW_CONFIDENCE|INTENT:{intent}|CONF:{conf:.2f}|PAYLOAD:{payload}",
            )
            self.display.set_estado(OrionEstado.ERROR, auto_reset_seg=3.0)
            if speak:
                self.context.speaker.decir(result.message)
            return result

        # Muestra el estado del intent mientras ejecuta el dispatch
        # sin auto_reset para que dure todo el tiempo que tarda el comando
        self.display.set_estado_por_intent(intent, auto_reset_seg=0)

        result = self.router.dispatch(
            context=self.context,
            intent=intent,
            payload=payload,
            text=comando,
            confidence=conf,
        )

        self.context.logger.guardar(
            frase=comando,
            accion=(
                f"{result.action}|OK:{result.success}|"
                f"INTENT:{intent}|CONF:{conf:.2f}|PAYLOAD:{result.payload}"
            ),
        )

        # Muestra HABLANDO mientras responde por voz
        # auto_reset vuelve a INACTIVO al terminar
        self.display.set_estado(OrionEstado.HABLANDO, auto_reset_seg=8.0)
        if speak:
            self.context.speaker.decir(result.message)

        return result

    # ── Loop principal (solo modo produccion) ─────────────────────────────────

    def run(self):
        """
        Loop principal de ORION en modo headless.
        Solo disponible en modo produccion (con microfono).
        """
        if self._modo_dev:
            raise RuntimeError("run() no esta disponible en modo dev. Usa process_text() directamente.")

        self.display.set_estado(OrionEstado.INACTIVO)
        self.context.speaker.decir("ORION iniciado. Di ORION para activarme.")
        print("ORION iniciado. (Ctrl+C o SIGTERM para salir)")

        try:
            while True:
                print("\n[Escuchando...]")
                self.display.set_estado(OrionEstado.INACTIVO)

                # Escucha continua — captura "Orion que es la luna" de una vez
                texto = self.context.listener.escuchar_hasta_texto(
                    intentos=1,
                    segundos_por_intento=config.LISTENER_HOTWORD_SECONDS + config.LISTENER_COMMAND_SECONDS,
                )
                print("[DEBUG] Oido:", texto)

                if not texto:
                    continue

                # Verificar si contiene la hotword
                texto_lower = texto.lower().strip()
                hotword_detectada = any(hw in texto_lower for hw in ["orion", "orion"])

                if not hotword_detectada:
                    continue

                # Extraer comando quitando la hotword y puntuacion
                import re
                comando = re.sub(r"^(orion)[,\s]+", "", texto_lower, flags=re.IGNORECASE).strip()
                print("[DEBUG] Hotword detectada. Comando:", comando)
                self.context.logger.guardar(frase=texto, accion="HOTWORD:DETECTADO")
                self.display.set_estado(OrionEstado.ESCUCHANDO)

                # Si no hay comando en la misma frase, pedir que lo diga
                if not comando or len(comando) < 2:
                    self.context.speaker.decir("Que necesitas?")
                    print("[Escuchando comando...]")
                    comando = self.context.listener.escuchar_hasta_texto(
                        intentos=config.LISTENER_COMMAND_ATTEMPTS,
                        segundos_por_intento=config.LISTENER_COMMAND_SECONDS,
                    )
                    print("[DEBUG] Oido (comando):", comando)

                if not comando:
                    self.display.set_estado(OrionEstado.ERROR, auto_reset_seg=2.0)
                    self.context.speaker.decir("No escuche el comando.")
                    continue

                result = self.process_text(comando, speak=True)

                if result.action == "EXIT":
                    break

        except KeyboardInterrupt:
            print("\nDetenido con Ctrl+C")
            try:
                self.context.speaker.decir("Detenido.")
            except Exception:
                pass
        finally:
            self.display.set_estado(OrionEstado.APAGANDO)
            try:
                self.context.speaker.cerrar()
            except Exception:
                pass
            self.display.apagar()