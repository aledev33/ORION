# test_rpi.py
#
# Script de verificación por fases para Raspberry Pi.
# Corre cada fase independientemente para aislar problemas.
#
# Uso:
#   python test_rpi.py              → corre todas las fases
#   python test_rpi.py --fase 1     → solo la fase 1
#   python test_rpi.py --fase 3     → solo la fase 3
#   python test_rpi.py --lista      → muestra qué prueba cada fase
 
from __future__ import annotations
 
import argparse
import os
import sys
import time
from pathlib import Path
 
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
 
# ── Colores ANSI ──────────────────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
GRAY   = "\033[90m"
 
 
def ok(msg):   print(f"  {GREEN}✅ {msg}{RESET}")
def fail(msg): print(f"  {RED}❌ {msg}{RESET}")
def info(msg): print(f"  {GRAY}   {msg}{RESET}")
def warn(msg): print(f"  {YELLOW}⚠️  {msg}{RESET}")
 
 
def titulo(n, nombre):
    print(f"\n{BOLD}{CYAN}{'─' * 54}{RESET}")
    print(f"{BOLD}{CYAN}  FASE {n}: {nombre}{RESET}")
    print(f"{BOLD}{CYAN}{'─' * 54}{RESET}")
 
 
def resultado_fase(exito: bool, nombre: str):
    if exito:
        print(f"\n{GREEN}{BOLD}  ✅ FASE OK: {nombre}{RESET}")
    else:
        print(f"\n{RED}{BOLD}  ❌ FASE FALLÓ: {nombre}{RESET}")
    return exito
 
 
# =============================================================================
# FASE 1 — Dependencias Python
# =============================================================================
 
def fase_1():
    titulo(1, "Dependencias Python")
    exito = True
 
    paquetes = [
        ("vosk",          "Reconocimiento de voz (STT)"),
        ("sounddevice",   "Captura de audio"),
        ("sklearn",       "Clasificador ML de intents"),
        ("joblib",        "Carga del modelo ML"),
        ("rapidfuzz",     "Fuzzy matching de apps"),
        ("requests",      "HTTP para API y búsqueda web"),
        ("fastapi",       "API backend"),
        ("uvicorn",       "Servidor ASGI"),
        ("sqlalchemy",    "ORM base de datos"),
        ("pymysql",       "Driver MariaDB"),
        ("pydantic",      "Validación de datos"),
        ("dotenv",        "Carga de .env"),
        ("PIL",           "Procesamiento de imágenes (Pillow)"),
        ("pulsectl",      "Control de volumen PulseAudio"),
    ]
 
    for modulo, descripcion in paquetes:
        try:
            __import__(modulo)
            ok(f"{modulo:15} — {descripcion}")
        except ImportError:
            fail(f"{modulo:15} — {descripcion}  ← NO INSTALADO")
            exito = False
 
    # Piper es un binario, no un módulo Python
    import subprocess
    try:
        r = subprocess.run(["piper", "--version"], capture_output=True, timeout=5)
        if r.returncode == 0:
            ok(f"{'piper (binario)':15} — TTS offline (Piper)")
        else:
            warn(f"{'piper (binario)':15} — instalado pero con error")
    except FileNotFoundError:
        warn(f"{'piper (binario)':15} — no instalado (INSTALAR antes de producción)")
        info("Ver instrucciones en orion/tts/speaker.py")
 
    # luma.oled es opcional (pantalla OLED)
    try:
        import luma.oled
        ok(f"{'luma.oled':15} — Pantalla OLED SSD1306")
    except ImportError:
        warn(f"{'luma.oled':15} — no instalado (opcional, solo con pantalla OLED)")
 
    return resultado_fase(exito, "Dependencias Python")
 
 
# =============================================================================
# FASE 2 — Modelo Vosk y configuración
# =============================================================================
 
def fase_2():
    titulo(2, "Modelo Vosk y configuración")
    exito = True
 
    try:
        import orion.config as config
        ok(f"config.py cargado correctamente")
        info(f"API_URL:    {config.API_URL}")
        info(f"MODEL_PATH: {config.MODEL_PATH}")
        info(f"TTS_RATE:   {config.TTS_RATE}")
    except Exception as e:
        fail(f"Error cargando config.py: {e}")
        return resultado_fase(False, "Modelo Vosk y configuración")
 
    # Verificar que el modelo existe
    model_path = config.MODEL_PATH
    if model_path.exists() and any(model_path.iterdir()):
        size_mb = sum(
            f.stat().st_size for f in model_path.rglob("*") if f.is_file()
        ) / (1024 * 1024)
        ok(f"Modelo Vosk encontrado ({size_mb:.0f} MB)")
        if size_mb < 100:
            warn("El modelo parece el 'small' (~40MB). Para producción se recomienda el grande.")
    else:
        fail(f"Modelo Vosk NO encontrado en: {model_path}")
        info("Copia el modelo desde tu laptop:")
        info("  scp -r /ruta/local/models/vosk-es pi@<IP>:~/orion2/models/")
        exito = False
 
    # Verificar .env
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        ok(".env encontrado")
        with open(env_path) as f:
            claves = [
                l.split("=")[0].strip()
                for l in f
                if l.strip() and not l.startswith("#") and "=" in l
            ]
        for clave in ["MARIADB_USER", "MARIADB_PASSWORD", "MARIADB_DB"]:
            if clave in claves:
                ok(f"  {clave} definido")
            else:
                fail(f"  {clave} NO definido en .env")
                exito = False
    else:
        fail(".env no encontrado en la raíz del proyecto")
        exito = False
 
    return resultado_fase(exito, "Modelo Vosk y configuración")
 
 
# =============================================================================
# FASE 3 — MariaDB y API
# =============================================================================
 
def fase_3():
    titulo(3, "MariaDB y API backend")
    exito = True
 
    # Verificar que MariaDB responde
    try:
        import pymysql
        from dotenv import load_dotenv
        load_dotenv(PROJECT_ROOT / ".env")
 
        conn = pymysql.connect(
            host=os.getenv("MARIADB_HOST", "127.0.0.1"),
            port=int(os.getenv("MARIADB_PORT", "3306")),
            user=os.getenv("MARIADB_USER"),
            password=os.getenv("MARIADB_PASSWORD"),
            database=os.getenv("MARIADB_DB"),
            connect_timeout=5,
        )
        conn.close()
        ok("Conexión a MariaDB exitosa")
    except Exception as e:
        fail(f"No se pudo conectar a MariaDB: {e}")
        info("Verificar que MariaDB esté corriendo:")
        info("  sudo systemctl status mariadb")
        info("  sudo systemctl start mariadb")
        exito = False
 
    # Verificar que la API responde
    try:
        import requests
        import orion.config as config
        r = requests.get(f"{config.API_URL}/health", timeout=5)
        data = r.json()
        if data.get("status") == "ok":
            ok(f"API responde en {config.API_URL}")
            if data.get("db_connected"):
                ok("API confirma conexión a MariaDB")
            else:
                warn("API responde pero reporta DB desconectada")
        else:
            warn(f"API responde pero con estado inesperado: {data}")
    except Exception as e:
        warn(f"API no responde en {config.API_URL}: {e}")
        info("La API necesita estar corriendo para este test:")
        info("  uvicorn orion.orion_api.app.main:app --host 127.0.0.1 --port 8000")
        info("(Abre otra terminal y déjala corriendo)")
        # No marcamos como fallo duro — la API puede no estar levantada aún
        warn("Levanta la API y vuelve a correr esta fase")
 
    return resultado_fase(exito, "MariaDB y API backend")
 
 
# =============================================================================
# FASE 4 — Clasificador de intents (ML)
# =============================================================================
 
def fase_4():
    titulo(4, "Clasificador ML de intents")
    exito = True
 
    try:
        from orion.nlu.classifier import IntentClassifier
        clf = IntentClassifier()
        ok("IntentClassifier cargado")
    except Exception as e:
        fail(f"Error cargando IntentClassifier: {e}")
        return resultado_fase(False, "Clasificador ML")
 
    casos = [
        ("abre chrome",                    "OPEN_APP"),
        ("busca qué es la inteligencia artificial", "WEB_SEARCH"),
        ("sube el volumen",                "SYSTEM_CONTROL"),
        ("hola cómo estás",                "SMALL_TALK"),
        ("toma una captura de pantalla",   "SYSTEM_CONTROL"),
    ]
 
    print()
    for texto, intent_esperado in casos:
        try:
            from orion.core.brain import decidir_accion_ml
            intent, payload, conf = decidir_accion_ml(texto, clf)
            correcto = intent == intent_esperado
            simbolo  = "✅" if correcto else "⚠️ "
            color    = GREEN if correcto else YELLOW
            print(
                f"  {color}{simbolo}  \"{texto}\"\n"
                f"       → {intent} (esperado: {intent_esperado}) "
                f"conf={conf:.2f}{RESET}"
            )
            if not correcto:
                warn(f"Intent incorrecto para: '{texto}'")
        except Exception as e:
            fail(f"Error procesando '{texto}': {e}")
            exito = False
 
    return resultado_fase(exito, "Clasificador ML de intents")
 
 
# =============================================================================
# FASE 5 — Búsqueda web
# =============================================================================
 
def fase_5():
    titulo(5, "Búsqueda web (Tavily / Serper)")
    exito = True
 
    try:
        from dotenv import load_dotenv
        load_dotenv(PROJECT_ROOT / ".env")
        from orion.web.providers.tavily_provider import TavilyProvider
        from orion.web.providers.serper_provider import SerperProvider
        from orion.web.providers.local_provider import LocalProvider
        from orion.web.search_manager import SearchManager
    except Exception as e:
        fail(f"Error importando módulos de búsqueda: {e}")
        return resultado_fase(False, "Búsqueda web")
 
    tavily = TavilyProvider()
    serper = SerperProvider()
 
    if tavily.available():
        ok("Tavily API key configurada")
    else:
        warn("Tavily API key NO configurada (TAVILY_API_KEY en .env)")
 
    if serper.available():
        ok("Serper API key configurada")
    else:
        warn("Serper API key NO configurada (SERPER_API_KEY en .env)")
 
    if not tavily.available() and not serper.available():
        fail("Ningún proveedor de búsqueda disponible")
        info("Agrega al menos una API key en .env:")
        info("  TAVILY_API_KEY=tu_clave")
        info("  SERPER_API_KEY=tu_clave")
        exito = False
        return resultado_fase(exito, "Búsqueda web")
 
    # Búsqueda de prueba real
    print()
    info("Haciendo búsqueda de prueba: 'qué es Python'...")
    try:
        manager = SearchManager([tavily, serper, LocalProvider()])
        texto, fuente = manager.buscar_con_fallback("qué es Python")
        if texto:
            resumen = manager.resumir_es(texto, max_chars=200)
            ok(f"Búsqueda exitosa — fuente: {fuente}")
            info(f"Resultado: {resumen[:150]}...")
        else:
            fail("La búsqueda no devolvió resultados")
            exito = False
    except Exception as e:
        fail(f"Error en búsqueda: {e}")
        exito = False
 
    return resultado_fase(exito, "Búsqueda web")
 
 
# =============================================================================
# FASE 6 — TTS (Piper / espeak-ng)
# =============================================================================
 
def fase_6():
    titulo(6, "TTS — síntesis de voz")
 
    import subprocess
    from pathlib import Path
 
    # Verificar Piper
    piper_ok = False
    try:
        r = subprocess.run(["piper", "--version"], capture_output=True, timeout=5)
        piper_ok = r.returncode == 0
    except FileNotFoundError:
        pass
 
    if piper_ok:
        ok("Binario piper encontrado")
        model = Path(os.getenv(
            "PIPER_MODEL_PATH",
            str(Path.home() / "piper-models" / "es_MX-claude-high.onnx")
        ))
        if model.exists():
            ok(f"Modelo Piper encontrado: {model.name}")
 
            # Generar audio de prueba en archivo (sin necesitar altavoces)
            out_wav = PROJECT_ROOT / "test_tts.wav"
            info("Generando audio de prueba → test_tts.wav ...")
            try:
                import io, wave
                proc = subprocess.Popen(
                    ["piper", "--model", str(model), "--output-raw"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                )
                pcm, _ = proc.communicate(input="Hola, soy ORION. El sistema de voz funciona correctamente.".encode())
                if pcm:
                    buf = io.BytesIO()
                    with wave.open(buf, "wb") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(22050)
                        wf.writeframes(pcm)
                    out_wav.write_bytes(buf.getvalue())
                    ok(f"Audio generado: {out_wav}")
                    info("Cópialo a tu laptop para escucharlo:")
                    info(f"  scp pi@<IP_RPi>:{out_wav} ~/Desktop/test_tts.wav")
                    info("O si tienes altavoces conectados: aplay test_tts.wav")
                else:
                    fail("Piper no generó audio")
            except Exception as e:
                fail(f"Error generando audio: {e}")
        else:
            warn(f"Modelo Piper no encontrado en: {model}")
            info("Descárgalo siguiendo las instrucciones en orion/tts/speaker.py")
    else:
        warn("Piper no instalado — usando espeak-ng como fallback")
        try:
            r = subprocess.run(
                ["espeak-ng", "--version"], capture_output=True, timeout=5
            )
            if r.returncode == 0:
                ok("espeak-ng disponible como fallback")
            else:
                fail("espeak-ng tampoco disponible")
        except FileNotFoundError:
            fail("Ni Piper ni espeak-ng están instalados")
 
    return resultado_fase(piper_ok, "TTS — síntesis de voz")
 
 
# =============================================================================
# FASE 7 — Pipeline completo sin hardware
# =============================================================================
 
def fase_7():
    titulo(7, "Pipeline completo (sin hardware)")
    exito = True
 
    info("Inicializando OrionAssistant completo...")
    try:
        from orion.core.assistant import OrionAssistant
        t0 = time.time()
        assistant = OrionAssistant()
        t1 = time.time()
        ok(f"OrionAssistant iniciado en {t1 - t0:.1f}s")
    except Exception as e:
        fail(f"Error iniciando OrionAssistant: {e}")
        return resultado_fase(False, "Pipeline completo")
 
    # Comandos de prueba representativos
    casos = [
        ("hola",                                   "SMALL_TALK"),
        ("busca qué es la inteligencia artificial", "WEB_SEARCH"),
        ("sube el volumen",                         "SYSTEM_CONTROL"),
        ("abre spotify",                            "OPEN_APP"),
        ("toma captura de pantalla",                "SYSTEM_CONTROL"),
    ]
 
    print()
    for texto, intent_esperado in casos:
        try:
            result = assistant.process_text(texto, speak=False)
            correcto = intent_esperado.lower() in result.action.lower()
            simbolo  = "✅" if correcto else "⚠️ "
            color    = GREEN if correcto else YELLOW
            print(f"  {color}{simbolo}  \"{texto}\"")
            print(f"       → [{result.action}] {result.message[:80]}{RESET}")
        except Exception as e:
            fail(f"Error procesando '{texto}': {e}")
            exito = False
 
    try:
        assistant.context.speaker.cerrar()
        assistant.display.apagar()
    except Exception:
        pass
 
    return resultado_fase(exito, "Pipeline completo")
 
 
# =============================================================================
# Runner principal
# =============================================================================
 
FASES = {
    1: ("Dependencias Python",          fase_1),
    2: ("Modelo Vosk y configuración",  fase_2),
    3: ("MariaDB y API backend",        fase_3),
    4: ("Clasificador ML de intents",   fase_4),
    5: ("Búsqueda web",                 fase_5),
    6: ("TTS — síntesis de voz",        fase_6),
    7: ("Pipeline completo",            fase_7),
}
 
 
def main():
    parser = argparse.ArgumentParser(
        description="ORION — Verificación por fases para Raspberry Pi",
    )
    parser.add_argument(
        "--fase", type=int, choices=FASES.keys(),
        help="Correr solo una fase específica",
    )
    parser.add_argument(
        "--lista", action="store_true",
        help="Mostrar qué prueba cada fase y salir",
    )
    args = parser.parse_args()
 
    if args.lista:
        print(f"\n{BOLD}Fases disponibles:{RESET}")
        for n, (nombre, _) in FASES.items():
            print(f"  {CYAN}{n}{RESET} — {nombre}")
        print()
        return
 
    print(f"\n{BOLD}{CYAN}{'═' * 54}{RESET}")
    print(f"{BOLD}{CYAN}   ORION — Verificación de sistema (RPi){RESET}")
    print(f"{BOLD}{CYAN}{'═' * 54}{RESET}")
 
    fases_a_correr = {args.fase: FASES[args.fase]} if args.fase else FASES
    resultados = {}
 
    for n, (nombre, fn) in fases_a_correr.items():
        resultados[n] = fn()
 
    # Resumen final
    print(f"\n{BOLD}{'═' * 54}")
    print(f"  RESUMEN{RESET}")
    print(f"{BOLD}{'─' * 54}{RESET}")
    for n, (nombre, _) in FASES.items():
        if n not in resultados:
            continue
        color  = GREEN if resultados[n] else RED
        estado = "OK" if resultados[n] else "FALLÓ"
        print(f"  {color}{estado:6}{RESET}  Fase {n}: {nombre}")
 
    total   = len(resultados)
    exitosas = sum(1 for v in resultados.values() if v)
    print(f"\n  {BOLD}{exitosas}/{total} fases exitosas{RESET}\n")
 
 
if __name__ == "__main__":
    main()
PYEOF