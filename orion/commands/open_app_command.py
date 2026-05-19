# orion/commands/open_app_command.py
#
# Comando OPEN_APP — abre aplicaciones por nombre de voz.
#
# Windows → ejecuta localmente
# RPi     → consulta la BD via API y manda la ruta completa al agente Electron

import sys
import requests as _requests
from rapidfuzz import process, fuzz

from orion.commands.base import BaseCommand, CommandResult
from orion.core.brain import limpiar_texto
import orion.config as config

_LAPTOP_AGENT = "http://100.107.212.54:8765"


def _obtener_catalogo() -> dict:
    """Obtiene el catálogo de apps desde la API con sus rutas completas."""
    try:
        r = _requests.get(f"{config.API_URL}/apps", timeout=5)
        if r.status_code == 200:
            catalogo = {}
            for app in r.json():
                if not app.get("enabled", True):
                    continue
                nombre = app["name"].lower().strip()
                catalogo[nombre] = {
                    "name": app["name"],
                    "exec_path": app["exec_path"],
                    "aliases": [a["alias"].lower().strip() for a in app.get("aliases", [])],
                }
            return catalogo
    except Exception as e:
        print(f"[OpenApp] Error obteniendo catálogo: {e}")
    return {}


def _buscar_app(payload: str, catalogo: dict):
    """Busca la app más parecida usando fuzzy matching."""
    payload = payload.lower().strip()

    # Construir lista de opciones (nombres + aliases)
    opciones = []
    alias_to_app = {}
    for nombre, data in catalogo.items():
        opciones.append(nombre)
        alias_to_app[nombre] = data
        for alias in data["aliases"]:
            opciones.append(alias)
            alias_to_app[alias] = data

    if not opciones:
        return None, None

    best = process.extractOne(payload, opciones, scorer=fuzz.ratio)
    if not best or best[1] < 70:
        return None, None

    app_data = alias_to_app[best[0]]
    return app_data["name"], app_data["exec_path"]


def _mandar_a_laptop(app_name: str, exec_path: str) -> bool:
    """Manda la orden al agente Electron con la ruta completa."""
    try:
        r = _requests.post(
            f"{_LAPTOP_AGENT}/run",
            json={"action": "OPEN_APP", "payload": exec_path},
            timeout=5,
        )
        print(f"[OpenApp] Agente respondió: {r.status_code} {r.text}")
        return r.status_code == 200 and r.json().get("ok", False)
    except Exception as e:
        print(f"[OpenApp] Error contactando agente laptop: {e}")
        return False


class OpenAppCommand(BaseCommand):
    intent_name = "OPEN_APP"

    def __init__(self):
        if sys.platform == "win32":
            from orion.os_apps.app_matcher import opciones_gramatica_apps
            self.grammar_apps = opciones_gramatica_apps()
        else:
            self.grammar_apps = []

    def execute(self, context, text: str, payload: str, confidence: float) -> CommandResult:

        # ── RPi: mandar al agente de la laptop ───────────────────────────────
        if sys.platform != "win32":
            payload_limpio = limpiar_texto(payload)
            print(f"[OpenApp] Buscando app: {payload_limpio!r}")

            catalogo = _obtener_catalogo()
            print(f"[OpenApp] Catálogo: {len(catalogo)} apps")

            app_nombre, app_exec = _buscar_app(payload_limpio, catalogo)
            print(f"[OpenApp] Encontrada: {app_nombre!r} → {app_exec!r}")

            if not app_nombre:
                return CommandResult(
                    success=False,
                    message=f"No conozco la aplicación {payload}. Puedes pedirme abrir Chrome, Discord, Spotify, Word o Excel.",
                    action="OPEN_APP_UNKNOWN",
                    payload=payload,
                )

            ok = _mandar_a_laptop(app_nombre, app_exec)

            if ok:
                return CommandResult(
                    success=True,
                    message=f"Listo, abriendo {app_nombre} en tu laptop.",
                    action="OPEN_APP_OK",
                    payload=app_nombre,
                )
            else:
                return CommandResult(
                    success=False,
                    message="No pude conectar con la laptop. Asegúrate de que la app de ORION esté abierta.",
                    action="OPEN_APP_AGENT_FAIL",
                    payload=app_nombre,
                )

        # ── Windows: ejecutar localmente ──────────────────────────────────────
        from orion.os_apps.app_matcher import normalizar_app
        from orion.os_apps.launcher import abrir_app

        payload_limpio = limpiar_texto(payload)

        if len(payload_limpio) < config.APP_MIN_PAYLOAD_LEN:
            return CommandResult(
                success=False,
                message="No entendí bien qué aplicación quieres abrir.",
                action="OPEN_APP_PAYLOAD_TOO_SHORT",
                payload=payload,
            )

        app_canon, score, exec_path = normalizar_app(payload)
        print(f"[DEBUG] open_app payload={payload!r} canon={app_canon!r} score={score:.2f}")

        if not app_canon or score < config.APP_MATCH_THRESHOLD:
            context.speaker.decir("No escuché bien qué programa quieres abrir. Repítelo.")
            intento_app = context.listener.escuchar_con_gramatica(
                self.grammar_apps, segundos_max=4,
            )
            if not intento_app:
                return CommandResult(
                    success=False,
                    message="No escuché lo que quieres abrir.",
                    action="OPEN_APP_NO_GRAMMAR_INPUT",
                    payload=payload,
                )
            app_canon, score, exec_path = normalizar_app(intento_app)
            if not app_canon or score < config.APP_MATCH_THRESHOLD:
                return CommandResult(
                    success=False,
                    message="Todavía no entendí bien el nombre del programa.",
                    action="OPEN_APP_LOW_CONF",
                    payload=intento_app,
                )

        ok = abrir_app(exec_path)
        return CommandResult(
            success=ok,
            message=f"Listo, abrí {app_canon}." if ok else f"No pude abrir {app_canon}.",
            action="OPEN_APP_OK" if ok else "OPEN_APP_FAIL",
            payload=app_canon,
        )