@echo off
SETLOCAL EnableDelayedExpansion
echo [*] Creazione della struttura del progetto OSINT-Agent in corso...

:: 1. Creazione della cartella principale e delle sottocartelle
mkdir osint-agent
cd osint-agent
mkdir app
mkdir app\sources
mkdir app\agents

:: 2. Creazione dei file nella root del progetto
type nul > .env
type nul > .gitignore
type nul > requirements.txt
type nul > test_local.http

:: 3. Creazione dei file nella cartella app/
type nul > app\__init__.py
type nul > app\config.py
type nul > app\models.py
type nul > app\llm_client.py
type nul > app\telegram_sender.py
type nul > app\main.py

:: 4. Creazione dei file nella cartella app/sources/
type nul > app\sources\__init__.py
type nul > app\sources\duckduckgo.py
type nul > app\sources\wikipedia.py
type nul > app\sources\whois_lookup.py
type nul > app\sources\dns_lookup.py
type nul > app\sources\crtsh.py
type nul > app\sources\shodan_free.py
type nul > app\sources\virustotal.py
type nul > app\sources\wayback.py
type nul > app\sources\ip_geo.py

:: 5. Creazione dei file nella cartella app/agents/
type nul > app\agents\__init__.py
type nul > app\agents\coordinator.py
type nul > app\agents\person_agent.py
type nul > app\agents\company_agent.py
type nul > app\agents\domain_agent.py
type nul > app\agents\report_writer.py

echo [^+] Struttura creata con successo in root: %CD%
pause