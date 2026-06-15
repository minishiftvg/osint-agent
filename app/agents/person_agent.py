# app/agents/person_agent.py
# Agente specializzato per la ricerca su persone pubbliche.
# Raccoglie informazioni da fonti pubbliche: DuckDuckGo, Wikipedia.
#
# IMPORTANTE ETICO:
# Questo agente raccoglie SOLO informazioni pubblicamente disponibili.
# Non accede a database privati, non fa scraping di profili privati,
# non usa dati personali protetti da GDPR.

import asyncio
from app.models import OsintTarget, AgentReport
from app.sources import duckduckgo, wikipedia


class PersonAgent:
    """
    Agente per ricerche su persone pubbliche.
    Fonti: DuckDuckGo (notizie, menzioni), Wikipedia (info enciclopediche)
    """

    async def investigate(self, target: OsintTarget) -> AgentReport:
        """
        Raccoglie informazioni pubbliche su una persona.

        Args:
            target: OsintTarget con type=PERSON e value=nome

        Returns:
            AgentReport con tutti i risultati raccolti
        """
        name = target.value
        print(f"\n[PersonAgent] Investigazione su: '{name}'")

        report = AgentReport(target=target)

        # Esegui ricerche in parallelo per velocità
        # asyncio.gather() esegue tutte le coroutine contemporaneamente
        # e raccoglie i risultati quando tutte sono completate
        results = await asyncio.gather(
            # Ricerca generale
            duckduckgo.search(name),
            # Ricerca Wikipedia
            wikipedia.search(name),
            # Ricerca notizie recenti
            duckduckgo.search(f"{name} notizie 2024 2025"),
            # Ricerca profili pubblici
            duckduckgo.search(f"{name} profilo LinkedIn Twitter"),
            # Per le gather usiamo return_exceptions per gestire errori
            return_exceptions=False
        )

        # Aggiungi i risultati al report
        for result in results:
            if result and result.success and result.data:
                report.results.append(result)

        print(
            f"[PersonAgent] Completato: "
            f"{len(report.successful_results)} fonti con dati"
        )

        return report
