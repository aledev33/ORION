# orion/web/providers/serper_provider.py
import os
import re
import orion.config as config
 
_DOMINIOS_BASURA = (
    "youtube.com", "youtu.be", "spotify.com", "soundcloud.com",
    "tiktok.com", "instagram.com", "twitter.com", "x.com",
    "facebook.com", "vimeo.com", "deezer.com", "music.apple.com",
)
 
_TITULOS_BASURA = re.compile(
    r"\b(video oficial|letra|lyrics|en vivo|live|feat\.|ft\.|"
    r"official video|music video|álbum|album|tour|concierto|"
    r"escúchala|streaming|playlist)\b",
    flags=re.IGNORECASE,
)
 
 
def _es_resultado_util(result: dict) -> bool:
    url = (result.get("link") or "").lower()
    title = result.get("title") or ""
    if any(d in url for d in _DOMINIOS_BASURA):
        return False
    if _TITULOS_BASURA.search(title):
        return False
    return True
 
 
class SerperProvider:
    name = "serper"
 
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("SERPER_API_KEY", "")
        self.url = "https://google.serper.dev/search"
 
    def available(self) -> bool:
        return bool(self.api_key)
 
    def search(self, query: str, max_results: int = 5) -> dict:
        import requests
        lang = getattr(config, "RESPONSE_LANGUAGE", "es")
 
        headers = {
            "Content-Type": "application/json",
            "X-API-KEY": self.api_key,
        }
        payload = {
            "q": query,
            "num": max_results,
            "hl": lang,
            "gl": "mx" if lang == "es" else "us",
        }
        r = requests.post(self.url, json=payload, headers=headers, timeout=25)
        r.raise_for_status()
        return r.json()
 
    def to_text(self, data: dict) -> str:
        # 1. answerBox: la respuesta más directa de Google
        ab = data.get("answerBox") or {}
        if isinstance(ab, dict):
            # Preferir snippet largo sobre answer corto
            snippet = (ab.get("snippet") or "").strip()
            answer  = (ab.get("answer") or "").strip()
            txt = snippet if len(snippet) > len(answer) else answer
            if txt and len(txt) > 20:
                return txt
 
        # 2. knowledgeGraph: ficha de persona/lugar de Google
        kg = data.get("knowledgeGraph") or {}
        if kg:
            descripcion = (kg.get("description") or "").strip()
            if descripcion and len(descripcion) > 30:
                return descripcion
 
        # 3. Snippets orgánicos filtrados — sin multimedia
        organic = data.get("organic") or []
        utiles = [r for r in organic if _es_resultado_util(r)] or organic
 
        parts = []
        for r in utiles[:2]:
            snippet = (r.get("snippet") or "").strip()
            if snippet and len(snippet) > 40:
                parts.append(snippet)
 
        return " ".join(parts).strip()