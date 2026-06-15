# app/sources/whois_lookup.py
# Recupera informazioni WHOIS di un dominio.
#
# WHOIS (pronunciato "who is") è un protocollo che permette di
# conoscere chi ha registrato un dominio: nome, email, date
# di registrazione e scadenza, nameserver, ecc.
#
# Usiamo WhoisJSON API (1.000 req/mese gratis, no carta)
# con fallback su python-whois (libreria locale, sempre gratis).

import httpx
from app.config import config
from app.models import SourceResult


async def lookup(domain: str) -> SourceResult:
    """
    Recupera i dati WHOIS di un dominio.

    Flusso:
    1. Prova con WhoisJSON API (più dati, JSON strutturato)
    2. Se fallisce o non c'è la key, usa query WHOIS diretta

    Args:
        domain: Il dominio da analizzare (es. "google.com")

    Returns:
        SourceResult con i dati WHOIS
    """
    # ── Tentativo 1: WhoisJSON API ────────────────────────────
    if config.WHOISJSON_API_KEY:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.whoisjson.com/v1/whois",
                    params={"domain": domain},
                    headers={
                        "Authorization": f"TOKEN={config.WHOISJSON_API_KEY}"
                    },
                    timeout=12.0
                )

                if response.status_code == 200:
                    data = response.json()

                    # Estrai i campi più rilevanti per OSINT
                    result_parts = []
                    result_parts.append(f"Dominio: {domain}")

                    # Registrante (chi ha registrato il dominio)
                    if data.get("registrant_name"):
                        result_parts.append(
                            f"Registrante: {data['registrant_name']}"
                        )
                    if data.get("registrant_organization"):
                        result_parts.append(
                            f"Organizzazione: {data['registrant_organization']}"
                        )
                    if data.get("registrant_country"):
                        result_parts.append(
                            f"Paese: {data['registrant_country']}"
                        )

                    # Date importanti
                    if data.get("creation_date"):
                        result_parts.append(
                            f"Data registrazione: {data['creation_date']}"
                        )
                    if data.get("expiration_date"):
                        result_parts.append(
                            f"Data scadenza: {data['expiration_date']}"
                        )
                    if data.get("updated_date"):
                        result_parts.append(
                            f"Ultimo aggiornamento: {data['updated_date']}"
                        )

                    # Registrar
                    if data.get("registrar"):
                        result_parts.append(f"Registrar: {data['registrar']}")

                    # Nameserver (indica chi gestisce il DNS)
                    nameservers = data.get("name_servers", [])
                    if nameservers:
                        ns_list = ", ".join(nameservers[:4])
                        result_parts.append(f"Nameserver: {ns_list}")

                    # Status del dominio
                    statuses = data.get("status", [])
                    if statuses:
                        result_parts.append(f"Status: {', '.join(statuses[:2])}")

                    if result_parts:
                        return SourceResult(
                            source_name="WHOIS (WhoisJSON)",
                            data="\n".join(result_parts)
                        )

        except Exception as e:
            print(f"[WHOIS] WhoisJSON fallito: {e}")

    # ── Fallback: query WHOIS pubblica tramite rdap.org ───────
    # RDAP è il successore moderno di WHOIS, disponibile pubblicamente
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://rdap.org/domain/{domain}",
                headers={"Accept": "application/json"},
                timeout=12.0,
                follow_redirects=True
            )

            if response.status_code == 200:
                data = response.json()
                result_parts = [f"Dominio: {domain}"]

                # Estrai eventi (registrazione, scadenza, aggiornamento)
                for event in data.get("events", []):
                    action = event.get("eventAction", "")
                    date = event.get("eventDate", "")[:10]  # Solo la data
                    if action == "registration":
                        result_parts.append(f"Registrato: {date}")
                    elif action == "expiration":
                        result_parts.append(f"Scadenza: {date}")
                    elif action == "last changed":
                        result_parts.append(f"Aggiornato: {date}")

                # Estrai nameserver
                ns_list = [
                    ns.get("ldhName", "")
                    for ns in data.get("nameservers", [])[:4]
                ]
                if ns_list:
                    result_parts.append(f"Nameserver: {', '.join(ns_list)}")

                # Estrai entità (registrant, registrar)
                for entity in data.get("entities", []):
                    roles = entity.get("roles", [])
                    vcard = entity.get("vcardArray", [None, []])[1]

                    name = ""
                    for field in vcard:
                        if field[0] == "fn":
                            name = field[3]
                            break

                    if "registrant" in roles and name:
                        result_parts.append(f"Registrante: {name}")
                    elif "registrar" in roles and name:
                        result_parts.append(f"Registrar: {name}")

                return SourceResult(
                    source_name="WHOIS (RDAP)",
                    data="\n".join(result_parts)
                )

    except Exception as e:
        return SourceResult(
            source_name="WHOIS",
            data="",
            success=False,
            error=f"Entrambi i metodi WHOIS falliti: {str(e)}"
        )

    return SourceResult(
        source_name="WHOIS",
        data=f"Dati WHOIS non disponibili per {domain}"
    )
