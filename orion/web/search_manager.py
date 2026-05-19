# orion/web/search_manager.py
#
# Estrategia de búsqueda:
# 1. Wikipedia ES siempre primero — gratis, en español, sin basura
# 2. Si el query es de tiempo real (clima, precio, etc.) o Wikipedia no tiene
#    resultado, cae a Tavily → Serper → Local
# Todo el texto pasa por limpieza antes de entregarse al TTS.

import re

# Queries que Wikipedia no puede responder (datos en tiempo real)
_TIEMPO_REAL = re.compile(
    r"\b(clima|temperatura|tiempo|lluvia|calor|frío|frio|"
    r"dólar|dollar|euro|peso|precio|cotización|cotizacion|bolsa|"
    r"hoy|ahora|actual|ahorita|este momento|noticias|últimas|ultimas)\b",
    flags=re.IGNORECASE,
)

# Basura multimedia
_BASURA_ORACION = re.compile(
    r"^(.*?\b(comments?|escúchala|guárdala|plataformas|video oficial|"
    r"letra|lyrics|en vivo|live|streaming|playlist|suscr[ií]be)\b.*?)$",
    flags=re.IGNORECASE,
)


class SearchManager:
    def __init__(self, providers: list):
        self.providers = [p for p in providers if p.available()]
        self._wikipedia = next((p for p in self.providers if p.name == "wikipedia"), None)
        self._fallbacks = [p for p in self.providers if p.name != "wikipedia"]

    def normalizar_query(self, query: str) -> str:
        return re.sub(r"\s+", " ", (query or "").strip())

    def _es_tiempo_real(self, query: str) -> bool:
        return bool(_TIEMPO_REAL.search(query))

    def _limpiar_para_tts(self, texto: str) -> str:
        t = texto or ""
        t = re.sub(r"https?://\S+", "", t)
        t = re.sub(r"www\.\S+", "", t)
        t = re.sub(r"\[\d+\]|\[cita[^\]]*\]", "", t)
        t = re.sub(r"[©®™°•·]", " ", t)
        t = re.sub(r"\s+", " ", t.replace("\n", " "))
        return t.strip()

    def _extraer_respuesta(self, texto: str, max_chars: int = 500) -> str:
        t = self._limpiar_para_tts(texto)

        # Saltar prefijo tipo "Título: Contenido"
        match_prefijo = re.match(r"^[^.]{0,100}[?:]\s+([A-ZÁÉÍÓÚ].{50,})", t)
        if match_prefijo:
            candidato = match_prefijo.group(1).strip()
            if len(candidato) > 80:
                t = candidato

        # Acumular oraciones buenas hasta max_chars
        oraciones = re.split(r"(?<=[.!?])\s+", t)
        respuesta = ""
        for oracion in oraciones:
            oracion = oracion.strip()
            if not oracion or _BASURA_ORACION.match(oracion):
                continue
            candidato = (respuesta + " " + oracion).strip() if respuesta else oracion
            if len(candidato) <= max_chars:
                respuesta = candidato
            else:
                break

        if not respuesta and t:
            respuesta = t[:max_chars].rsplit(" ", 1)[0] + "..."

        return respuesta.strip()

    def _buscar_fallback(self, query: str) -> tuple[str, str]:
        """Busca en Tavily → Serper → Local."""
        for p in self._fallbacks:
            try:
                data = p.search(query)
                text = p.to_text(data)
                if text and len(text.strip()) >= 30:
                    print(f"[SearchManager] Fallback usó: {p.name}")
                    return text.strip(), p.name
            except Exception as e:
                print(f"[SearchManager] {p.name} falló: {e}")
        return "", "none"

    def buscar_con_fallback(self, query: str) -> tuple[str, str]:
        query = self.normalizar_query(query)

        # Si el query es de tiempo real, saltar Wikipedia directamente
        if self._es_tiempo_real(query):
            print(f"[SearchManager] Query tiempo real → saltando Wikipedia")
            return self._buscar_fallback(query)

        # Intentar Wikipedia primero
        if self._wikipedia:
            try:
                data = self._wikipedia.search(query)
                text = self._wikipedia.to_text(data)
                if text and len(text.strip()) >= 50:
                    print(f"[SearchManager] Usando Wikipedia ✓")
                    return text.strip(), "wikipedia"
                else:
                    print(f"[SearchManager] Wikipedia sin resultado → fallback")
            except Exception as e:
                print(f"[SearchManager] Wikipedia falló: {e}")

        # Fallback a Tavily/Serper/Local
        return self._buscar_fallback(query)

    def resumir_es(self, texto: str, max_chars: int = 500) -> str:
        return self._extraer_respuesta(texto, max_chars=max_chars)