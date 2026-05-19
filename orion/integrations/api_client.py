# orion/integrations/api_client.py
#
# Cliente HTTP para la API interna de ORION.
# Lee la URL desde config.py, que a su vez la toma de la variable de
# entorno ORION_API_URL. Esto permite que laptop y RPi apunten al
# servidor correcto sin cambiar código:
#
#   RPi (.env sin ORION_API_URL)    → http://127.0.0.1:8000   (local)
#   Laptop (.env con ORION_API_URL) → http://100.x.x.x:8000   (Tailscale)

import requests
import orion.config as config


def get_apps() -> list:
    """Obtiene el catálogo de apps registradas en la API."""
    try:
        response = requests.get(f"{config.API_URL}/apps", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[APIClient] No se pudo obtener apps: {e}")
        return []


def log_command(
    raw_text: str,
    cleaned_text: str | None,
    intent: str | None,
    payload: str | None,
    confidence: float | None,
    status: str = "success",
    response_message: str | None = None,
) -> bool:
    """Registra un comando ejecutado en el historial de la API."""
    try:
        requests.post(
            f"{config.API_URL}/commands",
            json={
                "raw_text": raw_text,
                "cleaned_text": cleaned_text,
                "intent": intent,
                "payload": payload,
                "confidence": confidence,
                "status": status,
                "response_message": response_message,
            },
            timeout=3,
        )
        return True
    except Exception as e:
        print(f"[APIClient] No se pudo registrar comando: {e}")
        return False