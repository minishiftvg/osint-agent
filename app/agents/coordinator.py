# app/agents/coordinator.py
# Il Coordinator analizza il comando dell'utente e decide
# quali agenti attivare e con quali parametri.
#
# PATTERN COORDINATOR:
# In un sistema multi-agent, il Coordinator (o Dispatcher) è
# il punto di ingresso che:
# 1. Interpreta la richiesta in linguaggio naturale
# 2. La traduce in task strutturati
# 3. Assegna ogni task all'agente specializzato corretto
# Questo separa la logica di routing dalla logica di esecuzione.

import json
from app.models import OsintTarget, TargetType
from app.llm_client import call_gemini

COORDINATOR_PROMPT = """Sei il coordinatore di un sistema OSINT professionale.
Ricevi un comando da un utente e devi estrarre i target da investigare.

FORMATI RICONOSCIUTI:
- "persona: Nome Cognome" → target tipo PERSON
- "azienda: Nome Azienda" → target tipo COMPANY
- "dominio: example.com" → target tipo DOMAIN
- Combinazioni multiple: tutti e tre insieme

REGOLE:
1. Estrai TUTTI i target presenti nel comando
2. Per ogni target identifica tipo e valore
3. Rispondi SOLO con JSON valido, nessun testo aggiuntivo

FORMATO JSON:
{
  "targets": [
    {"type": "person", "value": "Mario Rossi", "context": ""},
    {"type": "company", "value": "Acme Corp", "context": ""},
    {"type": "domain", "value": "acmecorp.com", "context": ""}
  ],
  "intent": "descrizione breve dell'obiettivo dell'investigazione"
}

Se il comando non è chiaro o non contiene target validi:
{"targets": [], "intent": "comando non riconosciuto"}"""


class Coordinator:
    """
    Agente coordinatore: interpreta il comando e crea i target.
    """

    async def parse_command(self, user_command: str) -> list:
        """
        Analizza il comando e restituisce lista di OsintTarget.

        Args:
            user_command: Comando grezzo dell'utente

        Returns:
            Lista di OsintTarget da investigare
        """
        print(f"[Coordinator] Analisi comando: '{user_command}'")

        # Prima proviamo il parsing diretto (più veloce, senza LLM)
        targets = self._try_direct_parse(user_command)

        if targets:
            print(f"[Coordinator] Parsing diretto: {len(targets)} target")
            return targets

        # Se il parsing diretto fallisce, usa Gemini
        print("[Coordinator] Uso Gemini per interpretare il comando")
        raw = call_gemini(
            system_prompt=COORDINATOR_PROMPT,
            user_message=f"Comando: {user_command}",
            max_tokens=400,
            temperature=0
        )

        targets = self._parse_json(raw)
        print(f"[Coordinator] Gemini: {len(targets)} target trovati")

        return targets

    def _try_direct_parse(self, command: str) -> list:
        """
        Parsing diretto senza LLM per comandi nel formato standard.

        Gestisce comandi come:
          "persona: Mario Rossi"
          "dominio: google.com"
          "azienda: Acme\ndominio: acme.com"

        Returns:
            Lista di OsintTarget o lista vuota se parsing fallisce
        """
        targets = []
        lines = command.strip().lower().split("\n")

        keyword_map = {
            # Keywords italiane e inglesi per ogni tipo
            ("persona:", "person:", "persone:", "nome:"): TargetType.PERSON,
            ("azienda:", "company:", "aziende:", "società:"): TargetType.COMPANY,
            ("dominio:", "domain:", "domini:", "sito:", "website:"): TargetType.DOMAIN
        }

        for line in lines:
            line = line.strip()
            for keywords, target_type in keyword_map.items():
                for keyword in keywords:
                    if line.startswith(keyword):
                        value = line[len(keyword):].strip()
                        if value:
                            # Rimuovi virgolette se presenti
                            value = value.strip('"\'')
                            targets.append(
                                OsintTarget(type=target_type, value=value)
                            )
                        break

        return targets

    def _parse_json(self, raw_output: str) -> list:
        """Parsa il JSON di Gemini in lista di OsintTarget."""
        cleaned = raw_output.strip()

        # Rimuovi markdown
        if "```" in cleaned:
            start = cleaned.find("```")
            end = cleaned.rfind("```")
            if start != end:
                cleaned = "\n".join(cleaned[start:end].split("\n")[1:])

        # Estrai JSON
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start >= 0 and end > start:
            cleaned = cleaned[start:end]

        try:
            data = json.loads(cleaned)
            targets = []

            type_map = {
                "person": TargetType.PERSON,
                "company": TargetType.COMPANY,
                "domain": TargetType.DOMAIN
            }

            for t in data.get("targets", []):
                target_type = type_map.get(t.get("type", "").lower())
                value = t.get("value", "").strip()

                if target_type and value:
                    targets.append(OsintTarget(
                        type=target_type,
                        value=value,
                        context=t.get("context", "")
                    ))

            return targets

        except json.JSONDecodeError:
            print("[Coordinator] Errore parsing JSON")
            return []
