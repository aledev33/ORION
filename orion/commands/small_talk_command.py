from orion.commands.base import BaseCommand, CommandResult
from orion.core.brain import limpiar_texto


class SmallTalkCommand(BaseCommand):
    intent_name = "SMALL_TALK"

    def execute(self, context, text: str, payload: str, confidence: float) -> CommandResult:
        t = limpiar_texto(text)

        if any(k in t for k in ["hola", "buenos dias", "buenas tardes", "buenas noches", "que onda"]):
            return CommandResult(
                success=True,
                message="Hola, ¿qué necesitas?",
                action="SMALL_TALK_GREETING",
                payload="greeting",
            )

        if any(k in t for k in ["como estas", "como te va", "que tal"]):
            return CommandResult(
                success=True,
                message="Estoy bien. ¿Y tú?",
                action="SMALL_TALK_STATUS",
                payload="status",
            )

        if any(k in t for k in ["quien eres", "que eres"]):
            return CommandResult(
                success=True,
                message="Soy ORION, tu asistente de voz.",
                action="SMALL_TALK_IDENTITY",
                payload="identity",
            )


        if any(k in t for k in ["gracias", "muchas gracias", "te agradezco"]):
            return CommandResult(
                success=True,
                message="De nada.",
                action="SMALL_TALK_THANKS",
                payload="thanks",
            )

        if any(k in t for k in ["que puedes hacer", "que haces", "para que sirves"]):
            return CommandResult(
                success=True,
                message="Puedo abrir programas, controlar funciones del sistema y buscar información.",
                action="SMALL_TALK_CAPABILITIES",
                payload="capabilities",
            )

        return CommandResult(
            success=True,
            message="Aquí estoy. ¿En qué te ayudo?",
            action="SMALL_TALK_DEFAULT",
            payload="smalltalk",
        )