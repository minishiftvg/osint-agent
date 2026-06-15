# app/sources/dns_lookup.py
# Recupera i record DNS di un dominio.
#
# DNS (Domain Name System) è il "registro" di internet.
# Ogni dominio ha record che indicano:
# - Record A:    indirizzo IP del server web
# - Record MX:   server di posta elettronica
# - Record TXT:  verifiche di proprietà, SPF, DMARC
# - Record NS:   nameserver del dominio
# - Record CNAME: alias verso altri domini
#
# Usiamo dnspython (libreria Python) che usa i resolver DNS
# pubblici (Google 8.8.8.8, Cloudflare 1.1.1.1) — gratis.

import asyncio
import socket
from app.models import SourceResult

# Importa dnspython se disponibile
try:
    import dns.resolver
    import dns.exception
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False
    print("[DNS] dnspython non installato, uso socket come fallback")


async def lookup(domain: str) -> SourceResult:
    """
    Recupera i record DNS principali di un dominio.

    Args:
        domain: Il dominio da analizzare

    Returns:
        SourceResult con i record DNS trovati
    """
    # Esegui la query DNS in un thread separato
    # (le query DNS sono sincrone, non async)
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _dns_lookup_sync, domain)
    return result


def _dns_lookup_sync(domain: str) -> SourceResult:
    """
    Versione sincrona del DNS lookup (eseguita in thread pool).
    """
    results = [f"Dominio: {domain}"]
    found_data = False

    if DNS_AVAILABLE:
        # ── Usa dnspython per lookup completo ────────────────
        record_types = {
            "A": "Indirizzi IP",
            "MX": "Server email (MX)",
            "TXT": "Record TXT (SPF/DMARC/verifica)",
            "NS": "Nameserver",
            "AAAA": "Indirizzi IPv6",
            "CNAME": "Alias CNAME"
        }

        resolver = dns.resolver.Resolver()
        # Usa resolver pubblici affidabili
        resolver.nameservers = ["8.8.8.8", "1.1.1.1"]
        resolver.timeout = 5
        resolver.lifetime = 10

        for record_type, description in record_types.items():
            try:
                answers = resolver.resolve(domain, record_type)
                values = []

                for rdata in answers:
                    if record_type == "MX":
                        # MX ha priorità e server
                        values.append(
                            f"{rdata.preference} {rdata.exchange.to_text()}"
                        )
                    elif record_type == "TXT":
                        # TXT può contenere SPF, DMARC, verifica Google, ecc.
                        txt_value = rdata.to_text().strip('"')
                        # Tronca se troppo lungo
                        values.append(txt_value[:100])
                    else:
                        values.append(rdata.to_text())

                if values:
                    results.append(f"{description}: {', '.join(values[:3])}")
                    found_data = True

            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer,
                    dns.exception.Timeout):
                pass  # Record non esistente o timeout: normale
            except Exception:
                pass

    else:
        # ── Fallback: socket Python (solo record A) ───────────
        # socket.getaddrinfo risolve il dominio usando il resolver di sistema
        try:
            addr_info = socket.getaddrinfo(domain, None)
            ips = list(set(info[4][0] for info in addr_info))
            if ips:
                results.append(f"Indirizzi IP: {', '.join(ips[:3])}")
                found_data = True
        except socket.gaierror as e:
            return SourceResult(
                source_name="DNS",
                data="",
                success=False,
                error=f"Dominio non risolvibile: {str(e)}"
            )

    if not found_data:
        results.append("Nessun record DNS trovato (dominio potrebbe non esistere)")

    return SourceResult(
        source_name="DNS Records",
        data="\n".join(results)
    )
