# app/sources/virustotal.py
# Controlla la reputazione di domini e IP su VirusTotal.
#
# COS'È VIRUSTOTAL:
# VirusTotal è un servizio di Google che aggrega i risultati
# di oltre 70 antivirus e scanner di sicurezza.
# Per i domini: dice se sono stati flaggati come malware,
# phishing, spam, ecc. da qualche vendor di sicurezza.
#
# PIANO GRATUITO: 500 richieste/giorno, nessuna carta.

import httpx
from app.config import config
from app.models import SourceResult


async def check_domain(domain: str) -> SourceResult:
    """
    Controlla la reputazione di un dominio su VirusTotal.

    Args:
        domain: Il dominio da controllare

    Returns:
        SourceResult con il report di reputazione
    """
    if not config.VIRUSTOTAL_API_KEY:
        return SourceResult(
            source_name="VirusTotal",
            data="VirusTotal non configurato (aggiungi VIRUSTOTAL_API_KEY nel .env)",
            success=False,
            error="API key mancante"
        )

    try:
        async with httpx.AsyncClient() as client:
            # VirusTotal API v3: richiede header x-apikey
            response = await client.get(
                f"https://www.virustotal.com/api/v3/domains/{domain}",
                headers={"x-apikey": config.VIRUSTOTAL_API_KEY},
                timeout=12.0
            )

            if response.status_code == 200:
                data = response.json()
                attrs = data.get("data", {}).get("attributes", {})

                result_parts = [f"Dominio analizzato: {domain}"]

                # Statistiche analisi: quanti antivirus lo flaggano
                stats = attrs.get("last_analysis_stats", {})
                if stats:
                    malicious = stats.get("malicious", 0)
                    suspicious = stats.get("suspicious", 0)
                    harmless = stats.get("harmless", 0)
                    undetected = stats.get("undetected", 0)
                    total = malicious + suspicious + harmless + undetected

                    result_parts.append(
                        f"Analisi sicurezza ({total} engine):"
                    )
                    result_parts.append(
                        f"  ✓ Pulito: {harmless} engine"
                    )
                    if malicious > 0:
                        result_parts.append(
                            f"  ⚠️ MALEVOLO: {malicious} engine"
                        )
                    if suspicious > 0:
                        result_parts.append(
                            f"  ⚠️ Sospetto: {suspicious} engine"
                        )

                # Categorie del dominio secondo i vendor
                categories = attrs.get("categories", {})
                if categories:
                    unique_cats = list(set(categories.values()))[:5]
                    result_parts.append(
                        f"Categorie: {', '.join(unique_cats)}"
                    )

                # Reputation score (-100 = molto pericoloso, 0 = neutro)
                reputation = attrs.get("reputation", None)
                if reputation is not None:
                    rep_label = (
                        "Ottima" if reputation > 50 else
                        "Buona" if reputation > 0 else
                        "Neutra" if reputation == 0 else
                        "Scarsa" if reputation > -50 else
                        "Pessima"
                    )
                    result_parts.append(
                        f"Reputation score: {reputation} ({rep_label})"
                    )

                # Data ultima analisi
                last_analysis = attrs.get("last_analysis_date")
                if last_analysis:
                    from datetime import datetime
                    date_str = datetime.fromtimestamp(last_analysis).strftime(
                        "%d/%m/%Y"
                    )
                    result_parts.append(f"Ultima analisi: {date_str}")

                return SourceResult(
                    source_name="VirusTotal",
                    data="\n".join(result_parts)
                )

            elif response.status_code == 404:
                return SourceResult(
                    source_name="VirusTotal",
                    data=f"Dominio {domain} non nel database VirusTotal"
                )
            elif response.status_code == 401:
                return SourceResult(
                    source_name="VirusTotal",
                    data="",
                    success=False,
                    error="API key VirusTotal non valida"
                )

    except Exception as e:
        return SourceResult(
            source_name="VirusTotal",
            data="",
            success=False,
            error=str(e)
        )
