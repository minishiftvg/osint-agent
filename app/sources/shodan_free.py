# app/sources/shodan_free.py
# Usa Shodan InternetDB — API pubblica GRATUITA, senza chiave.
#
# COS'È SHODAN:
# Shodan è un motore di ricerca per dispositivi connessi a internet.
# Scansiona continuamente tutto internet e registra quali porte
# sono aperte su ogni IP e quali vulnerabilità sono note.
#
# COS'È InternetDB:
# internetdb.shodan.io è una versione semplificata e pubblica
# di Shodan — gratuita, senza registrazione, senza chiave API.
# Fornisce: porte aperte, CVE (vulnerabilità note), hostname.
#
# IMPORTANTE ETICO:
# Queste informazioni sono già pubbliche — Shodan le ha scansionate.
# Non stiamo "attaccando" nessun sistema, stiamo solo leggendo
# un database pubblico di informazioni già raccolte.

import httpx
import socket
from app.models import SourceResult


async def scan_domain(domain: str) -> SourceResult:
    """
    Recupera informazioni di sicurezza per un dominio tramite Shodan InternetDB.

    Flusso:
    1. Risolve il dominio in indirizzo IP
    2. Interroga Shodan InternetDB per quell'IP
    3. Restituisce porte aperte, vulnerabilità, hostname

    Args:
        domain: Il dominio da analizzare

    Returns:
        SourceResult con informazioni di sicurezza
    """
    try:
        # Step 1: Risolvi il dominio in IP
        try:
            ip = socket.gethostbyname(domain)
        except socket.gaierror:
            return SourceResult(
                source_name="Shodan InternetDB",
                data=f"Impossibile risolvere IP per {domain}",
                success=False,
                error="DNS resolution failed"
            )

        # Step 2: Interroga Shodan InternetDB
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://internetdb.shodan.io/{ip}",
                timeout=10.0
            )

            if response.status_code == 200:
                data = response.json()

                result_parts = [
                    f"IP analizzato: {ip} (per {domain})"
                ]

                # Porte aperte: servizi in ascolto
                ports = data.get("ports", [])
                if ports:
                    # Aggiungi descrizione per le porte più comuni
                    port_descriptions = {
                        21: "FTP", 22: "SSH", 23: "Telnet",
                        25: "SMTP", 53: "DNS", 80: "HTTP",
                        110: "POP3", 143: "IMAP", 443: "HTTPS",
                        3306: "MySQL", 5432: "PostgreSQL",
                        6379: "Redis", 8080: "HTTP-Alt",
                        8443: "HTTPS-Alt", 27017: "MongoDB"
                    }
                    port_list = []
                    for port in sorted(ports):
                        desc = port_descriptions.get(port, "")
                        port_list.append(
                            f"{port}/{desc}" if desc else str(port)
                        )
                    result_parts.append(
                        f"Porte aperte ({len(ports)}): {', '.join(port_list)}"
                    )

                # CVE: vulnerabilità note (Critical Vulnerability Enumeration)
                vulns = data.get("vulns", [])
                if vulns:
                    # Le CVE sono identificatori standard (es. CVE-2021-44228)
                    result_parts.append(
                        f"⚠️ Vulnerabilità note (CVE): {', '.join(vulns[:5])}"
                    )
                    if len(vulns) > 5:
                        result_parts.append(
                            f"  ... e altre {len(vulns)-5} vulnerabilità"
                        )

                # Hostname: altri nomi che puntano allo stesso IP
                hostnames = data.get("hostnames", [])
                if hostnames:
                    result_parts.append(
                        f"Hostname associati: {', '.join(hostnames[:5])}"
                    )

                # Tag: categorie assegnate da Shodan
                tags = data.get("tags", [])
                if tags:
                    result_parts.append(f"Tag Shodan: {', '.join(tags)}")

                # Se nessun dato trovato
                if len(result_parts) == 1:
                    result_parts.append(
                        "Nessun dato disponibile (IP non scansionato da Shodan)"
                    )

                return SourceResult(
                    source_name="Shodan InternetDB",
                    data="\n".join(result_parts)
                )

            elif response.status_code == 404:
                # IP non nel database Shodan
                return SourceResult(
                    source_name="Shodan InternetDB",
                    data=f"IP {ip} non nel database Shodan (bassa esposizione)"
                )

    except Exception as e:
        return SourceResult(
            source_name="Shodan InternetDB",
            data="",
            success=False,
            error=str(e)
        )
