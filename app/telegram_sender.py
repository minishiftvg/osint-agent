# app/telegram_sender.py
# Invia messaggi Telegram direttamente tramite Bot API.

import httpx
import os


async def send_message(chat_id: str, text: str) -> bool:
    """Invia un messaggio su Telegram."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        return False

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "Markdown"
                },
                timeout=15.0
            )
            success = response.status_code == 200
            if success:
                print(f"[Telegram] ✓ Messaggio inviato")
            else:
                print(f"[Telegram] ✗ Errore: {response.status_code}")
            return success
    except Exception as e:
        print(f"[Telegram] Eccezione: {e}")
        return False


async def send_typing(chat_id: str) -> None:
    """Mostra 'sta scrivendo...' su Telegram."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        return
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{token}/sendChatAction",
                json={"chat_id": chat_id, "action": "typing"},
                timeout=5.0
            )
    except Exception:
        pass
