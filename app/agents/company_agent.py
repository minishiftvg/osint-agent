# app/agents/company_agent.py
# Agente specializzato per ricerche su aziende e organizzazioni.

import asyncio
from app.models import OsintTarget, AgentReport
from app.sources import duckduckgo, wikipedia


class CompanyAgent:
    """
    Agente per ricerche su aziende.
    Fonti: DuckDuckGo (notizie, info), Wikipedia (enciclopedica)
    """

    async def investigate(self, target: OsintTarget) -> AgentReport:
        """
        Raccoglie informazioni pubbliche su un'azienda.

        Args:
            target: OsintTarget con type=COMPANY

        Returns:
            AgentReport con tutti i risultati
        """
        company = target.value
        print(f"\n[CompanyAgent] Investigazione su: '{company}'")

        report = AgentReport(target=target)

        results = await asyncio.gather(
            # Info generali sull'azienda
            duckduckgo.search(company),
            # Wikipedia
            wikipedia.search(company),
            # Notizie recenti
            duckduckgo.search(f"{company} notizie 2024 2025"),
            # Leadership e struttura
            duckduckgo.search(f"{company} CEO fondatore storia"),
            # Controversie o problemi
            duckduckgo.search(f"{company} problemi controversie"),
            return_exceptions=False
        )

        for result in results:
            if result and result.success and result.data:
                report.results.append(result)

        print(
            f"[CompanyAgent] Completato: "
            f"{len(report.successful_results)} fonti"
        )

        return report
