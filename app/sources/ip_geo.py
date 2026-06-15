# app/sources/ip_geo.py
# Geolocalizzazione IP tramite ip-api.com.
# Gratuito, 45 req/minuto, senza chiave API.

import httpx
import socket
from app.models import SourceResult


async def geolocate_domain(domain: str) -> SourceResult:
    """
    Trova la posizione geografica del server di un dominio.

    Flusso:
    1. Risolve il dominio in IP
    2. Geolocalizza l'IP con ip-api.com

    Args:
        domain: Il dominio da geolocalizzare

    Returns:
        SourceResult con info geografiche del server
    """
    try:
        # Risolvi il dominio in IP
        try:
            ip = socket.gethostbyname(domain)
        except socket.gaierror:
            return SourceResult(
                source_name="IP Geolocalizzazione",
                data=f"Impossibile risolvere {domain} in IP",
                success=False,
                error="DNS failed"
            )

        # Geolocalizza l'IP
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://ip-api.com/json/{ip}",
                params={
                    # Campi desiderati dalla risposta
                    "fields": (
                        "status,country,regionName,city,"
                        "isp,org,as,hosting,proxy,mobile"
                    )
                },
                timeout=8.0
            )

            if response.status_code == 200:
                data = response.json()

                if data.get("status") == "success":
                    result_parts = [f"IP: {ip} (per {domain})"]

                    if data.get("country"):
                        location = data.get("country", "")
                        if data.get("city"):
                            location = f"{data['city']}, {location}"
                        result_parts.append(f"Posizione server: {location}")

                    if data.get("isp"):
                        result_parts.append(f"ISP: {data['isp']}")

                    if data.get("org"):
                        result_parts.append(f"Organizzazione: {data['org']}")

                    if data.get("as"):
                        result_parts.append(f"AS (Autonomous System): {data['as']}")

                    # Flag speciali
                    flags = []
                    if data.get("hosting"):
                        flags.append("Hosting/Datacenter")
                    if data.get("proxy"):
                        flags.append("Proxy/VPN")
                    if data.get("mobile"):
                        flags.append("Mobile network")
                    if flags:
                        result_parts.append(f"Flag: {', '.join(flags)}")

                    return SourceResult(
                        source_name="IP Geolocalizzazione",
                        data="\n".join(result_parts)
                    )

    except Exception as e:
        return SourceResult(
            source_name="IP Geolocalizzazione",
            data="",
            success=False,
            error=str(e)
        )
