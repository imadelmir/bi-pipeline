# BI Pipeline

Un milione di righe di vendite grezze entrano da un file, escono da un cruscotto
con cinque indicatori, e in mezzo attraversano quattro strati che si possono
rilanciare uno per uno senza sporcare niente.

<!-- Badge della CI: da aggiungere in M1-T10, quando il repository remoto esiste
     e il primo workflow è passato. -->

> **Stato:** in costruzione — milestone M1 (Fondamenta).
> Il case study completo arriva a M8.

---

## Cosa fa

Una pipeline **ELT** su dati di vendita reali:

```
online_retail_II.xlsx ──► raw ──► staging ──► marts ──► cruscotti
       Python           Postgres    dbt        dbt       Metabase
```

| Strato | Strumento | Regola invariabile |
| --- | --- | --- |
| `raw` | Python + `COPY` | Nessuna trasformazione: se il dato è sporco, entra sporco |
| `staging` | dbt, viste | Tipi, nomi, pulizia, deduplica. Un modello per sorgente, nessun join |
| `marts` | dbt, tabelle | Schema a stella: un fatto e quattro dimensioni. Solo qui nascono le chiavi |
| presentazione | Metabase | Nessuna logica di business nei grafici: se serve un calcolo, si fa in dbt |

Ogni strato è **idempotente**: rilanciarlo non duplica niente.

## La sorgente

**Online Retail II** — tutte le transazioni di un grossista inglese di articoli
da regalo, dal 01/12/2009 al 09/12/2011, 1.067.371 righe.

Licenza **CC BY 4.0**: il riuso è libero a condizione di citare la fonte.

> Chen, D. (2012). *Online Retail II* [Dataset]. UCI Machine Learning
> Repository. <https://doi.org/10.24432/C5CG6D>

Il file sorgente **non è nel repository**: pesa 43,5 MB e in git resterebbe per
sempre. Si scarica con `make ingest`, che ne verifica lo SHA-256 prima di
caricarlo.

## Prerequisiti

| Strumento | Versione | Nota |
| --- | --- | --- |
| [Docker](https://docs.docker.com/get-docker/) | con Compose v2 | Alza PostgreSQL |
| [uv](https://docs.astral.sh/uv/) | ≥ 0.12 | Gestisce Python e le dipendenze |
| Python | 3.12 | Lo installa `uv` da solo: non serve averlo già |
| `make` | GNU Make | Su Windows si può usare `.\make.ps1 <comando>` senza installarlo |

## Avvio in locale

```bash
git clone <url-del-repository>
cd bi-pipeline

cp .env.example .env          # poi si riempiono i valori
git config core.hooksPath .githooks   # attiva i controlli prima del commit
uv sync                       # crea .venv con Python 3.12 e le versioni bloccate

make up                       # PostgreSQL su Docker
```

Su Windows, se `make` non è installato, ogni comando ha la sua forma
PowerShell equivalente: `.\make.ps1 up`, `.\make.ps1 ingest`, e così via.

## I comandi

| Comando | Cosa fa |
| --- | --- |
| `make up` | Alza i servizi Docker (PostgreSQL) |
| `make down` | Li ferma |
| `make ingest` | Scarica, verifica il checksum e carica in `raw` con `COPY` |
| `make build` | `dbt build`: modelli e test insieme |
| `make test` | Solo i test, senza ricostruire i modelli |
| `make docs` | Genera e apre la documentazione dbt con il lineage |
| `make flow` | Il flusso Prefect completo |
| `make check` | Formattazione, lint e type check — gli stessi controlli della CI |

I comandi delle milestone non ancora raggiunte esistono già e lo dicono:
stampano quale task li riempirà, invece di fallire con un errore oscuro.

## Struttura

```
ingestion/      Python: scaricamento, checksum, COPY verso raw
dbt/            Modelli, test, seed e macro delle trasformazioni
orchestration/  Il flusso Prefect che mette in fila tutto
metabase/       Cosa contiene ogni cruscotto e perché
docs/
├── milestones/ Una relazione per milestone, con i numeri misurati
├── decisioni.md   Le decisioni tecniche e le alternative scartate
├── piano.md       Il piano di progetto
└── backlog.md     Le 8 milestone e i 53 task
```

## Le milestone

| | Milestone | Chiude quando |
| --- | --- | --- |
| M1 | Fondamenta | `docker compose up` alza PostgreSQL, la CI è verde |
| M2 | Ingestione | Un milione di righe in `raw`, ricaricabili senza duplicare |
| M3 | Staging | `stg_vendite` pulito, con i conteggi delle esclusioni |
| M4 | Schema a stella | Un fatto e quattro dimensioni, chiavi surrogate, fatto incrementale |
| M5 | Qualità | Tutti i test passano, la quadratura torna |
| M6 | Orchestrazione | Prefect esegue tutto con un comando, con ritentativi |
| M7 | Cruscotti | Metabase mostra i cinque indicatori su tre pagine |
| M8 | Pubblicazione | README con diagramma, case study nel portfolio |

Ogni milestone chiude con una relazione in [`docs/milestones/`](docs/milestones/):
cosa è stato costruito, quali decisioni, con quali numeri misurati.

## Limiti dichiarati

- **Il margine non è calcolabile.** Serve il costo d'acquisto e nessun dataset
  pubblico lo contiene. Inventarlo renderebbe finto tutto il resto.
- **Niente dimensioni a evoluzione lenta.** Esiste una sola fotografia dei
  prodotti: storicizzarla vorrebbe dire inventare cambiamenti mai avvenuti.
- **Non ci sono negozi.** È un rivenditore che vende solo online: la geografia
  è per paese, e i paesi si chiamano paesi.

## Licenza

Codice: [MIT](LICENSE). Dati: CC BY 4.0, con l'attribuzione riportata sopra.
