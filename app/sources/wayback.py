# app/sources/wayback.py
# Controlla la storia di un dominio su Wayback Machine.
#
# COS'È WAYBACK MACHINE:
# archive.org/web è l'archivio storico di internet.
# Salva snapshot (fotografie) di pagine web nel tempo.
# Per OSINT: mostra quando un sito esiste, come è cambiato,
# se era un sito diverso in passato, ecc.
#
# Gratuito, senza chiave API, nella whitelist PythonAnywhere.

import httpx
from app.models import SourceResult


async def check(domain: str) -> SourceResult:
    """
    Controlla la presenza di un dominio su Wayback Machine.

    Args:
        domain: Il dominio da controllare

    Returns:
        SourceResult con informazioni storiche
    """
    try:
        async with httpx.AsyncClient() as client:
            # availability API: controlla se il sito è archiviato
            response = await client.get(
                "https://archive.org/wayback/available",
                params={"url": domain},
                timeout=12.0
            )

            if response.status_code == 200:
                data = response.json()
                snapshot = data.get("archived_snapshots", {}).get(
                    "closest", {}
                )

                result_parts = [f"Dominio: {domain}"]

                if snapshot and snapshot.get("available"):
                    result_parts.append(
                        f"✓ Sito archiviato su Wayback Machine"
                    )
                    # Data dello snapshot più vicino
                    timestamp = snapshot.get("timestamp", "")
                    if timestamp and len(timestamp) >= 8:
                        date_str = (
                            f"{timestamp[6:8]}/{timestamp[4:6]}/{timestamp[:4]}"
                        )
                        result_parts.append(
                            f"Snapshot più recente: {date_str}"
                        )
                    if snapshot.get("url"):
                        result_parts.append(
                            f"URL archivio: {snapshot['url']}"
                        )
                else:
                    result_parts.append(
                        "✗ Dominio non trovato su Wayback Machine"
                    )

                # CDX API: numero totale di snapshot
                cdx_response = await client.get(
                    "https://web.archive.org/cdx/search/cdx",
                    params={
                        "url": domain,
                        "output": "json",
                        "limit": "1",
                        "fl": "timestamp",
                        "from": "19960101"
                    },
                    timeout=10.0
                )

                if cdx_response.status_code == 200:
                    cdx_data = cdx_response.json()
                    if len(cdx_data) > 1:
                        # Primo risultato è l'header, poi i dati
                        first_snap = cdx_data[1][0] if len(cdx_data) > 1 else None
                        if first_snap:
                            year = first_snap[:4]
                            result_parts.append(
                                f"Prima archiviazione: {year}"
                            )

                return SourceResult(
                    source_name="Wayback Machine",
                    data="\n".join(result_parts)
                )

    except Exception as e:
        return SourceResult(
            source_name="Wayback Machine",
            data="",
            success=False,
            error=str(e)
        )
