# orion/commands/small_talk_command.py
import random
from orion.commands.base import BaseCommand, CommandResult
from orion.core.brain import limpiar_texto


class SmallTalkCommand(BaseCommand):
    intent_name = "SMALL_TALK"

    def execute(self, context, text: str, payload: str, confidence: float) -> CommandResult:
        t = limpiar_texto(text)

        # ── Saludos ───────────────────────────────────────────────────────────
        if any(k in t for k in [
            "hola", "buenos dias", "buenas tardes", "buenas noches",
            "que onda", "que tal", "como estas", "como te va",
            "buenas", "hey", "ey", "saludos", "buen dia"
        ]):
            respuestas = [
                "Hola, ¿qué necesitas?",
                "¡Hola! Aquí estoy para ayudarte.",
                "¡Buenas! ¿En qué te puedo ayudar?",
                "Hola, dime, ¿qué necesitas?",
                "¡Hey! ¿Cómo te puedo ayudar hoy?",
            ]
            return CommandResult(
                success=True,
                message=random.choice(respuestas),
                action="SMALL_TALK_GREETING",
                payload="greeting",
            )

        # ── Estado de ORION ───────────────────────────────────────────────────
        if any(k in t for k in [
            "como estas", "como te va", "que tal", "como andas",
            "todo bien", "como te encuentras", "estas bien"
        ]):
            respuestas = [
                "Estoy bien, gracias. ¿Y tú?",
                "Todo en orden por aquí. ¿En qué te ayudo?",
                "Funcionando perfectamente. ¿Qué necesitas?",
                "Muy bien, listo para ayudarte.",
            ]
            return CommandResult(
                success=True,
                message=random.choice(respuestas),
                action="SMALL_TALK_STATUS",
                payload="status",
            )

        # ── Identidad ─────────────────────────────────────────────────────────
        if any(k in t for k in [
            "quien eres", "que eres", "como te llamas", "cual es tu nombre",
            "presentate", "quien soy", "tu nombre"
        ]):
            respuestas = [
                "Soy ORION, tu asistente de voz inteligente.",
                "Me llamo ORION. Soy un asistente de voz desarrollado en el CUCEI.",
                "Soy ORION, estoy aquí para ayudarte con búsquedas, apps y control del sistema.",
            ]
            return CommandResult(
                success=True,
                message=random.choice(respuestas),
                action="SMALL_TALK_IDENTITY",
                payload="identity",
            )

        # ── Capacidades ───────────────────────────────────────────────────────
        if any(k in t for k in [
            "que puedes hacer", "que haces", "para que sirves",
            "que sabes hacer", "cuales son tus funciones", "que puedes",
            "ayudame con", "como me ayudas"
        ]):
            return CommandResult(
                success=True,
                message="Puedo buscar información en internet, abrir aplicaciones en tu computadora, controlar el sistema, tomar fotos y mucho más. Solo pídelo.",
                action="SMALL_TALK_CAPABILITIES",
                payload="capabilities",
            )

        # ── Agradecimientos ───────────────────────────────────────────────────
        if any(k in t for k in [
            "gracias", "muchas gracias", "te agradezco", "mil gracias",
            "muy amable", "genial", "excelente", "perfecto", "bien hecho"
        ]):
            respuestas = [
                "De nada, para eso estoy.",
                "Con gusto.",
                "No hay de qué.",
                "Siempre a tus órdenes.",
                "Para eso estoy aquí.",
            ]
            return CommandResult(
                success=True,
                message=random.choice(respuestas),
                action="SMALL_TALK_THANKS",
                payload="thanks",
            )

        # ── Despedidas ────────────────────────────────────────────────────────
        if any(k in t for k in [
            "adios", "hasta luego", "nos vemos", "chao", "bye",
            "hasta pronto", "me voy", "hasta manana"
        ]):
            respuestas = [
                "¡Hasta luego!",
                "¡Hasta pronto!",
                "Nos vemos. Aquí estaré cuando me necesites.",
                "¡Cuídate!",
            ]
            return CommandResult(
                success=True,
                message=random.choice(respuestas),
                action="SMALL_TALK_BYE",
                payload="bye",
            )

        # ── Chistes ───────────────────────────────────────────────────────────
        if any(k in t for k in [
            "cuéntame un chiste", "cuentame un chiste", "dime un chiste",
            "un chiste", "hazme reir", "algo gracioso"
        ]):
            chistes = [
                "¿Por qué los programadores confunden Halloween con Navidad? Porque Oct 31 es igual a Dec 25.",
                "¿Qué le dijo un bit al otro? Nos vemos en el bus.",
                "¿Por qué el robot fue al médico? Porque tenía un virus.",
                "¿Cómo se despide un informático? Con un byte.",
            ]
            return CommandResult(
                success=True,
                message=random.choice(chistes),
                action="SMALL_TALK_JOKE",
                payload="joke",
            )

        # ── Hora y fecha ──────────────────────────────────────────────────────
        if any(k in t for k in [
            "que hora es", "dime la hora", "hora actual",
            "que dia es", "que fecha es", "fecha de hoy"
        ]):
            from datetime import datetime
            now = datetime.now()
            if "hora" in t:
                msg = f"Son las {now.strftime('%I:%M %p')}."
            else:
                dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
                meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                         "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
                msg = f"Hoy es {dias[now.weekday()]}, {now.day} de {meses[now.month-1]} de {now.year}."
            return CommandResult(
                success=True,
                message=msg,
                action="SMALL_TALK_DATETIME",
                payload="datetime",
            )

        # ── Preguntas personales ───────────────────────────────────────────────
        if any(k in t for k in [
            "cuantos anos tienes", "que edad tienes", "cuando naciste"
        ]):
            return CommandResult(
                success=True,
                message="Soy un programa, no tengo edad. Pero fui creado en 2026.",
                action="SMALL_TALK_AGE",
                payload="age",
            )

        if any(k in t for k in [
            "eres inteligente", "eres listo", "eres bueno"
        ]):
            respuestas = [
                "Hago lo que puedo con lo que me dieron.",
                "Intento serlo. ¿En qué te ayudo?",
                "Gracias, aunque sigo aprendiendo.",
            ]
            return CommandResult(
                success=True,
                message=random.choice(respuestas),
                action="SMALL_TALK_COMPLIMENT",
                payload="compliment",
            )

        if any(k in t for k in [
            "te gusta", "tienes favorito", "prefieres"
        ]):
            return CommandResult(
                success=True,
                message="Soy un asistente, no tengo preferencias. Pero me gusta ayudarte.",
                action="SMALL_TALK_PREFERENCE",
                payload="preference",
            )

        if any(k in t for k in [
            "cuentame algo", "dime algo", "algo interesante", "sabias que"
        ]):
            datos = [
                "¿Sabías que el primer bug de computadora fue literalmente un insecto? Una polilla atrapada en el Harvard Mark II en 1947.",
                "¿Sabías que Python fue nombrado por Monty Python, no por la serpiente?",
                "¿Sabías que el primer mensaje enviado por internet fue 'lo'. Se intentó escribir 'login' pero el sistema colapsó.",
                "¿Sabías que hay más posibles partidas de ajedrez que átomos en el universo observable?",
            ]
            return CommandResult(
                success=True,
                message=random.choice(datos),
                action="SMALL_TALK_FACT",
                payload="fact",
            )

        # ── Default ───────────────────────────────────────────────────────────
        respuestas_default = [
            "Aquí estoy. ¿En qué te ayudo?",
            "Dime, ¿qué necesitas?",
            "Te escucho. ¿Qué puedo hacer por ti?",
            "Estoy listo. ¿Qué necesitas?",
        ]
        return CommandResult(
            success=True,
            message=random.choice(respuestas_default),
            action="SMALL_TALK_DEFAULT",
            payload="smalltalk",
        )