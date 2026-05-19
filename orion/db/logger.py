import requests


class ConversationLogger:
    def __init__(self, api_url: str = "http://127.0.0.1:8000"):
        self.api_url = api_url.rstrip("/")

    def guardar(self, frase: str, accion: str):
        """
        Guarda eventos generales en command_history vía FastAPI/MariaDB.
        """
        try:
            requests.post(
                f"{self.api_url}/commands",
                json={
                    "raw_text": frase or "",
                    "cleaned_text": frase or "",
                    "intent": "SYSTEM_EVENT",
                    "payload": accion or "",
                    "confidence": 1.0,
                    "status": "success",
                    "response_message": accion or "",
                },
                timeout=3,
            )
        except Exception as e:
            print(f"[WARN] No se pudo guardar evento en API: {e}")