# orion/commands/web_search_command.py
import re
from orion.commands.base import BaseCommand, CommandResult


def _mejorar_query(payload: str, texto_original: str) -> str:
    """
    Reconstruye un query más útil combinando el payload con el texto original.
    El texto original tiene acentos y mayúsculas; el payload viene limpio/lowercase.
    """
    payload = (payload or "").strip()
    texto   = (texto_original or "").strip()

    if not payload:
        return texto

    # Extraer el tema del texto original preservando mayúsculas y acentos
    # Eliminar verbos de búsqueda comunes del inicio
    texto_limpio = re.sub(
        r"^(busca|buscar|búsca|dime|cuéntame|explícame|explicame|"
        r"qué es|que es|quién es|quien es|cómo es|como es|"
        r"qué fue|que fue|cuál es|cual es|cuánto vale|cuanto vale|"
        r"cuándo|cuando|dónde|donde|háblame de|hablame de)\s+",
        "", texto, flags=re.IGNORECASE
    ).strip()

    # Si el texto limpio es más informativo que el payload, usarlo
    if len(texto_limpio) >= len(payload):
        return texto_limpio

    return payload


class WebSearchCommand(BaseCommand):
    intent_name = "WEB_SEARCH"

    def execute(self, context, text: str, payload: str, confidence: float) -> CommandResult:
        tema = _mejorar_query(payload, text)
        print(f"[DEBUG] WEB tema={tema!r}")

        if not tema or len(tema) < 2:
            return CommandResult(
                success=False,
                message="No entendí bien qué quieres buscar.",
                action="WEB_SEARCH_INVALID",
                payload=payload,
            )

        texto, fuente = context.search_manager.buscar_con_fallback(tema)
        print("[DEBUG] web fuente:", fuente)
        print("[DEBUG] web texto:", (texto[:250] + "...") if texto else "")

        if not texto:
            return CommandResult(
                success=False,
                message="No encontré información sobre ese tema.",
                action="WEB_SEARCH_EMPTY",
                payload=tema,
            )

        resumen = context.search_manager.resumir_es(texto, max_chars=500)

        return CommandResult(
            success=True,
            message=resumen,
            action="WEB_SEARCH_OK",
            payload=tema,
        )