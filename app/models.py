# app/models.py
# Strutture dati del sistema OSINT.
#
# Usiamo dataclass per rappresentare i dati in modo chiaro e tipizzato.
# Ogni dataclass è come un "contenitore" con campi ben definiti.

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class TargetType(Enum):
    """
    Tipo di soggetto da investigare.
    PERSON  = persona fisica pubblica
    COMPANY = azienda o organizzazione
    DOMAIN  = dominio web / infrastruttura digitale
    """
    PERSON = "person"
    COMPANY = "company"
    DOMAIN = "domain"


@dataclass
class OsintTarget:
    """
    Il soggetto da investigare.

    Viene creato dal Coordinator dopo aver analizzato
    il comando dell'utente.

    Esempi:
        OsintTarget(type=TargetType.DOMAIN, value="google.com")
        OsintTarget(type=TargetType.PERSON, value="Mario Rossi")
    """
    type: TargetType      # Tipo: PERSON, COMPANY o DOMAIN
    value: str            # Il valore da ricercare
    context: str = ""     # Contesto aggiuntivo (es. "CEO di Acme")


@dataclass
class SourceResult:
    """
    Risultato di una singola fonte OSINT.

    Ogni tool (DuckDuckGo, WHOIS, crt.sh...) produce un SourceResult.
    La pipeline li raccoglie tutti e li passa al ReportWriter.

    Attributi:
        source_name:   Nome della fonte (es. "WHOIS", "DuckDuckGo")
        data:          Dati grezzi raccolti (testo o dict convertito)
        success:       True se la fonte ha risposto correttamente
        error:         Messaggio di errore se success=False
    """
    source_name: str
    data: str
    success: bool = True
    error: str = ""


@dataclass
class AgentReport:
    """
    Report prodotto da un singolo agente (Person, Company o Domain).
    Contiene tutti i SourceResult raccolti dall'agente.
    """
    target: OsintTarget
    results: list = field(default_factory=list)  # Lista di SourceResult

    @property
    def successful_results(self) -> list:
        """Solo i risultati con successo=True."""
        return [r for r in self.results if r.success]

    def to_text(self) -> str:
        """
        Converte i risultati in testo per il ReportWriter.
        Ogni risultato viene formattato con il nome della fonte
        e i dati raccolti.
        """
        lines = [f"TARGET: {self.target.value} ({self.target.type.value})\n"]
        for r in self.successful_results:
            lines.append(f"=== {r.source_name} ===")
            lines.append(r.data)
            lines.append("")
        return "\n".join(lines)


@dataclass
class FinalReport:
    """
    Il report finale professionale generato dal ReportWriter.

    Struttura professionale:
    - executive_summary: visione d'insieme in 3-4 frasi
    - findings:          lista di categorie con trovati specifici
    - risk_score:        punteggio 0-100 (0=nessun rischio, 100=alto rischio)
    - risk_level:        LOW / MEDIUM / HIGH / CRITICAL
    - recommendations:   cosa fare in base ai trovati
    - raw_data_summary:  riepilogo dati tecnici
    """
    target_value: str
    target_type: str
    executive_summary: str
    findings: list          # [{"category": "...", "items": ["..."]}]
    risk_score: int         # 0-100
    risk_level: str         # LOW / MEDIUM / HIGH / CRITICAL
    recommendations: list   # ["raccomandazione 1", ...]
    raw_data_summary: str   # Riepilogo tecnico

    def risk_emoji(self) -> str:
        """Emoji corrispondente al livello di rischio."""
        return {
            "LOW": "🟢",
            "MEDIUM": "🟡",
            "HIGH": "🟠",
            "CRITICAL": "🔴"
        }.get(self.risk_level, "⚪")

    def to_telegram(self) -> list:
        """
        Formatta il report per Telegram.

        Telegram ha un limite di 4096 caratteri per messaggio.
        Restituisce una LISTA di messaggi se il report è lungo,
        così possiamo inviare più messaggi in sequenza.

        Returns:
            Lista di stringhe, ognuna ≤ 4000 caratteri
        """
        messages = []

        # ── Messaggio 1: Header + Executive Summary ──────────
        msg1 = []
        msg1.append(
            f"🔍 *OSINT REPORT*\n"
            f"Target: `{self.target_value}`\n"
            f"Tipo: {self.target_type.upper()}\n"
            f"{self.risk_emoji()} *Risk Score: {self.risk_score}/100 "
            f"({self.risk_level})*\n"
        )
        msg1.append("📋 *Executive Summary*")
        msg1.append(self.executive_summary)
        messages.append("\n".join(msg1))

        # ── Messaggio 2: Findings ─────────────────────────────
        msg2 = ["📊 *Findings Dettagliati*\n"]
        for finding in self.findings:
            category = finding.get("category", "")
            items = finding.get("items", [])
            msg2.append(f"*{category}*")
            for item in items:
                msg2.append(f"  • {item}")
            msg2.append("")

        findings_text = "\n".join(msg2)
        # Se troppo lungo, tronca
        if len(findings_text) > 3900:
            findings_text = findings_text[:3800] + "\n_[troncato]_"
        messages.append(findings_text)

        # ── Messaggio 3: Raccomandazioni + Dati tecnici ───────
        msg3 = []
        if self.recommendations:
            msg3.append("✅ *Raccomandazioni*")
            for rec in self.recommendations:
                msg3.append(f"• {rec}")
            msg3.append("")

        if self.raw_data_summary:
            msg3.append("🔧 *Dati Tecnici*")
            # Limite lunghezza per dati tecnici
            tech_summary = self.raw_data_summary[:800]
            msg3.append(f"`{tech_summary}`")

        messages.append("\n".join(msg3))

        return messages

    def to_email_html(self) -> str:
        """
        Genera il report in formato HTML per l'email.
        Make.com invierà questo HTML tramite Gmail.
        """
        risk_colors = {
            "LOW": "#28a745",
            "MEDIUM": "#ffc107",
            "HIGH": "#fd7e14",
            "CRITICAL": "#dc3545"
        }
        color = risk_colors.get(self.risk_level, "#6c757d")

        findings_html = ""
        for finding in self.findings:
            category = finding.get("category", "")
            items = finding.get("items", [])
            items_html = "".join(f"<li>{item}</li>" for item in items)
            findings_html += f"""
            <h3 style="color:#333;">{category}</h3>
            <ul>{items_html}</ul>
            """

        recs_html = "".join(
            f"<li>{rec}</li>" for rec in self.recommendations
        )

        return f"""
        <html><body style="font-family: Arial, sans-serif; max-width: 800px; margin: auto; padding: 20px;">
        <h1 style="color:#1a1a2e; border-bottom: 2px solid #e0e0e0; padding-bottom: 10px;">
            🔍 OSINT Intelligence Report
        </h1>

        <table style="width:100%; background:#f8f9fa; padding:15px; border-radius:8px; margin-bottom:20px;">
            <tr>
                <td><strong>Target:</strong> {self.target_value}</td>
                <td><strong>Tipo:</strong> {self.target_type.upper()}</td>
            </tr>
            <tr>
                <td colspan="2">
                    <strong>Risk Score:</strong>
                    <span style="background:{color}; color:white; padding:3px 10px;
                                border-radius:12px; font-weight:bold;">
                        {self.risk_score}/100 — {self.risk_level}
                    </span>
                </td>
            </tr>
        </table>

        <h2>📋 Executive Summary</h2>
        <p style="background:#e8f4f8; padding:15px; border-left:4px solid #007bff;
                  border-radius:4px;">
            {self.executive_summary}
        </p>

        <h2>📊 Findings</h2>
        {findings_html}

        <h2>✅ Raccomandazioni</h2>
        <ul>{recs_html}</ul>

        <h2>🔧 Dati Tecnici</h2>
        <pre style="background:#f4f4f4; padding:15px; border-radius:4px;
                    font-size:12px; overflow-x:auto;">
{self.raw_data_summary[:1500]}
        </pre>

        <hr style="margin-top:30px;">
        <p style="color:#999; font-size:12px;">
            Report generato automaticamente dal sistema OSINT Intelligence.
            Tutte le informazioni provengono da fonti pubblicamente disponibili.
        </p>
        </body></html>
        """
