from orion.commands.base import BaseCommand, CommandResult
from orion.core.brain import limpiar_texto


class SystemControlCommand(BaseCommand):
    intent_name = "SYSTEM_CONTROL"

    def execute(self, context, text: str, payload: str, confidence: float) -> CommandResult:
        t = limpiar_texto(text)
        print(f"[DEBUG] SYSTEM_CONTROL texto_normalizado={t!r}")

        if "captura" in t or "screenshot" in t or "pantallazo" in t:
            ok, msg = context.sysctl.tomar_captura()
            print("[DEBUG] captura:", ok, msg)
            return CommandResult(
                success=ok,
                message="Listo. Tomé la captura." if ok else "No pude tomar la captura.",
                action="SCREENSHOT",
                payload=msg,
            )

        if ("sube" in t or "aumenta" in t or "mas volumen" in t) and "volumen" in t:
            ok, msg = context.sysctl.subir_volumen(delta=10)
            print("[DEBUG] subir_volumen:", ok, msg)
            return CommandResult(
                success=ok,
                message=msg if ok else "No pude subir el volumen.",
                action="VOLUME_UP",
                payload=msg,
            )

        if ("baja" in t or "reduce" in t or "menos volumen" in t) and "volumen" in t:
            ok, msg = context.sysctl.bajar_volumen(delta=10)
            print("[DEBUG] bajar_volumen:", ok, msg)
            return CommandResult(
                success=ok,
                message=msg if ok else "No pude bajar el volumen.",
                action="VOLUME_DOWN",
                payload=msg,
            )

        if (
            "quita silencio" in t
            or "quita el silencio" in t
            or "activa el sonido" in t
            or "unmute" in t
        ):
            ok, msg = context.sysctl.unmute()
            print("[DEBUG] unmute:", ok, msg)
            return CommandResult(
                success=ok,
                message=msg if ok else "No pude activar el sonido.",
                action="UNMUTE",
                payload=msg,
            )

        if "silencia" in t or "silencio" in t or "mute" in t or "sin sonido" in t:
            ok, msg = context.sysctl.mute()
            print("[DEBUG] mute:", ok, msg)
            return CommandResult(
                success=ok,
                message=msg if ok else "No pude silenciar.",
                action="MUTE",
                payload=msg,
            )

        return CommandResult(
            success=False,
            message="Entendí que quieres una acción del sistema, pero no reconocí cuál.",
            action="SYSTEM_CONTROL_NO_MATCH",
            payload=text,
        )