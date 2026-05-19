# orion/os_apps/app_matcher.py
from rapidfuzz import process, fuzz
from orion.integrations.api_client import get_apps
 
# ── Caché en memoria ──────────────────────────────────────────────────────────
# El catálogo se carga UNA sola vez al primer uso (o al llamar refresh_catalogo).
# Así evitamos una petición HTTP a la API en cada reconocimiento de app.
_catalogo_cache: dict | None = None
 
 
def _build_catalogo(apps_data: list) -> dict:
    catalogo = {}
    for app in apps_data:
        if not app.get("enabled", True):
            continue
        nombre = _normalizar_texto(app["name"])
        aliases = [_normalizar_texto(a["alias"]) for a in app.get("aliases", [])]
        catalogo[nombre] = {
            "name": app["name"],
            "exec_path": app["exec_path"],
            "aliases": aliases,
        }
    return catalogo
 
 
def _normalizar_texto(texto: str) -> str:
    return texto.strip().lower()
 
 
def _get_catalogo() -> dict:
    """
    Devuelve el catálogo desde caché.
    Si aún no se ha cargado, lo carga desde la API una sola vez.
    Si la API no responde, devuelve un catálogo vacío sin crashear.
    """
    global _catalogo_cache
    if _catalogo_cache is None:
        refresh_catalogo()
    return _catalogo_cache or {}
 
 
def refresh_catalogo():
    """
    Fuerza una recarga del catálogo desde la API.
    Útil cuando se agregan/editan apps desde la GUI sin reiniciar ORION.
    """
    global _catalogo_cache
    apps_data = get_apps()
    if apps_data:
        _catalogo_cache = _build_catalogo(apps_data)
        print(f"[AppMatcher] Catálogo cargado: {len(_catalogo_cache)} apps")
    else:
        # Si la API no responde, dejamos el caché anterior (si existía)
        # o un dict vacío, sin romper el flujo
        if _catalogo_cache is None:
            _catalogo_cache = {}
            print("[AppMatcher] WARN: API no disponible, catálogo vacío")
        else:
            print("[AppMatcher] WARN: API no disponible, usando catálogo anterior")
 
 
# ── API pública (misma interfaz que antes, el resto del proyecto no cambia) ───
 
def normalizar_texto(texto: str) -> str:
    return _normalizar_texto(texto)
 
 
def opciones_gramatica_apps() -> list[str]:
    """
    Devuelve nombres y aliases para la confirmación por gramática cerrada.
    """
    catalogo = _get_catalogo()
    opciones = set()
    for app_name, app_data in catalogo.items():
        opciones.add(app_name)
        for alias in app_data["aliases"]:
            opciones.add(alias)
    return sorted(opciones)
 
 
def normalizar_app(user_input: str, threshold: int = 75):
    """
    Busca la app más parecida al texto del usuario.
    Retorna (nombre_canonico, score 0-1, exec_path) o (None, score, None).
    """
    user_input = _normalizar_texto(user_input)
    catalogo = _get_catalogo()
 
    opciones = []
    alias_to_app = {}
 
    for app_name, app_data in catalogo.items():
        opciones.append(app_name)
        alias_to_app[app_name] = app_data
        for alias in app_data["aliases"]:
            opciones.append(alias)
            alias_to_app[alias] = app_data
 
    if not opciones:
        return None, 0.0, None
 
    best_match = process.extractOne(user_input, opciones, scorer=fuzz.ratio)
 
    if not best_match:
        return None, 0.0, None
 
    texto_encontrado, score, _ = best_match
 
    if score < threshold:
        return None, score / 100.0, None
 
    app_data = alias_to_app[texto_encontrado]
    return app_data["name"], score / 100.0, app_data["exec_path"]