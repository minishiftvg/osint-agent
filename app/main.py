# app/main.py
# Server Flask principale con endpoint per Make.com.

from flask import Flask, request, jsonify
from app.config import config
from app.telegram_sender import send_message, send_typing
from app.agents.coordinator import Coordinator
from app.agents.person_agent import PersonAgent
from app.agents.company_agent import CompanyAgent
from app.agents.domain_agent import DomainAgent
from app.agents.report_writer import ReportWriter
from app.models import TargetType
import asyncio
import threading
import time

app = Flask(__name__)

# Inizializza gli agenti una sola volta all'avvio
coordinator = Coordinator()
person_agent = PersonAgent()
company_agent = CompanyAgent()
domain_agent = DomainAgent()
report_writer = ReportWriter()


def check_auth() -> bool:
    """Verifica autenticazione richiesta."""
    return request.headers.get("X-Webhook-Secret", "") == config.WEBHOOK_SECRET


def run_async(coro):
    """Esegue coroutine async in contesto sincrono."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def run_osint_pipeline(command: str, chat_id: str, email: str = "") -> None:
    """
    Pipeline OSINT completa:
    Coordinator → [PersonAgent, CompanyAgent, DomainAgent] → ReportWriter

    Args:
        command:  Comando dell'utente (es. "dominio: google.com")
        chat_id:  ID chat Telegram per la risposta
        email:    Email per invio report (opzionale)
    """
    print(f"\n{'='*60}")
    print(f"[Pipeline] Avvio OSINT per: '{command}'")
    print(f"{'='*60}")

    start_time = time.time()

    try:
        # Mostra "sta scrivendo..."
        await send_typing(chat_id)

        # Messaggio di avvio ricevuto dall'utente
        await send_message(
            chat_id,
            f"🔍 *OSINT avviato*\n"
            f"Comando: `{command}`\n"
            f"_Raccolta dati in corso... (30-60 secondi)_"
        )

        # ── FASE 1: COORDINATOR ───────────────────────────────
        print("\n[Pipeline] FASE 1: Parsing comando...")
        targets = await coordinator.parse_command(command)

        if not targets:
            await send_message(
                chat_id,
                "❌ Comando non riconosciuto.\n\n"
                "Usa il formato:\n"
                "`persona: Nome Cognome`\n"
                "`azienda: Nome Azienda`\n"
                "`dominio: example.com`"
            )
            return

        print(f"[Pipeline] {len(targets)} target identificati")

        # ── FASE 2: INVESTIGAZIONE per ogni target ────────────
        all_reports = []

        for i, target in enumerate(targets, 1):
            print(f"\n[Pipeline] FASE 2.{i}: Investigazione {target.type.value}: {target.value}")

            # Seleziona l'agente corretto per il tipo di target
            if target.type == TargetType.PERSON:
                agent_report = await person_agent.investigate(target)
            elif target.type == TargetType.COMPANY:
                agent_report = await company_agent.investigate(target)
            elif target.type == TargetType.DOMAIN:
                agent_report = await domain_agent.investigate(target)
            else:
                continue

            all_reports.append((target, [agent_report]))

            # Pausa tra target multipli
            if i < len(targets):
                await asyncio.sleep(3)

        # ── FASE 3: REPORT WRITING ────────────────────────────
        for target, agent_reports in all_reports:
            print(f"\n[Pipeline] FASE 3: Report per {target.value}")

            final_report = await report_writer.write(target, agent_reports)

            total_time = round(time.time() - start_time, 1)
            print(f"[Pipeline] Report completato in {total_time}s")

            # ── INVIO TELEGRAM (lista di messaggi) ────────────
            telegram_messages = final_report.to_telegram()
            for msg in telegram_messages:
                if msg.strip():
                    await send_message(chat_id, msg)
                    await asyncio.sleep(0.5)  # Piccola pausa tra messaggi

            # ── INVIO EMAIL via Make.com (se configurata) ─────
            if email and config.REPORT_EMAIL:
                # Inviamo l'HTML del report a un webhook Make.com
                # che girerà l'email tramite Gmail
                import httpx
                try:
                    async with httpx.AsyncClient() as client:
                        await client.post(
                            # Questo webhook Make.com gestisce l'invio email
                            # Lo configuriamo nella sezione Make.com
                            os.getenv("MAKE_EMAIL_WEBHOOK", ""),
                            json={
                                "to": email,
                                "subject": f"OSINT Report: {target.value}",
                                "html": final_report.to_email_html(),
                                "risk_score": final_report.risk_score,
                                "risk_level": final_report.risk_level
                            },
                            headers={
                                "X-Webhook-Secret": config.WEBHOOK_SECRET
                            },
                            timeout=10.0
                        )
                    print(f"[Pipeline] Email inviata a {email}")
                except Exception as e:
                    print(f"[Pipeline] Errore invio email: {e}")

        # Messaggio finale con statistiche
        await send_message(
            chat_id,
            f"✅ *Analisi completata*\n"
            f"_{len(all_reports)} target analizzati in {total_time}s_"
        )

    except Exception as e:
        print(f"[Pipeline] ✗ Errore: {e}")
        await send_message(
            chat_id,
            f"❌ Errore durante l'analisi: {str(e)[:200]}\nRiprova."
        )


def background_pipeline(command: str, chat_id: str, email: str = ""):
    """Esegue la pipeline in thread background."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            run_osint_pipeline(command, chat_id, email)
        )
    finally:
        loop.close()


# ── ENDPOINTS ──────────────────────────────────────────────

@app.route("/")
def root():
    return jsonify({
        "status": "online",
        "system": "OSINT Multi-Agent Intelligence System",
        "version": "1.0",
        "agents": ["Coordinator", "PersonAgent", "CompanyAgent",
                   "DomainAgent", "ReportWriter"]
    })


@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "model": config.GEMINI_MODEL,
        "sources": [
            "DuckDuckGo", "Wikipedia", "WHOIS",
            "DNS", "crt.sh", "Shodan InternetDB",
            "VirusTotal", "Wayback Machine", "IP Geo"
        ]
    })


@app.route("/webhook/make", methods=["POST"])
def make_webhook():
    """
    Endpoint principale per Make.com.
    Risposta immediata + elaborazione in background.
    """
    if not check_auth():
        return jsonify({"error": "Non autorizzato"}), 403

    body = request.get_json() or {}
    command = body.get("message", "").strip()
    chat_id = str(body.get("chat_id", "")).strip()
    email = body.get("email", config.REPORT_EMAIL)

    if not command:
        return jsonify({"error": "Campo 'message' mancante"}), 400
    if not chat_id:
        return jsonify({"error": "Campo 'chat_id' mancante"}), 400

    print(f"[Webhook] Ricevuto: '{command}' da chat {chat_id}")

    # Avvia pipeline in background
    thread = threading.Thread(
        target=background_pipeline,
        args=(command, chat_id, email),
        daemon=True
    )
    thread.start()

    return jsonify({
        "success": True,
        "status": "processing",
        "message": "OSINT avviato"
    })


@app.route("/test", methods=["POST"])
def test():
    """Endpoint sincrono per test da VSCode (può andare in timeout)."""
    if not check_auth():
        return jsonify({"error": "Non autorizzato"}), 403

    body = request.get_json() or {}
    command = body.get("message", "").strip()

    if not command:
        return jsonify({"error": "Campo 'message' mancante"}), 400

    start = time.time()
    result = run_async(coordinator.parse_command(command))
    elapsed = round(time.time() - start, 2)

    return jsonify({
        "command": command,
        "targets_parsed": [
            {"type": t.type.value, "value": t.value}
            for t in result
        ],
        "parse_time_seconds": elapsed
    })


if __name__ == "__main__":
    config.validate()
    app.run(debug=True, port=8000, use_reloader=False)
