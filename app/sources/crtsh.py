# app/sources/crtsh.py
# Cerca certificati SSL e sottodomini su crt.sh.
#
# COS'È crt.sh:
# È un registro pubblico di tutti i certificati SSL/TLS emessi.
# Per legge (Certificate Transparency), ogni certificato SSL
# deve essere registrato pubblicamente. crt.sh è un database
# di questi certificati — gratuito e senza chiave API.
#
# PERCHÉ È UTILE PER OSINT:
# Rivelano sottodomini nascosti! Se un'azienda ha certificati per
# "mail.azienda.com", "vpn.azienda.com", "dev.azienda.com"
# questi appaiono in crt.sh anche se non linkati dal sito principale.
# Questo è uno dei tool OSINT più potenti per la ricognizione.

import httpx
from app.models import SourceResult


async def find_subdomains(domain: str) -> SourceResult:
    """
    Trova tutti i sottodomini di un dominio tramite crt.sh.

    La query %.dominio.com cerca certificati per qualsiasi
    sottodominio di dominio.com.

    Args:
        domain: Il dominio principale (es. "acmecorp.com")

    Returns:
        SourceResult con lista di sottodomini trovati
    """
    try:
        async with httpx.AsyncClient() as client:
            # %.domain cerca tutti i sottodomini del dominio
            response = await client.get(
                "https://crt.sh/",
                params={
                    "q": f"%.{domain}",
                    "output": "json"
                },
                headers={
                    # User-Agent necessario per evitare blocchi
                    "User-Agent": "Mozilla/5.0 OSINT-Research"
                },
                timeout=20.0,  # crt.sh può essere lento
                follow_redirects=True
            )

            if response.status_code == 200:
                certs = response.json()

                # Raccogli tutti i sottodomini unici
                subdomains = set()

                for cert in certs:
                    # name_value può contenere più nomi separati da \n
                    name_value = cert.get("name_value", "")
                    for name in name_value.split("\n"):
                        name = name.strip().lower()
                        # Filtriamo:
                        # - Wildcard (*.dominio.com)
                        # - Nomi che contengono il dominio target
                        if name and domain in name and not name.startswith("*"):
                            subdomains.add(name)

                if subdomains:
                    # Ordina e prendi i primi 20
                    sorted_subs = sorted(subdomains)[:20]
                    result_text = (
                        f"Sottodomini trovati per {domain} "
                        f"({len(subdomains)} totali, mostro i primi 20):\n"
                    )
                    for sub in sorted_subs:
                        result_text += f"• {sub}\n"

                    # Informazioni aggiuntive sui certificati
                    # Conta certificati per capire la "storia" del dominio
                    total_certs = len(certs)
                    result_text += f"\nCertificati SSL totali emessi: {total_certs}"

                    return SourceResult(
                        source_name="crt.sh (Certificati SSL)",
                        data=result_text
                    )

                return SourceResult(
                    source_name="crt.sh (Certificati SSL)",
                    data=f"Nessun sottodominio trovato per {domain}"
                )

    except httpx.TimeoutException:
        return SourceResult(
            source_name="crt.sh",
            data="crt.sh timeout (il servizio può essere lento)",
            success=False,
            error="Timeout"
        )
    except Exception as e:
        return SourceResult(
            source_name="crt.sh",
            data="",
            success=False,
            error=str(e)
        )
