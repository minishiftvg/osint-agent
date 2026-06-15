# app/config.py
# Configurazione centralizzata.
# Tutte le chiavi API e i parametri vengono letti dal file .env

import os
from pathlib import Path
from dotenv import load_dotenv

# Carica il file .env dalla root del progetto
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class Config:
    """
    Configurazione dell'applicazione OSINT.

    Separiamo la configurazione dal codice per:
    1. Sicurezza: le chiavi non vanno su GitHub
    2. Flessibilità: cambi un valore senza toccare il codice
    3. Portabilità: stesso codice funziona in dev e in produzione
    """

    # ── LLM ──────────────────────────────────────────────────
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    # gemini-2.0-flash: veloce, gratuito, ottimo per analisi strutturata
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    # ── API OSINT (opzionali ma consigliate) ─────────────────
    # WhoisJSON: 1.000 req/mese gratis, nessuna carta
    WHOISJSON_API_KEY: str = os.getenv("WHOISJSON_API_KEY", "")
    # VirusTotal: 500 req/giorno gratis
    VIRUSTOTAL_API_KEY: str = os.getenv("VIRUSTOTAL_API_KEY", "")

    # ── Telegram ─────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

    # ── Sicurezza ─────────────────────────────────────────────
    # Password per autenticare le richieste di Make.com
    WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "changeme")

    # ── Email (opzionale) ────────────────────────────────────
    # Email destinatario per i report (inviati via Make.com)
    REPORT_EMAIL: str = os.getenv("REPORT_EMAIL", "")

    # ── Parametri sistema ────────────────────────────────────
    # Timeout HTTP per le chiamate alle API esterne
    HTTP_TIMEOUT: int = int(os.getenv("HTTP_TIMEOUT", "12"))

    def validate(self) -> None:
        """Verifica le variabili obbligatorie all'avvio."""
        errors = []
        if not self.GEMINI_API_KEY:
            errors.append("GEMINI_API_KEY mancante (https://aistudio.google.com)")
        if not self.TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN mancante (@BotFather su Telegram)")
        if errors:
            raise ValueError(
                "Configurazione incompleta nel .env:\n" +
                "\n".join(f"  • {e}" for e in errors)
            )


config = Config()
