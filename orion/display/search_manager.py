# orion/web/search_manager.py
 
import re
import orion.config as config
 
# Patrones que indican que una oracion es basura multimedia/marketing
_BASURA_ORACION = re.compile(
    r"^(.*?\b(comments?|escuchala|guardala|plataformas|video oficial|"
    r"letra|lyrics|en vivo|live|streaming|playlist|suscribe|"
    r"todo mi amor|por tu maldito|aca entre nos)\b.*?)$",
    flags=re.IGNORECASE,
)
 
 
class SearchManager:
    def __init__(self, providers: list):
        self.providers = [p for p in providers if p.available()]
 
    def normalizar_query(self, query: str) -> str:
        return re.sub(r"\s+", " ", (query or "").strip())
 
    def _preparar_query(self, query: str) -> str:
        """
        Prepara el query final.
        - Detecta nombres propios y agrega 'biografia' para evitar
          resultados de canciones.
        - NO agrega sufijo de idioma — Serper y Tavily detectan el idioma
          del query automaticamente. Agregar "en español" causaba resultados
          incorrectos porque los buscadores lo interpretaban como parte
          de la busqueda.
        """
        q = query.strip()
 
        palabras = q.split()
        verbos_busqueda = {
            "que", "quien", "como", "cuando", "donde", "clima",
            "temperatura", "precio", "hora", "cuanto",
        }
        es_nombre_propio = (
            len(palabras) >= 2
            and all(p[0].isupper() for p in palabras if len(p) > 2)
            and not any(p.lower() in verbos_busqueda for p in palabras)
        )
 
        if es_nombre_propio:
            q = f"{q} biografia"
 
        return q
 
    def _saltar_prefijo_roto(self, texto: str) -> str:
        """
        Salta fragmentos rotos al inicio como 'l machine learning - Que es...: Contenido'
        Ejecutar ANTES de limpiar_para_tts para aprovechar los signos originales.
        """
        t = texto.strip()
        if t and not t[0].isupper() and not t[0].isdigit():
            m = re.search(r"[?:]\s+([A-ZAEIOU][^?:]{50,})", t)
            if m:
                return m.group(1).strip()
        return t
 
    def _limpiar_para_tts(self, texto: str) -> str:
        """Elimina artefactos tecnicos que el TTS no puede leer bien."""
        t = texto or ""
        t = re.sub(r"https?://\S+", "", t)
        t = re.sub(r"www\.\S+", "", t)
        t = re.sub(
            r"\s*[|\-]\s*(YouTube|Spotify|Wikipedia|IBM|Forbes|BBC|CNN|"
            r"AccuWeather|Meteored|Instagram|TikTok)[^.]*",
            "", t, flags=re.IGNORECASE,
        )
        t = re.sub(r"\[\d+\]|\[cita[^\]]*\]|\[note[^\]]*\]", "", t)
        t = re.sub(r"[©®™°•·]", " ", t)
        t = re.sub(r"\s+", " ", t.replace("\n", " "))
        return t.strip()
 
    def _extraer_respuesta(self, texto: str, max_chars: int = 500) -> str:
        """
        Pipeline completo de extraccion:
        1. Saltar prefijo roto
        2. Limpiar artefactos tecnicos
        3. Saltar prefijo tipo 'Titulo: Contenido'
        4. Acumular oraciones buenas hasta max_chars
        """
        t = self._saltar_prefijo_roto(texto)
        t = self._limpiar_para_tts(t)
 
        match_prefijo = re.match(r"^[^.]{0,100}[?:]\s+([A-Z].{50,})", t)
        if match_prefijo:
            candidato = match_prefijo.group(1).strip()
            if len(candidato) > 80:
                t = candidato
 
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
 
        if not respuesta and oraciones:
            primera   = oraciones[0][:max_chars]
            ult_punto = primera.rfind(". ")
            respuesta = (
                primera[:ult_punto + 1] if ult_punto > 60
                else primera.rsplit(" ", 1)[0] + "..."
            )
 
        return respuesta.strip()
 
    def buscar_con_fallback(self, query: str) -> tuple:
        query           = self.normalizar_query(query)
        query_preparado = self._preparar_query(query)
 
        for p in self.providers:
            try:
                data = p.search(query_preparado)
                text = p.to_text(data)
                if text and len(text.strip()) >= 30:
                    return text.strip(), p.name
            except Exception as e:
                print(f"[SearchManager] {p.name} fallo: {e}")
                continue
 
        return "", "none"
 
    def resumir_es(self, texto: str, max_chars: int = 500) -> str:
        """Punto de entrada principal. Devuelve texto listo para TTS."""
        return self._extraer_respuesta(texto, max_chars=max_chars)