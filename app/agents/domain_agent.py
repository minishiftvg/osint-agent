# app/agents/domain_agent.py
# Agente specializzato per l'analisi tecnica di domini web.
# È l'agente più ricco di fonti: WHOIS, DNS, SSL, Shodan, ecc.

import asyncio
from app.models import OsintTarget, AgentReport
from app.sources import (
    whois_lookup, dns_lookup, crtsh,
    shodan_free, virustotal, wayback, ip_geo, duckduckgo
)


class DomainAgent:
    """
    Agente per analisi tecnica di domini.

    Fonti usate:
    - WHOIS: proprietario e date registrazione
    - DNS: record tecnici del dominio
    - crt.sh: certificati SSL e sottodomini
    - Shodan InternetDB: porte aperte e vulnerabilità
    - VirusTotal: reputazione sicurezza
    - Wayback Machine: storia del sito
    - IP Geolocalizzazione: posizione del server
    - DuckDuckGo: info generali online
    """

    async def investigate(self, target: OsintTarget) -> AgentReport:
        """
        Analisi tecnica completa di un dominio.

        Esegue alcune fonti in parallelo e altre in sequenza
        per rispettare i rate limit dei servizi gratuiti.

        Args:
            target: OsintTarget con type=DOMAIN

        Returns:
            AgentReport con tutti i risultati tecnici
        """
        domain = target.value
        # Normalizza: rimuovi protocollo se presente
        domain = domain.replace("https://", "").replace("http://", "")
        domain = domain.rstrip("/").split("/")[0]

        print(f"\n[DomainAgent] Analisi di: '{domain}'")

        report = AgentReport(target=target)

        # ── BATCH 1: Fonti veloci in parallelo ───────────────
        # Eseguiamo le fonti più veloci e affidabili insieme
        print("[DomainAgent] Batch 1: WHOIS, DNS, IP geo, Wayback...")
        batch1_results = await asyncio.gather(
            whois_lookup.lookup(domain),
            dns_lookup.lookup(domain),
            ip_geo.geolocate_domain(domain),
            wayback.check(domain),
            duckduckgo.search(f"sito {domain} informazioni"),
            return_exceptions=True
        )

        for result in batch1_results:
            if result and not isinstance(result, Exception):
                if result.success and result.data:
                    report.results.append(result)

        # Pausa per rispettare i rate limit
        await asyncio.sleep(2)

        # ── BATCH 2: Fonti che possono essere più lente ──────
        print("[DomainAgent] Batch 2: crt.sh, Shodan, VirusTotal...")
        batch2_results = await asyncio.gather(
            crtsh.find_subdomains(domain),
            shodan_free.scan_domain(domain),
            virustotal.check_domain(domain),
            return_exceptions=True
        )

        for result in batch2_results:
            if result and not isinstance(result, Exception):
                if result.success and result.data:
                    report.results.append(result)

        total = len(report.successful_results)
        print(f"[DomainAgent] Completato: {total} fonti con dati")

        return report
