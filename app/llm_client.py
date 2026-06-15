# app/llm_client.py
# Client Google Gemini per tutte le chiamate LLM del sistema.

import google.generativeai as genai
from app.config import config

# Configura Gemini con la chiave API
genai.configure(api_key=config.GEMINI_API_KEY)


def call_gemini(
    system_prompt: str,
    user_message: str,
    max_tokens: int = 1500,
    temperature: float = 0.3
) -> str:
    """
    Chiama Google Gemini con system prompt e messaggio utente.

    Args:
        system_prompt: Istruzioni permanenti (ruolo dell'agente)
        user_message:  Richiesta specifica
        max_tokens:    Lunghezza massima risposta
        temperature:   0=deterministico, 1=creativo

    Returns:
        Testo della risposta
    """
    model = genai.GenerativeModel(
        model_name=config.GEMINI_MODEL,
        system_instruction=system_prompt,
        generation_config=genai.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature
        )
    )
    response = model.generate_content(user_message)
    return response.text
