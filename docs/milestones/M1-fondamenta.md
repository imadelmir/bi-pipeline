# M1 — Fondamenta

Lavoro locale svolto il 19/08/2026 · commit iniziale `d949622` · commit finale
`46c0866`

> **Non ancora chiusa.** Nove task su undici sono fatti e verificati. Restano la
> parte remota di M1-T2 (repository pubblico su GitHub) e M1-T10 (badge verde),
> che dipendono da una decisione dell'autore: vedi la sezione 6.

## 1. Cosa è stato costruito

Prima non c'era niente: una cartella vuota. Adesso c'è un repository con la
licenza della sorgente verificata e citata, un ambiente Python 3.12 con le
versioni bloccate al valore esatto, un PostgreSQL 16.14 che si alza con un
comando e risponde, tre controlli di qualità che rifiutano un commit mal
formattato, e un elenco di comandi che funziona sia con GNU Make sia senza.

La pipeline non esiste ancora — nessun dato è stato caricato. Quello che esiste
è il terreno su cui costruirla: chi clona il repository e segue il README arriva
a un database funzionante senza dover indovinare niente.

## 2. File creati e modificati

| Percorso | Scopo |
| --- | --- |
| `README.md` | Cosa fa il progetto, la sorgente con l'attribuzione, i prerequisiti, i comandi |
| `LICENSE` | MIT sul codice, con l'attribuzione CC BY dei dati |
| `CLAUDE.md` | Requisiti, architettura, convenzioni e vincoli in un file solo |
| `.gitignore` | Fuori `.env`, `profiles.yml` e il file sorgente da 43,5 MB |
| `.gitattributes` | Fine riga LF nel repository, CRLF nella copia di lavoro |
| `pyproject.toml` | Dipendenze con versioni fissate, configurazione di ruff e mypy |
| `uv.lock` | Le 150 versioni risolte, committate |
| `.githooks/pre-commit` | ruff format, ruff check e mypy prima di ogni commit |
| `docker-compose.yml` | PostgreSQL 16.14 con volume persistente e healthcheck |
| `.env.example` | Ogni variabile documentata con un valore di esempio |
| `Makefile` | I comandi del progetto |
| `make.ps1` | Gli stessi comandi su Windows senza GNU Make |
| `.github/workflows/ci.yml` | Formato, lint e tipi su ogni push e pull request |
| `docs/decisioni.md` | Le cinque decisioni prese finora, con le alternative scartate |
| `docs/piano.md`, `docs/backlog.md`, `docs/mockup.pdf` | Le fonti del progetto, dentro il repository |
| `ingestion/`, `orchestration/` | Pacchetti Python veri, con `__init__.py` |
| `dbt/`, `metabase/`, `docs/milestones/` | Cartelle del piano, con `.gitkeep` |

## 3. Decisioni tecniche

Le decisioni sono scritte per esteso in [`docs/decisioni.md`](../decisioni.md).
In sintesi:

### Scelta: l'hook pre-commit è uno script versionato, non il framework `pre-commit` (D2)
**Alternativa scartata:** `.pre-commit-config.yaml`.
**Perché:** il framework vuole le versioni degli strumenti dichiarate una
seconda volta dentro il suo YAML. Un giorno divergerebbero da `pyproject.toml`,
e il commit locale passerebbe mentre la CI fallisce. Con `uv run`, lo strumento
che gira in locale è lo stesso identico che gira in CI.

### Scelta: Metabase non entra in `docker-compose.yml` fino a M7 (D3)
**Alternativa scartata:** alzare tutto subito.
**Perché:** un servizio inutile per sei milestone allunga l'avvio e confonde la
diagnosi quando qualcosa non parte.

### Scelta: versioni fissate ovunque, non solo in `pyproject.toml` (D4)
**Alternativa scartata:** intervalli `>=` e tag mobili come `postgres:16`.
**Perché:** con un intervallo, due macchine installano cose diverse e il giorno
che qualcosa si rompe non si sa se è colpa del codice o di un aggiornamento
arrivato di nascosto.

### Scelta: `make.ps1` accanto al `Makefile` (D5)
**Alternativa scartata:** installare GNU Make e tenere un file solo.
**Perché:** su Windows `make` non c'è, e chiedere di installarlo prima ancora di
poter alzare un database è attrito inutile. Il `Makefile` resta il contratto.

### Scelta: i comandi non ancora implementati escono con errore
**Alternativa scartata:** farli uscire con successo senza fare niente.
**Perché:** un comando che risponde «tutto bene» senza aver fatto nulla è il modo
più rapido per costruirsi una CI verde che non prova niente. Stampano quale task
li riempirà, poi escono con 1.

## 4. Numeri misurati

| Cosa | Valore | Come |
| --- | --- | --- |
| Licenza della sorgente | CC BY 4.0, DOI `10.24432/C5CG6D` | Letta sulla scheda UCI il 19/08/2026 |
| Righe dichiarate dalla sorgente | 1.067.371 | Scheda UCI (da verificare al caricamento, M2) |
| Python | 3.12.13 | `uv python install 3.12` — 1 min 17 s, 20,9 MiB scaricati |
| Pacchetti risolti | 150 | `uv lock` |
| `uv sync` con `.venv` assente e cache uv calda | 2 s | `rm -rf .venv && uv sync --frozen` |
| Peso di `.venv` | 608 MB | `du -sh .venv` |
| `make up` a freddo, con pull dell'immagine | 318 s | `docker compose up -d --wait` |
| `make up` a caldo | 7 s | Stesso comando, immagine già presente |
| Versione del database | PostgreSQL 16.14 (Debian), UTF8, collazione C | `select version()` dentro il contenitore |
| `make check` (ruff format + ruff check + mypy) | 2 s | Sull'albero attuale |
| Commit con codice mal formattato | rifiutato, uscita `1` | Prova descritta sotto |

## 5. Problemi incontrati

**`mypy` non parte su cartelle senza file Python.** Con `files = ["ingestion",
"orchestration"]` in `pyproject.toml` e le cartelle ancora vuote, mypy esce con
`There are no .py[i] files in directory 'ingestion'` e codice 2 — cioè l'hook
avrebbe rifiutato ogni commit. Risolto trasformando le due cartelle in pacchetti
veri con `__init__.py`, che servivano comunque: `ingestion/sources/online_retail.py`
va importato come modulo in M2.

**`ruff` formatta anche il Markdown.** La versione 0.16.3 tratta i file `.md`:
`docs/piano.md` e `docs/backlog.md` sono copie dei documenti sorgente e devono
restare identiche all'originale, altrimenti confrontarle diventa impossibile.
Escluse con `extend-exclude` in `pyproject.toml`.

**`docker compose exec db psql -U $POSTGRES_USER` non funziona dall'host.** Le
variabili stanno in `.env`, che Docker Compose legge per sé ma che la shell non
ha. La prima versione del comando `make psql` sarebbe fallita sulla macchina di
chiunque. Corretto facendo espandere le variabili **dentro** il contenitore, dove
esistono già: `exec db sh -c 'psql -U "$POSTGRES_USER" …'`.

**Il primo commit ha raggruppato cinque task in un messaggio che ne citava tre.**
Rifatto con `git reset --soft` e tre commit separati, uno per gruppo di task: la
relazione di milestone si scrive leggendo `git log`, e un log impreciso costa più
tempo di quanto ne faccia risparmiare.

**Docker Desktop non era in esecuzione**, e `docker info` falliva con un errore
sulla named pipe che non dice niente a chi non lo ha già visto. Vale la pena
saperlo prima di M2: se `make up` si lamenta del daemon, il problema è
l'applicazione spenta, non il file compose.

## 6. Cosa resta aperto

- **M1-T2, parte remota — il repository pubblico su GitHub non esiste ancora.**
  L'account autenticato su questa macchina è `AVENA50`, ma i link del case study
  di Football Analytics nel portfolio puntano a `imadelmir`. Serve la decisione
  dell'autore su quale usare, e se il repository debba nascere pubblico subito o
  privato fino a M8.
- **M1-T10 — il badge della CI.** Il workflow è scritto ma non è mai girato:
  senza remoto non può. Il badge va aggiunto al README dopo la prima esecuzione
  verde, non prima.
- **Le versioni delle action di GitHub** (`actions/checkout@v7`,
  `astral-sh/setup-uv@v10`) sono fissate al maggiore, non all'esatto: è la
  convenzione già usata nel repository del portfolio.
- **`make ingest`, `build`, `test`, `docs`, `flow` sono segnaposto** che escono
  con errore. È voluto, e ognuno dichiara il task che lo riempirà.
- **Nessun dato è ancora stato scaricato.** Le 1.067.371 righe sono un numero
  dichiarato dalla scheda UCI: diventa un numero misurato in M2.

## 7. Come verificarlo

Su una macchina pulita, con Docker e `uv` installati:

```bash
git clone <url-del-repository>
cd bi-pipeline

cp .env.example .env                    # poi si riempiono i valori
git config core.hooksPath .githooks

uv sync --frozen                        # Python 3.12 e le 150 versioni bloccate
uv run --frozen ruff format --check .   # oppure: make check
uv run --frozen ruff check .
uv run --frozen mypy

make up                                 # oppure: .\make.ps1 up
docker compose ps                       # bi-pipeline-db  Up (healthy)
make psql                               # \l elenca il database bi_pipeline
make down
```

Per verificare che l'hook rifiuti davvero un commit sporco:

```bash
printf 'def brutto( x ):\n    y   =  x+1\n    return y\n' > ingestion/prova.py
git add ingestion/prova.py
git commit -m "prova"                   # esce con 1, il commit non viene creato
git restore --staged ingestion/prova.py && rm ingestion/prova.py
```
