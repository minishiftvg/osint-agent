# app/agents/report_writer.py
# Il ReportWriter sintetizza tutti i dati raccolti dagli agenti
# in un report professionale con Risk Score.
#
# STRUTTURA DEL REPORT:
# - Executive Summary: panoramica in 3-4 frasi per chi legge veloce
# - Findings: dati organizzati per categoria
# - Risk Score: 0-100 calcolato su fattori oggettivi
# - Risk Level: LOW/MEDIUM/HIGH/CRITICAL
# - Recommendations: azioni concrete da intraprendere

import json
from app.models import AgentReport, FinalReport, OsintTarget, TargetType
from app.llm_client import call_gemini

WRITER_PROMPT = """Sei un analista di intelligence OSINT senior.
Ricevi dati grezzi da fonti multiple su un target e devi produrre
un report di intelligence professionale.

ISTRUZIONI:
1. Analizza TUTTI i dati forniti attentamente
2. Sintetizza le informazioni più rilevanti per categoria
3. Calcola un Risk Score oggettivo 0-100 basato su:
   - 0-20: Nessuna anomalia rilevata (LOW)
   - 21-40: Alcune informazioni da monitorare (LOW-MEDIUM)
   - 41-60: Presenza di elementi di attenzione (MEDIUM)
   - 61-80: Fattori di rischio significativi (HIGH)
   - 81-100: Rischi critici immediati (CRITICAL)
4. Per DOMINI considera: porte aperte, CVE, reputazione VirusTotal
5. Per PERSONE/AZIENDE considera: controversie, presenze negative, anomalie
6. Produci raccomandazioni CONCRETE e ACTIONABLE
7. Rispondi SOLO con JSON valido, nessun testo aggiuntivo

FORMATO JSON OBBLIGATORIO:
{
  "executive_summary": "3-4 frasi che descrivono il target e i finding principali",
  "findings": [
    {
      "category": "Nome Categoria",
      "items": ["trovato 1", "trovato 2", "trovato 3"]
    }
  ],
  "risk_score": 45,
  "risk_level": "MEDIUM",
  "recommendations": [
    "raccomandazione concreta 1",
    "raccomandazione concreta 2"
  ],
  "raw_data_summary": "riepilogo tecnico dei dati principali in 2-3 frasi"
}"""


class ReportWriter:
    """
    Agente che produce il report finale professionale.
    """

    async def write(
        self,
        target: OsintTarget,
        agent_reports: list
    ) -> FinalReport:
        """
        Genera il report finale da tutti i dati raccolti.

        Args:
            target:       Il target investigato
            agent_reports: Lista di AgentReport dagli agenti

        Returns:
            FinalReport con report professionale completo
        """
        print(f"\n[ReportWriter] Generazione report per '{target.value}'")

        # Combina tutti i dati in un unico testo
        combined_data = self._combine_reports(agent_reports)
        char_count = len(combined_data)
        print(f"[ReportWriter] Dati da analizzare: {char_count} caratteri")

        # Limita i dati per non superare il context window di Gemini
        if char_count > 8000:
            combined_data = combined_data[:8000] + "\n[dati troncati per limite]"

        # Chiedi a Gemini di produrre il report
        raw_output = call_gemini(
            system_prompt=WRITER_PROMPT,
            user_message=(
                f"TARGET: {target.value} ({target.type.value})\n\n"
                f"DATI RACCOLTI:\n{combined_data}"
            ),
            max_tokens=2000,
            temperature=0.2
        )

        print(f"[ReportWriter] Report generato: {len(raw_output)} caratteri")

        # Parsa il JSON del report
        report_data = self._parse_json(raw_output, target)

        return FinalReport(
            target_value=target.value,
            target_type=target.type.value,
            executive_summary=report_data.get("executive_summary", ""),
            findings=report_data.get("findings", []),
            risk_score=min(100, max(0, int(report_data.get("risk_score", 0)))),
            risk_level=report_data.get("risk_level", "LOW"),
            recommendations=report_data.get("recommendations", []),
            raw_data_summary=report_data.get("raw_data_summary", "")
        )

    def _combine_reports(self, agent_reports: list) -> str:
        """Combina tutti i report degli agenti in un unico testo."""
        sections = []
        for agent_report in agent_reports:
            if agent_report.successful_results:
                sections.append(agent_report.to_text())
        return "\n\n".join(sections)

    def _parse_json(self, raw_output: str, target: OsintTarget) -> dict:
        """Parsa il JSON con gestione errori e fallback."""
        cleaned = raw_output.strip()

        if "```" in cleaned:
            start = cleaned.find("```")
            end = cleaned.rfind("```")
            if start != end:
                cleaned = "\n".join(cleaned[start:end].split("\n")[1:])

        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start >= 0 and end > start:
            cleaned = cleaned[start:end]

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            print("[ReportWriter] Errore JSON, uso fallback")
            return {
                "executive_summary": f"Report OSINT per {target.value}. "
                                    f"Analisi completata con dati parziali.",
                "findings": [
                    {"category": "Analisi", "items": [raw_output[:300]]}
                ],
                "risk_score": 0,
                "risk_level": "LOW",
                "recommendations": ["Rianalizzare il target con più dati"],
                "raw_data_summary": "Dati parziali disponibili."
            }
