from orion.core.assistant import OrionAssistant
from orion.core.brain import limpiar_texto, decidir_accion_ml
from orion.commands.base import CommandResult
import orion.config as config


class KeyboardListener:
    """
    Listener falso para modo texto.
    Sirve sobre todo para las confirmaciones con gramática cerrada
    que algunos comandos ya usan.
    """

    def escuchar_con_gramatica(self, grammar_options, segundos_max=4):
        if grammar_options:
            print("\n[GRAMÁTICA DISPONIBLE]")
            print(", ".join(grammar_options[:30]))
            if len(grammar_options) > 30:
                print(f"... y {len(grammar_options) - 30} más")
        return input("Confirmación (texto): ").strip()

    def escuchar_hasta_texto(self, intentos=1, segundos_por_intento=5):
        return input("Comando (texto): ").strip()


class SilentSpeaker:
    """
    Speaker silencioso para no depender del TTS.
    Imprime el mensaje en consola en vez de hablar.
    """

    def decir(self, mensaje: str):
        print(f"ORION> {mensaje}")

    def cerrar(self):
        pass


class OrionTextAssistant(OrionAssistant):
    def __init__(self):
        super().__init__()
        self.context.listener = KeyboardListener()
        self.context.speaker = SilentSpeaker()

    def run_text(self):
        self.context.speaker.decir("Modo texto iniciado.")
        self.context.speaker.decir(
            "Escribe tu comando. Usa '/salir' para terminar y '/help' para ayuda."
        )
        print("ORION texto iniciado. (/salir para terminar)")

        try:
            while True:
                comando = input("\nTÚ> ").strip()

                if not comando:
                    continue

                comando_limpio = limpiar_texto(comando)

                if comando_limpio in ["/salir", "salir", "exit", "termina", "adios"]:
                    self.context.logger.guardar(frase=comando, accion="EXIT_TEXT")
                    self.context.speaker.decir("Saliendo del modo texto. Hasta luego.")
                    break

                if comando_limpio in ["/help", "help", "ayuda"]:
                    print(
                        "\nEjemplos:\n"
                        "  abre chrome\n"
                        "  abre discord\n"
                        "  abre navegador\n"
                        "  abre worth\n"
                        "  que es machine learning\n"
                        "  busca redes neuronales\n"
                        "  sube el volumen\n"
                        "  toma una captura\n"
                        "  quien eres\n"
                    )
                    continue

                if len(comando_limpio) < 2:
                    self.context.logger.guardar(
                        frase=comando,
                        accion="COMANDO_TEXTO:DEMASIADO_CORTO",
                    )
                    self.context.speaker.decir("Escribe un poco más para entenderte mejor.")
                    continue

                intent, payload, conf = decidir_accion_ml(comando, self.clf)
                print(f"[DEBUG] intent={intent} payload={payload!r} conf={conf:.2f}")

                if intent == "EXIT":
                    self.context.logger.guardar(frase=comando, accion="EXIT")
                    self.context.speaker.decir("Saliendo. Hasta luego.")
                    break

                if intent == "UNKNOWN":
                    self.context.logger.guardar(
                        frase=comando,
                        accion=f"UNKNOWN_TEXT|CONF:{conf:.2f}|PAYLOAD:{payload}",
                    )
                    self.context.speaker.decir(
                        "No entendí. Intenta con abrir app, búsqueda web, acción del sistema o small talk."
                    )
                    continue

                if not self.confidence_ok(intent, conf):
                    self.context.logger.guardar(
                        frase=comando,
                        accion=f"LOW_CONFIDENCE_TEXT|INTENT:{intent}|CONF:{conf:.2f}|PAYLOAD:{payload}",
                    )
                    self.context.speaker.decir(
                        "No estoy seguro de lo que quieres. Escríbelo de otra forma."
                    )
                    continue

                result: CommandResult = self.router.dispatch(
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

                self.context.speaker.decir(result.message)

        except KeyboardInterrupt:
            print("\nDetenido con Ctrl+C")
        finally:
            try:
                self.context.speaker.cerrar()
            except Exception:
                pass


def main():
    assistant = OrionTextAssistant()
    assistant.run_text()


if __name__ == "__main__":
    main()