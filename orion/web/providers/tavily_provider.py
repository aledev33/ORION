# orion/web/providers/tavily_provider.py
#
# Proveedor Tavily — usado como fallback para datos en tiempo real.

import os
import re

_DOMINIOS_BASURA = (
    "youtube.com", "youtu.be", "spotify.com", "soundcloud.com",
    "tiktok.com", "instagram.com", "twitter.com", "x.com",
    "facebook.com", "vimeo.com", "deezer.com", "music.apple.com",
)
_TITULOS_BASURA = re.compile(
    r"\b(video oficial|letra|lyrics|en vivo|live|feat\.|ft\.|"
    r"official video|music video|album|tour|concierto|"
    r"escuchala|streaming|playlist)\b",
    flags=re.IGNORECASE,
)


def _es_resultado_util(result: dict) -> bool:
    url   = (result.get("url") or "").lower()
    title = result.get("title") or ""
    if any(d in url for d in _DOMINIOS_BASURA):
        return False
    if _TITULOS_BASURA.search(title):
        return False
    return True


class TavilyProvider:
    name = "tavily"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY", "")

    def available(self) -> bool:
        return bool(self.api_key)

    def search(self, query: str, max_results: int = 5) -> dict:
        from tavily import TavilyClient
        client = TavilyClient(self.api_key)
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=max_results,
            include_answer=True,
            country="mexico",
        )
        return response

    def to_text(self, data: dict) -> str:
        # Respuesta directa de Tavily (la más limpia)
        answer = (data.get("answer") or "").strip()
        if answer and len(answer) > 30:
            return answer
        # Snippets filtrados
        results = data.get("results") or []
        utiles  = [r for r in results if _es_resultado_util(r)] or results
        parts = []
        for r in utiles[:2]:
            content = (r.get("content") or "").strip()
            if content and len(content) > 40:
                parts.append(content)
        return " ".join(parts).strip()