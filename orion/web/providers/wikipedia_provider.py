# orion/web/providers/wikipedia_provider.py
import re
import urllib.parse
import urllib.request
import json

_HEADERS = {
    "User-Agent": "ORION-Assistant/1.0 (Raspberry Pi; educational project)"
}


class WikipediaProvider:
    name = "wikipedia"

    def available(self) -> bool:
        return True

    def search(self, query: str, max_results: int = 3) -> dict:
        query_enc = urllib.parse.quote(query.strip())

        # Paso 1: buscar título más relevante (action=query&list=search)
        search_url = (
            "https://es.wikipedia.org/w/api.php"
            f"?action=query&list=search&format=json&srsearch={query_enc}"
            "&srnamespace=0&srlimit=1&utf8=1"
        )
        try:
            req = urllib.request.Request(search_url, headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=8) as r:
                search_data = json.loads(r.read().decode("utf-8"))
        except Exception as e:
            print(f"[Wikipedia] Error búsqueda: {e}")
            return {}

        resultados = (search_data.get("query") or {}).get("search") or []
        if not resultados:
            print(f"[Wikipedia] Sin resultados para: {query}")
            return {}

        titulo = resultados[0].get("title", "")
        if not titulo:
            return {}

        # Paso 2: obtener introducción del artículo
        titulo_enc = urllib.parse.quote(titulo)
        extract_url = (
            "https://es.wikipedia.org/w/api.php"
            f"?action=query&format=json&titles={titulo_enc}"
            "&prop=extracts&exintro=1&explaintext=1&redirects=1&utf8=1"
        )
        try:
            req = urllib.request.Request(extract_url, headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=8) as r:
                extract_data = json.loads(r.read().decode("utf-8"))
        except Exception as e:
            print(f"[Wikipedia] Error extracto: {e}")
            return {}

        pages = (extract_data.get("query") or {}).get("pages") or {}
        for page in pages.values():
            extract = (page.get("extract") or "").strip()
            if extract and len(extract) > 50:
                print(f"[Wikipedia] Artículo encontrado: '{titulo}'")
                return {"titulo": titulo, "extract": extract}

        return {}

    def to_text(self, data: dict) -> str:
        extract = (data.get("extract") or "").strip()
        if not extract:
            return ""
        extract = re.sub(r"==+[^=]+=+\n?", " ", extract)
        extract = re.sub(r"\s+", " ", extract)
        return extract[:600].strip()