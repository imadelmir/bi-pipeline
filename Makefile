# Comandi del progetto (M1-T9).
#
# Chi clona il repository legge il README e digita `make up`. Se per lavorare
# serve ricordare altro, il README è scritto male.
#
# Su Windows senza GNU Make c'è `.\make.ps1 <comando>`, che espone gli stessi
# nomi con le stesse azioni. Se cambi un comando qui, cambialo anche là.

COMPOSE := docker compose
UV      := uv run --frozen

.DEFAULT_GOAL := help
.PHONY: help up down psql ingest build test docs flow check format

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
	@echo "Non ancora implementato: arriva con M2-T1 (scaricamento) e M2-T5 (COPY)." && exit 1

build: ## dbt build: modelli e test insieme
	@echo "Non ancora implementato: arriva con M3-T1 (dbt init)." && exit 1

test: ## Solo i test dbt, senza ricostruire i modelli
	@echo "Non ancora implementato: arriva con M5-T1." && exit 1

docs: ## Genera e apre la documentazione dbt con il lineage
	@echo "Non ancora implementato: arriva con M5-T9." && exit 1

flow: ## Il flusso Prefect completo, dall'inizio alla fine
	@echo "Non ancora implementato: arriva con M6-T1." && exit 1
