# main_robot.py
#
# Punto de entrada de ORION para Raspberry Pi.
#
# Modos de uso:
#   python main_robot.py              → producción (voz, headless, systemd)
#   python main_robot.py --dev        → desarrollo (teclado, sin micrófono/altavoces)
#   python main_robot.py --dev --tts  → desarrollo con TTS real activado
 
from __future__ import annotations
 
import argparse
import os
import sys
import signal
import logging
from pathlib import Path
 
os.environ.setdefault("PYTHONWARNINGS", "ignore")
 
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger("orion.robot")
 
 
# =============================================================================
# Helpers de arranque
# =============================================================================
 
def _cargar_env():
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        log.warning(".env no encontrado — usando variables de entorno del sistema")
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
        log.info(".env cargado desde %s", env_path)
    except ImportError:
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip())
 
 
def _verificar_audio():
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        inputs  = [d for d in devices if d["max_input_channels"] > 0]
        outputs = [d for d in devices if d["max_output_channels"] > 0]
        if not inputs:
            log.warning("No se detectó ningún micrófono. El listener no funcionará.")
        if not outputs:
            log.warning("No se detectó ningún altavoz. El TTS no producirá sonido.")
    except Exception as e:
        log.warning("No se pudo verificar dispositivos de audio: %s", e)
 
 
def _manejador_seniales(assistant):
    def _handler(signum, frame):
        log.info("Señal %s recibida. Deteniendo ORION...", signal.Signals(signum).name)
        try:
            assistant.context.speaker.decir("Apagando ORION.")
            assistant.context.speaker.cerrar()
        except Exception:
            pass
        sys.exit(0)
    signal.signal(signal.SIGTERM, _handler)
    signal.signal(signal.SIGINT, _handler)
 
 
# =============================================================================
# Modo DEV — loop por teclado sin micrófono ni altavoces
# =============================================================================
 
_RESET  = "\033[0m"
_CYAN   = "\033[96m"
_GREEN  = "\033[92m"
_YELLOW = "\033[93m"
_RED    = "\033[91m"
_GRAY   = "\033[90m"
_BOLD   = "\033[1m"
 
 
def _imprimir_resultado(result):
    icono = "✅" if result.success else "❌"
    color = _GREEN if result.success else _RED
    print(f"\n{color}{icono}  [{result.action}]{_RESET}")
    print(f"{_BOLD}   Respuesta:{_RESET} {result.message}")
    print(f"{_GRAY}   Payload:   {result.payload}{_RESET}")
 
 
def _run_dev(assistant, con_tts: bool):
    print(f"\n{_BOLD}{_CYAN}{'=' * 54}{_RESET}")
    print(f"{_BOLD}{_CYAN}   ORION — Modo desarrollo (teclado){_RESET}")
    if con_tts:
        print(f"{_YELLOW}   TTS activado — ORION hablará las respuestas{_RESET}")
    else:
        print(f"{_GRAY}   TTS desactivado — respuestas solo en pantalla{_RESET}")
        print(f"{_GRAY}   Usa --tts para activar el audio{_RESET}")
    print(f"{_BOLD}{_CYAN}{'=' * 54}{_RESET}")
    print(f"{_GRAY}   Escribe un comando y presiona Enter.")
    print(f"   Escribe 'salir' para terminar.")
    print(f"{'-' * 54}{_RESET}\n")
 
    while True:
        try:
            texto = input(f"{_CYAN}Comando: {_RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{_YELLOW}Saliendo...{_RESET}")
            break
 
        if not texto:
            continue
 
        if texto.lower() in {"salir", "exit", "quit"}:
            print(f"{_YELLOW}Hasta luego.{_RESET}")
            break
 
        print(f"{_GRAY}   Procesando...{_RESET}")
        result = assistant.process_text(texto, speak=con_tts)
        _imprimir_resultado(result)
 
        if result.action == "EXIT":
            break
 
    try:
        assistant.context.speaker.cerrar()
    except Exception:
        pass
    assistant.display.apagar()
 
 
# =============================================================================
# Modo PRODUCCION — loop por voz headless
# =============================================================================
 
def _run_produccion(assistant):
    _manejador_seniales(assistant)
    log.info("ORION listo. Esperando hotword...")
    assistant.run()
 
 
# =============================================================================
# Entrada principal
# =============================================================================
 
def _parsear_args():
    parser = argparse.ArgumentParser(
        description="ORION Robot — Asistente de voz para Raspberry Pi",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Modo desarrollo: comandos por teclado en lugar de microfono",
    )
    parser.add_argument(
        "--tts",
        action="store_true",
        help="En modo --dev, activa el TTS para escuchar las respuestas",
    )
    return parser.parse_args()
 
 
def main():
    args = _parsear_args()
 
    log.info("=" * 50)
    if args.dev:
        log.info("ORION Robot — modo DESARROLLO (teclado)")
    else:
        log.info("ORION Robot — modo PRODUCCION (voz)")
    log.info("=" * 50)
 
    _cargar_env()
 
    if not args.dev or args.tts:
        _verificar_audio()
 
    from orion.core.assistant import OrionAssistant
    assistant = OrionAssistant(modo_dev=args.dev)
 
    if args.dev:
        _run_dev(assistant, con_tts=args.tts)
    else:
        _run_produccion(assistant)
 
 
if __name__ == "__main__":
    main()