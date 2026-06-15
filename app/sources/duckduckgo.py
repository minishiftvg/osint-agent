# app/sources/duckduckgo.py
# Ricerca web generica tramite DuckDuckGo Instant Answers API.
# Gratuito, nessuna chiave, nella whitelist PythonAnywhere.

import httpx
import asyncio
from app.models import SourceResult


async def search(query: str, context: str = "") -> SourceResult:
    """
    Cerca informazioni su DuckDuckGo.

    Args:
        query:   Stringa di ricerca
        context: Contesto aggiuntivo per affinare la ricerca

    Returns:
        SourceResult con i dati trovati
    """
    full_query = f"{query} {context}".strip() if context else query

    for attempt in range(3):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.duckduckgo.com/",
                    params={
                        "q": full_query,
                        "format": "json",
                        "no_html": "1",
                        "skip_disambig": "1"
                    },
                    timeout=12.0
                )

                if response.status_code == 200:
                    data = response.json()
                    results = []

                    if data.get("Abstract"):
                        results.append(f"Abstract: {data['Abstract']}")
                        if data.get("AbstractURL"):
                            results.append(f"Fonte: {data['AbstractURL']}")

                    # Prendi i migliori 5 risultati correlati
                    for topic in data.get("RelatedTopics", [])[:5]:
                        if isinstance(topic, dict) and topic.get("Text"):
                            results.append(f"• {topic['Text']}")

                    if data.get("Answer"):
                        results.append(f"Risposta diretta: {data['Answer']}")

                    if results:
                        return SourceResult(
                            source_name="DuckDuckGo",
                            data="\n".join(results)
                        )
                    return SourceResult(
                        source_name="DuckDuckGo",
                        data=f"Nessun risultato specifico per: {full_query}"
                    )

        except httpx.TimeoutException:
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)
        except Exception as e:
            return SourceResult(
                source_name="DuckDuckGo",
                data="",
                success=False,
                error=str(e)
            )

    return SourceResult(
        source_name="DuckDuckGo",
        data="",
        success=False,
        error="Timeout dopo 3 tentativi"
    )