# orion/orion_api/app/main.py
from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import text
from .db import Base, engine
from .routes import commands, apps, stats
from . import models  # noqa: F401

Base.metadata.create_all(bind=engine)
app = FastAPI(title="ORION API", version="1.0.0")
app.include_router(commands.router)
app.include_router(apps.router)
app.include_router(stats.router)

# ── Singleton del assistant ───────────────────────────────────────────────────
# modo_dev=True → no carga Listener (Vosk) ni micrófono.
# La API solo necesita el clasificador ML y los comandos, no reconocimiento de voz.
# Esto reduce el uso de RAM de ~3.4GB a ~300MB.
_assistant = None

def get_assistant():
    global _assistant
    if _assistant is None:
        from orion.core.assistant import OrionAssistant
        # modo_dev=True evita cargar Vosk — ahorra ~3GB de RAM
        _assistant = OrionAssistant(modo_dev=True)
        print("[ORION API] Assistant cargado (sin Vosk).")
    return _assistant

# ── Endpoints ─────────────────────────────────────────────────────────────────
class ExecuteRequest(BaseModel):
    text: str

@app.post("/execute")
def execute_command(payload: ExecuteRequest):
    texto = (payload.text or "").strip()
    if not texto:
        return {
            "success": False,
            "message": "No se recibió texto.",
            "action": "EXECUTE_EMPTY",
        }
    assistant = get_assistant()
    result = assistant.process_text(texto, speak=False)
    return {
        "success": result.success,
        "message": result.message,
        "action": result.action,
        "payload": result.payload,
    }

@app.get("/health")
def health():
    db_connected = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_connected = True
    except Exception:
        db_connected = False
    return {
        "status": "ok",
        "db_connected": db_connected,
    }