# orion/core/brain.py
import re
import unicodedata
from orion.os_apps.app_matcher import normalizar_app
 
 
def quitar_acentos(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
 
 
def limpiar_texto(texto: str) -> str:
    texto = (texto or "").lower().strip()
    texto = quitar_acentos(texto)
    texto = re.sub(r"[^\w\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto
 
 
def detectar_hotword(texto: str, hotword: str = "orion") -> bool:
    return hotword in limpiar_texto(texto)
 
 
# ── Corrección de términos técnicos mal reconocidos por Vosk ─────────────────
# El modelo small confunde palabras técnicas con palabras comunes del español.
# Este diccionario corrige las más frecuentes ANTES de procesar el intent.
# Clave: lo que dice Vosk | Valor: lo que el usuario realmente dijo
_CORRECCIONES = {
    # Tecnología
    "peyton": "python",
    "paiton": "python",
    "payton": "python",
    "piton":  "python",
    "java script": "javascript",
    "javas cript": "javascript",
    "git hub": "github",
    "you tube": "youtube",
    "face book": "facebook",
    "what sapp": "whatsapp",
    "was ap": "whatsapp",
    "what sap": "whatsapp",
    "spotify": "spotify",      # a veces lo pronuncian raro
    "visual estudio": "visual studio",
    "visual estudio code": "visual studio code",
    "vs cot": "vscode",
    "pauer point": "powerpoint",
    "pauer poi": "powerpoint",
    # Comandos del sistema
    "screenshot": "screenshot",
    "escrin shot": "screenshot",
    "escrín": "screenshot",
}
 
 
def corregir_terminos(texto: str) -> str:
    """
    Aplica correcciones de términos técnicos mal reconocidos por Vosk.
    Se aplica DESPUÉS de limpiar_texto (ya sin acentos y en minúsculas).
    """
    for erroneo, correcto in _CORRECCIONES.items():
        texto = re.sub(rf"\b{re.escape(erroneo)}\b", correcto, texto)
    return texto
 
 
PALABRAS_ABRIR = [
    "abre", "abrir", "abreme", "abreme el", "abre el", "abre la",
    "inicia", "ejecuta", "arranca", "pon",
    "quiero abrir", "quiero que abras",
]
 
PALABRAS_BUSCAR = [
    # Preguntas directas
    "que es", "que significa", "que son",
    "quien es", "quien fue", "quienes son",
    "como es", "como funciona", "como se hace",
    "cuando fue", "cuando es", "cuando ocurrio",
    "donde es", "donde queda", "donde esta",
    "por que es", "para que sirve", "para que es",
    "cuanto es", "cuanto cuesta", "cuantos son",
    # Verbos de búsqueda
    "busca", "buscar", "investiga", "investigame",
    "explicame", "explica", "dime", "dime sobre",
    "cuentame", "cuentame sobre",
    "quiero saber", "necesito saber",
    "informacion sobre", "informacion de",
    "dime sobre", "habla de", "hablame de",
    # Patrones con "quien"
    "quien pinto", "quien escribio", "quien descubrio",
    "quien invento", "quien fundo", "quien gano",
    "quien creo", "quien dirigio",
]
 
 
def extraer_tema_busqueda(texto: str) -> str:
    t = limpiar_texto(texto)
    t = corregir_terminos(t)
    t = t.replace("orion", "").strip()
 
    # Ordenar por longitud descendente para que "quiero saber" no quede
    # tapado por "saber" en una iteración anterior
    for p in sorted(PALABRAS_BUSCAR, key=len, reverse=True):
        if t.startswith(p):
            t = t[len(p):].strip()
            break
 
    return t
 
 
def extraer_app(texto: str) -> str:
    t = limpiar_texto(texto)
    t = corregir_terminos(t)
    t = t.replace("orion", "").strip()
 
    for p in sorted(PALABRAS_ABRIR, key=len, reverse=True):
        if t.startswith(p):
            t = t[len(p):].strip()
            break
 
    return t
 
 
def es_system_control_directo(t: str) -> bool:
    claves = [
        "captura", "screenshot", "pantallazo",
        "volumen", "audio",
        "silencia", "silencio", "mute", "sin sonido",
        "quita silencio", "quita el silencio",
        "activa el sonido", "unmute", "desmutea",
    ]
    return any(k in t for k in claves)
 
 
def es_web_search_directo(t: str) -> bool:
    # "es X" al inicio → "¿Qué es X?"
    if t.startswith("es ") and len(t) > 5:
        return True
    return any(k in t for k in PALABRAS_BUSCAR)
 
 
def es_small_talk_directo(t: str) -> bool:
    claves = [
        "hola", "buenos dias", "buenas tardes", "buenas noches",
        "como estas", "quien eres", "gracias",
        "que puedes hacer", "que haces", "para que sirves",
        "me escuchas", "estas ahi",
        "como te llamas", "cual es tu nombre",
        "cuentame un chiste", "dime un chiste", "un chiste",
        "que hora es", "que dia es", "que fecha es",
        "adios", "hasta luego", "bye", "chao",
        "como andas", "que onda", "que tal",
        "eres inteligente", "cuantos anos tienes",
    ]
    return any(k in t for k in claves)
 
 
def detectar_open_app_directo(t: str) -> tuple[bool, str]:
    payload = extraer_app(t)
 
    if len(payload) >= 3:
        canon, score, _ = normalizar_app(payload)
        if canon and score >= 0.85:
            return True, canon
 
    if len(t) >= 4:
        canon2, score2, _ = normalizar_app(t)
        if canon2 and score2 >= 0.88:
            return True, canon2
 
    return False, ""
 
 
def decidir_accion_ml(comando: str, classifier) -> tuple[str, str, float]:
    t = limpiar_texto(comando)
    t = corregir_terminos(t)
 
    # EXIT
    if any(k in t for k in [
        "salir", "termina", "terminar", "adios", "hasta luego",
        "cierra orion", "apagate", "apágate",
    ]):
        return ("EXIT", "", 1.0)
 
    # Detección directa por reglas (rápida y confiable)
    if es_system_control_directo(t):
        return ("SYSTEM_CONTROL", t, 0.99)
 
    if es_web_search_directo(t):
        if t.startswith("es "):
            tema = t.replace("es ", "", 1).strip()
        else:
            tema = extraer_tema_busqueda(t)
        return ("WEB_SEARCH", tema, 0.97 if tema else 0.75)
 
    if es_small_talk_directo(t):
        return ("SMALL_TALK", t, 0.99)
 
    ok_app, app_name = detectar_open_app_directo(t)
    if ok_app:
        return ("OPEN_APP", app_name, 0.96)
 
    # Fallback al clasificador ML
    intent, conf = classifier.predecir(comando)
 
    if intent == "WEB_SEARCH":
        return (intent, extraer_tema_busqueda(comando), conf)
 
    if intent == "OPEN_APP":
        payload = extraer_app(comando)
        if len(payload) < 3:
            return ("UNKNOWN", "", conf)
        canon, score, _ = normalizar_app(payload)
        if canon and score >= 0.85:
            return (intent, canon, max(conf, score))
        return (intent, payload, conf)
 
    if intent == "SYSTEM_CONTROL":
        return (intent, t, conf)
 
    if intent == "SMALL_TALK":
        return (intent, "smalltalk", conf)

    if intent == "TAKE_PHOTO":
        return (intent, "", conf)

    return ("UNKNOWN", "", conf)