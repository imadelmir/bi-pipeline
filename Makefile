# Comandi del progetto (M1-T9).
#
# Chi clona il repository legge il README e digita `make up`. Se per lavorare
# serve ricordare altro, il README è scritto male.
#
# Su Windows senza GNU Make c'è `.\make.ps1 <comando>`, che espone gli stessi
# nomi con le stesse azioni. Se cambi un comando qui, cambialo anche là.

COMPOSE := docker compose
UV      := uv run --frozen

# dbt non legge .env da solo: le variabili gli arrivano dall'ambiente, e qui
# vengono caricate una volta per tutti i comandi. Il file resta l'unico posto
# dove stanno le credenziali.
ifneq (,$(wildcard .env))
include .env
export
endif

# --project-dir e --profiles-dir: il progetto dbt sta in dbt/, e il profilo
# accanto ai modelli invece che in ~/.dbt. Chi clona il repository non deve
# scrivere niente nella propria cartella utente.
# dbt si avvia come modulo Python e non con il suo eseguibile: su Windows il
# criterio di controllo delle applicazioni blocca gli .exe generati dentro
# .venv (vedi scripts/esegui_dbt.py).
DBT := $(UV) python scripts/esegui_dbt.py

# Il progetto dbt sta in dbt/, e il profilo accanto ai modelli invece che in
# ~/.dbt: chi clona il repository non deve scrivere nella propria cartella
# utente.
export DBT_PROJECT_DIR  := dbt
export DBT_PROFILES_DIR := dbt

# Il target predefinito e' dev: un trimestre di dati, ciclo di prova rapido.
# Per la produzione: make build TARGET=prod
TARGET ?= dev

.DEFAULT_GOAL := help
.PHONY: help up down psql ingest profila confronto build test docs flow check format

help: ## Elenca i comandi disponibili
	@echo "Comandi disponibili:"
	@grep -E '^[a-z-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  %-10s %s\n", $$1, $$2}'

# --- Ambiente -----------------------------------------------------------------

up: ## Alza i servizi Docker e aspetta che il database risponda
	$(COMPOSE) up -d --wait

down: ## Ferma i servizi (il volume dei dati resta)
	$(COMPOSE) down

psql: ## Apre psql dentro il contenitore del database
	$(COMPOSE) exec db sh -c 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

# --- Qualità del codice -------------------------------------------------------

check: ## Formattazione, lint e tipi — gli stessi controlli della CI
	$(UV) ruff format --check .
	$(UV) ruff check .
	$(UV) mypy

format: ## Formatta e corregge quello che si può correggere da solo
	$(UV) ruff format .
	$(UV) ruff check --fix .

# --- Pipeline -----------------------------------------------------------------
#
# I comandi delle milestone non ancora raggiunte esistono e dichiarano chi li
# riempirà. Escono con errore di proposito: un comando che non fa niente e
# risponde "tutto bene" è il modo più rapido per costruirsi una CI verde che
# non prova nulla.

ingest: ## Scarica, verifica il checksum e carica in raw con COPY
	$(UV) python -m ingestion.sources.online_retail
	$(UV) python -m ingestion.load

profila: ## Riconta lo sporco della sorgente e riscrive docs/profilazione.md
	$(UV) python -m ingestion.profilazione

confronto: ## Cronometra COPY contro pandas.to_sql su centomila righe
	$(UV) python -m ingestion.confronto_copy

build: ## dbt build: modelli e test insieme (TARGET=dev di default)
	$(DBT) seed --target $(TARGET)
	$(DBT) build --target $(TARGET)

test: ## Solo i test, senza ricostruire i modelli
	$(DBT) test --target $(TARGET)

docs: ## Genera e apre la documentazione dbt con il lineage
	$(DBT) docs generate --target $(TARGET)
	$(DBT) docs serve --target $(TARGET)

flow: ## Il flusso Prefect completo, dall'inizio alla fine
	@echo "Non ancora implementato: arriva con M6-T1." && exit 1
