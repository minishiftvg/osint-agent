# app/sources/wikipedia.py
# Recupera informazioni da Wikipedia tramite API pubblica.
# Gratuito, nessuna chiave richiesta.
# Ottimo per persone e aziende famose.

import httpx
from app.models import SourceResult

async def search(query: str) -> SourceResult:
    """
    Cerca un argomento su Wikipedia e restituisce il summary.
    L'API Wikipedia restituisce il summary della pagina
    (i primi paragrafi) — perfetto per info di base.
    Args:
        query: Nome della persona o azienda da cercare
    Returns:
        SourceResult con il summary Wikipedia
    """
    try:
        async with httpx.AsyncClient() as client:
            # Cerca le pagine corrispondenti alla query
            search_response = await client.get(
                "https://en.wikipedia.org/api/rest_v1/page/summary/" +
                query.replace(" ", "_"),
                headers={"User-Agent": "OSINT-Agent/1.0"},
                timeout=10.0,
                follow_redirects=True
            )

            if search_response.status_code == 200:
                data = search_response.json()

                # Estrai le informazioni più rilevanti
                result_parts = []

                if data.get("title"):
                    result_parts.append(f"Titolo: {data['title']}")

                if data.get("description"):
                    result_parts.append(f"Descrizione: {data['description']}")

                if data.get("extract"):
                    # Prendi i primi 500 caratteri del testo
                    extract = data["extract"][:500]
                    result_parts.append(f"Estratto: {extract}")

                if data.get("content_urls", {}).get("desktop", {}).get("page"):
                    result_parts.append(
                        f"URL: {data['content_urls']['desktop']['page']}"
                    )

                if result_parts:
                    return SourceResult(
                        source_name="Wikipedia",
                        data="\n".join(result_parts)
                    )

            # Prova con Wikipedia in italiano se inglese non trova nulla
            it_response = await client.get(
                "https://it.wikipedia.org/api/rest_v1/page/summary/" +
                query.replace(" ", "_"),
                headers={"User-Agent": "OSINT-Agent/1.0"},
                timeout=10.0,
                follow_redirects=True
            )

            if it_response.status_code == 200:
                data = it_response.json()
                if data.get("extract"):
                    return SourceResult(
                        source_name="Wikipedia (IT)",
                        data=data["extract"][:500]
                    )

            return SourceResult(
                source_name="Wikipedia",
                data=f"Nessuna pagina Wikipedia trovata per: {query}"
            )

    except Exception as e:
        return SourceResult(
            source_name="Wikipedia",
            data="",
            success=False,
            error=str(e)
        )
