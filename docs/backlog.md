# BI Pipeline — backlog per GitHub

Otto milestone, cinquantatré task. Ogni task è pensato per diventare una issue:
titolo, contesto, criteri di completamento.

**Regola d'ordine:** le milestone si chiudono in sequenza. Dentro una
milestone, i task senza dipendenze dichiarate possono procedere in parallelo.

---

## Perché una documentazione a ogni milestone

L'ultimo task di ogni milestone è sempre lo stesso: scrivere
`docs/milestones/M_-nome.md`.

Non è burocrazia. È il momento in cui i numeri sono ancora sotto gli occhi —
quante righe sono state escluse, quanto è durato il caricamento, quale join
sbagliato ha raddoppiato il fatturato. Se non si scrive adesso, fra tre
settimane si scriverà "ho costruito una pipeline", che non dice niente.

Da quei file nasce il case study del portfolio. Scriverli è già metà del lavoro
di pubblicazione.

### Il modello da seguire

```markdown
# M_ — Nome della milestone

Chiusa il GG/MM/AAAA · commit iniziale `abc1234` · commit finale `def5678`

## 1. Cosa è stato costruito
Tre o quattro frasi. Cosa esiste adesso che prima non c'era.

## 2. File creati e modificati
Elenco con percorso completo e una riga di scopo per ciascuno.

## 3. Decisioni tecniche
### Scelta: ...
**Alternativa scartata:** ...
**Perché:** ...

## 4. Numeri misurati
Righe, secondi, megabyte. Misurati, non stimati.

## 5. Problemi incontrati
Cosa si è rotto e come è stato risolto. Anche gli errori stupidi:
sono quelli che si ripetono.

## 6. Cosa resta aperto
Debito tecnico dichiarato, con il motivo per cui è accettabile adesso.

## 7. Come verificarlo
I comandi esatti per riprodurre il risultato su una macchina pulita.
```

---

## Etichette

| Etichetta | Uso |
|---|---|
| `M1` … `M8` | Milestone di appartenenza |
| `ingestione` | Tutto ciò che tocca lo strato `raw` |
| `dbt` | Modelli, test, documentazione dbt |
| `modellazione` | Decisioni sullo schema a stella |
| `qualità` | Test e controlli |
| `infra` | Docker, CI, Makefile |
| `dashboard` | Metabase |
| `documentazione` | Relazioni di milestone, README |
| `bloccante` | Impedisce di procedere |

---

## M1 — Fondamenta

Obiettivo: una macchina pulita esegue `docker compose up` e ha un PostgreSQL
funzionante, con la CI verde su ogni push.

### M1-T1 · Verificare la licenza della sorgente
Aprire la scheda UCI del dataset, leggere la licenza per intero, salvare la
citazione con il DOI in `docs/decisioni.md`.
**Fatto quando:** la citazione completa è nel repository e la licenza risulta
CC BY 4.0.
Etichette: `documentazione`, `bloccante`

### M1-T2 · Creare il repository pubblico
Nome `bi-pipeline`, licenza MIT sul codice, `.gitignore` per Python, `README.md`
con una riga di descrizione.
**Fatto quando:** il repository esiste ed è visibile senza autenticazione.

### M1-T3 · Ambiente Python isolato
`uv` oppure `venv`, Python 3.12.
**Fatto quando:** `python --version` dentro l'ambiente dà la versione attesa.

### M1-T4 · `pyproject.toml` con dipendenze bloccate
`pandas`, `openpyxl`, `psycopg`, `dbt-postgres`, `prefect`, `python-dotenv`.
Versioni fissate, non intervalli.
**Fatto quando:** l'installazione su una macchina pulita produce le stesse
versioni.

### M1-T5 · Strumenti di qualità
`ruff` per formattazione e lint, `mypy` in modalità stretta sui moduli di
ingestione, hook pre-commit che li esegue.
**Fatto quando:** un commit con codice mal formattato viene rifiutato.

### M1-T6 · `docker-compose.yml` con PostgreSQL
PostgreSQL 16, volume persistente, porta esposta, credenziali da `.env`.
**Fatto quando:** `docker compose up -d` e poi `psql` si collega.
Etichette: `infra`, `bloccante`

### M1-T7 · `.env.example` e gestione dei segreti
Tutte le variabili documentate con un valore di esempio. Il `.env` vero è in
`.gitignore`.
**Fatto quando:** `git status` non mostra mai `.env`.

### M1-T8 · Struttura delle cartelle
Creare `ingestion/`, `dbt/`, `orchestration/`, `docs/milestones/`, `metabase/`
con un `.gitkeep` dove servono.
**Fatto quando:** l'albero corrisponde al piano.

### M1-T9 · `Makefile` con i comandi principali
`make up`, `make down`, `make ingest`, `make build`, `make test`, `make docs`.
**Fatto quando:** ogni comando esiste, anche se per ora alcuni non fanno nulla.

### M1-T10 · CI su GitHub Actions
Lint, type check e — quando ci saranno — i test, su ogni push e pull request.
**Fatto quando:** il badge verde compare nel README.

### M1-T11 · Documentazione della milestone M1
`docs/milestones/M1-fondamenta.md` secondo il modello.
Etichette: `documentazione`

---

## M2 — Ingestione

Obiettivo: un milione di righe dentro lo schema `raw`, con un caricamento che
si può rilanciare senza duplicare niente.

### M2-T1 · Script di scaricamento con verifica del checksum
`ingestion/sources/online_retail.py` scarica il file da UCI, ne calcola lo
SHA-256 e lo confronta con quello atteso salvato nel repository.
**Fatto quando:** un file corrotto o cambiato fa fallire lo script con un
messaggio chiaro.
Etichette: `ingestione`, `bloccante`

### M2-T2 · Conversione da Excel a CSV
Il file sorgente è `.xlsx` su due fogli, uno per anno. Convertirli in CSV una
volta sola: leggere Excel a ogni esecuzione è lento e inutile.
**Fatto quando:** esistono due CSV e la somma delle righe è 1.067.371.

### M2-T3 · Profilazione della sorgente
Prima di scrivere qualsiasi trasformazione: contare righe, valori nulli per
colonna, valori distinti, minimi e massimi, e **verificare l'elenco dei
problemi ipotizzati nel piano**.
**Fatto quando:** ogni riga della tabella "Lo sporco che ci aspettiamo" ha
accanto un numero misurato.
Etichette: `ingestione`, `documentazione`

### M2-T4 · Schema `raw` e tabella di atterraggio
Tutte le colonne come testo, più `caricato_il` e `file_origine`. Nessun vincolo,
nessuna conversione: se il dato è sporco, entra sporco.
**Fatto quando:** la tabella esiste e accetta qualsiasi contenuto.
Etichette: `ingestione`, `modellazione`

### M2-T5 · Caricamento con `COPY` a blocchi
`ingestion/load.py` usa `COPY` di PostgreSQL invece di inserimenti riga per
riga, a blocchi da centomila.
**Fatto quando:** il caricamento completo termina e le righe in tabella
corrispondono a quelle nei CSV.

### M2-T6 · Misurare `COPY` contro `to_sql`
Caricare centomila righe nei due modi e cronometrare.
**Fatto quando:** i due tempi sono nella documentazione di M2. È uno dei numeri
che finiranno nel case study.
Etichette: `documentazione`

### M2-T7 · Registro dei caricamenti
`ingestion/registry.py` scrive in una tabella: file, checksum, istante, righe
caricate, esito.
**Fatto quando:** dopo due esecuzioni ci sono due righe nel registro.

### M2-T8 · Idempotenza del caricamento
Rilanciare l'ingestione dello stesso file non deve duplicare. Strategia:
cancellare e ricaricare per file d'origine, dentro una transazione.
**Fatto quando:** tre esecuzioni consecutive lasciano sempre 1.067.371 righe.
Etichette: `ingestione`, `bloccante`

### M2-T9 · Comportamento in caso di interruzione
Interrompere il caricamento a metà (Ctrl-C) e verificare che la tabella resti
coerente, non a metà.
**Fatto quando:** dopo un'interruzione il conteggio è zero oppure completo, mai
un valore intermedio.
Etichette: `qualità`

### M2-T10 · Documentazione della milestone M2
Con i numeri della profilazione e il confronto dei tempi di caricamento.
Etichette: `documentazione`

---

## M3 — Staging

Obiettivo: un modello pulito, tipizzato e deduplicato, con il conteggio
esplicito di tutto ciò che è stato escluso.

### M3-T1 · Inizializzare dbt
`dbt init`, `profiles.yml.example` nel repository, `profiles.yml` vero ignorato.
**Fatto quando:** `dbt debug` risponde che la connessione funziona.
Etichette: `dbt`, `bloccante`

### M3-T2 · Dichiarare la sorgente
`_sources.yml` con la tabella `raw`, la descrizione e il controllo di
freschezza su `caricato_il`.
**Fatto quando:** `dbt source freshness` gira senza errori.

### M3-T3 · Due target: `dev` e `prod`
`dev` limita a un trimestre di dati, `prod` prende tutto. Il limite si applica
con una macro, non copiando i modelli.
**Fatto quando:** `dbt build --target dev` è sensibilmente più veloce di `prod`
e i modelli sono gli stessi.
Etichette: `dbt`

### M3-T4 · `stg_vendite`: tipi e nomi
Conversione dei tipi, rinomina in italiano coerente, nessun join.
**Fatto quando:** ogni colonna ha il tipo giusto e nessuna conversione fallisce
in silenzio.

### M3-T5 · Marcare i resi
`is_reso` vero quando il numero di fattura inizia per `C`. I resi **restano**.
**Fatto quando:** il conteggio dei resi corrisponde a quello della profilazione.

### M3-T6 · Escludere i codici di servizio
`POST`, `DOT`, `M`, `BANK CHARGES`, `AMAZONFEE`, `CARRIAGE` e quanto altro
emerso in M2-T3. L'elenco sta in una seed, non nel SQL.
**Fatto quando:** esiste `seeds/codici_di_servizio.csv` e il modello la usa.
Etichette: `dbt`, `modellazione`

### M3-T7 · Escludere prezzi non positivi
Con il conteggio di quante righe se ne vanno.
**Fatto quando:** il numero è documentato.

### M3-T8 · Deduplica
Righe identiche su fattura, prodotto, quantità e istante.
**Fatto quando:** il conteggio prima e dopo è documentato.

### M3-T9 · Normalizzare le descrizioni
Spazi, maiuscole, e per ogni codice la descrizione più frequente.
**Fatto quando:** ogni `StockCode` ha esattamente una descrizione.

### M3-T10 · Tabella delle esclusioni
Un modello che conta, per motivo, quante righe sono state escluse. È la base
del test di quadratura di M5.
**Fatto quando:** la somma delle esclusioni più le righe di `stg_vendite`
uguaglia le righe di `raw`.
Etichette: `dbt`, `qualità`

### M3-T11 · Documentazione della milestone M3
Con la tabella delle esclusioni e i numeri.
Etichette: `documentazione`

---

## M4 — Schema a stella

Obiettivo: un fatto e quattro dimensioni, con chiavi surrogate e il fatto
costruito in modo incrementale.

### M4-T1 · `dim_data` generata
Calendario completo del periodo, buchi compresi. Anno, trimestre, mese,
settimana, giorno della settimana, weekend, festivi del Regno Unito.
**Fatto quando:** il numero di righe corrisponde ai giorni fra la prima e
l'ultima vendita, senza salti.
Etichette: `modellazione`

### M4-T2 · `dim_prodotto`
Chiave surrogata, codice, descrizione normalizzata, prima e ultima vendita,
prezzo medio.
**Fatto quando:** `unique` e `not_null` sulla chiave passano.

### M4-T3 · `dim_cliente` con il membro *Sconosciuto*
Chiave `-1` per le righe senza cliente. Non è un caso limite: è un quarto dei
dati.
**Fatto quando:** esiste la riga con chiave `-1` e le vendite senza cliente vi
puntano.
Etichette: `modellazione`, `bloccante`

### M4-T4 · `dim_paese`
Nome normalizzato, macro-area, flag Regno Unito. Attenzione ai valori strani
emersi in profilazione (`Unspecified`, `European Community`).
**Fatto quando:** ogni paese presente nei dati ha una riga.

### M4-T5 · `fct_vendite`
Le quattro chiavi, la fattura come dimensione degenere, quantità, prezzo,
valore, `is_reso`.
**Fatto quando:** nessuna chiave è nulla e il totale del valore corrisponde a
quello calcolato su `stg_vendite`.

### M4-T6 · Rendere il fatto incrementale
`materialized='incremental'`, con la data come chiave di aggiornamento e
`is_incremental()` per il filtro.
**Fatto quando:** una seconda esecuzione elabora solo le righe nuove, e il
totale resta identico a una ricostruzione completa.
Etichette: `dbt`, `modellazione`

### M4-T7 · Indici sulle chiavi esterne
Un indice per ogni chiave del fatto, con `post_hook`.
**Fatto quando:** `EXPLAIN` di una query aggregata mostra l'uso degli indici.

### M4-T8 · Confronto prima e dopo gli indici
Cronometrare la stessa query aggregata con e senza indici.
**Fatto quando:** i due tempi sono documentati. Su un milione di righe la
differenza si vede, ed è un numero che vale nel case study.
Etichette: `documentazione`

### M4-T9 · Documentazione dei modelli in `_marts.yml`
Ogni tabella e ogni colonna con la propria descrizione.
**Fatto quando:** `dbt docs generate` non segnala colonne senza descrizione.

### M4-T10 · Diagramma dello schema a stella
`docs/schema-a-stella.png`. È l'immagine che finisce nel case study, quindi va
fatta bene: entità, chiavi, cardinalità.
**Fatto quando:** l'immagine esiste ed è leggibile a schermo intero.
Etichette: `documentazione`

### M4-T11 · Documentazione della milestone M4
Etichette: `documentazione`

---

## M5 — Qualità

Obiettivo: i test intercettano ogni modo in cui questi dati possono mentire.

### M5-T1 · Test generici sulle dimensioni
`unique` e `not_null` su tutte le chiavi surrogate.

### M5-T2 · Test generici sul fatto
`not_null` su tutte le chiavi esterne.

### M5-T3 · `relationships` fatto → dimensioni
Quattro test, uno per dimensione.
**Fatto quando:** nessuna riga orfana.
Etichette: `qualità`, `bloccante`

### M5-T4 · `accepted_values` su `is_reso`
**Fatto quando:** solo vero e falso sono ammessi.

### M5-T5 · Test singolare: prezzo positivo
Nessuna riga in `stg_vendite` con prezzo minore o uguale a zero.

### M5-T6 · Test singolare: coerenza dei resi
Nessuna riga con `is_reso` vero e quantità positiva, e viceversa.

### M5-T7 · Test singolare: quadratura dei totali
Righe in `raw` = righe in `fct_vendite` + esclusioni dichiarate.
**Fatto quando:** il test passa. Se non passa, qualcosa sparisce senza che
nessuno lo sappia — ed è il motivo per cui questo test esiste.
Etichette: `qualità`, `bloccante`

### M5-T8 · Freschezza della sorgente
Soglie di avviso ed errore su `caricato_il`.

### M5-T9 · `dbt docs` e lineage
Generare la documentazione e verificare che il grafo delle dipendenze sia
corretto.
**Fatto quando:** `dbt docs serve` mostra il lineage completo da `raw` ai marts.

### M5-T10 · I test in CI
Aggiungere `dbt build` alla pipeline di GitHub Actions, su un PostgreSQL di
servizio.
**Fatto quando:** una pull request che rompe un test viene bloccata.
Etichette: `infra`, `qualità`

### M5-T11 · Documentazione della milestone M5
Con l'elenco dei test e cosa ciascuno protegge.
Etichette: `documentazione`

---

## M6 — Orchestrazione

Obiettivo: un comando esegue tutto, e se qualcosa fallisce si capisce dove.

### M6-T1 · Flusso Prefect
`orchestration/flow.py`: scaricamento → caricamento → `dbt build` → test.
**Fatto quando:** un solo comando porta da file vuoto a marts pronti.

### M6-T2 · Ritentativi sui passi di rete
Solo sullo scaricamento: ritentare una trasformazione fallita non ha senso.
**Fatto quando:** un errore di rete simulato viene ritentato tre volte.

### M6-T3 · Registrazione dei tempi per passo
Ogni passo scrive quanto è durato e quante righe ha toccato.
**Fatto quando:** l'esecuzione produce un riepilogo leggibile.

### M6-T4 · Comportamento al fallimento
Se `dbt build` fallisce, il flusso si ferma e non prosegue con i test.
**Fatto quando:** un modello rotto di proposito interrompe la catena.

### M6-T5 · Esecuzione programmata (facoltativa)
Uno scheduler locale che esegue il flusso ogni notte.
**Fatto quando:** documentato. Su dati storici non serve, ma dimostra che ci
sai fare.

### M6-T6 · Documentazione della milestone M6
Etichette: `documentazione`

---

## M7 — Cruscotti

Obiettivo: cinque indicatori su tre pagine, tutti calcolati in dbt e non in
Metabase.

### M7-T1 · Metabase in `docker-compose.yml`
Con volume persistente, così le dashboard sopravvivono a un riavvio.
**Fatto quando:** dopo `docker compose down && up` le dashboard ci sono ancora.
Etichette: `infra`, `dashboard`

### M7-T2 · Collegare Metabase allo schema `marts`
Utente di sola lettura, non l'amministratore.
**Fatto quando:** Metabase vede le cinque tabelle e non riesce a scrivere.

### M7-T3 · I cinque indicatori come domande salvate
Fatturato netto, ordini, scontrino medio, tasso di reso, clienti attivi.
**Fatto quando:** ogni numero coincide con la stessa query lanciata in `psql`.
Etichette: `dashboard`, `bloccante`

### M7-T4 · Cruscotto 1 — Andamento
I cinque indicatori in alto, la serie mensile del fatturato, il confronto con
l'anno precedente.

### M7-T5 · Cruscotto 2 — Prodotti e clienti
Primi venti prodotti per valore, distribuzione dello scontrino, clienti per
fatturato, prodotti con il tasso di reso più alto.

### M7-T6 · Cruscotto 3 — Geografia
Fatturato per paese, Regno Unito contro estero, e la scheda del mercato
italiano se i volumi lo giustificano.
**Nota:** verificare prima quante righe ha l'Italia. Se sono poche, la pagina
lo dichiara invece di far sembrare significativo un campione minuscolo.

### M7-T7 · Filtri comuni
Periodo, paese, con o senza resi. Collegati a tutte le schede della pagina.

### M7-T8 · Modelli pre-aggregati se serve
Se una pagina impiega più di tre secondi, si aggiunge un `agg_vendite_giorno`
in dbt. **Non** si ottimizza prima di aver misurato.
**Fatto quando:** i tempi di risposta sono misurati e documentati.

### M7-T9 · Documentazione della milestone M7
Con gli screenshot dei tre cruscotti.
Etichette: `documentazione`

---

## M8 — Pubblicazione e ingresso nel portfolio

### M8-T1 · README completo
Cosa fa, stack, come funziona con il diagramma, avvio in locale, struttura,
decisioni tecniche, limiti noti, licenza e **attribuzione della sorgente**.
**Fatto quando:** una persona che non conosce il progetto lo avvia seguendo
solo il README.

### M8-T2 · Prova su macchina pulita
Clonare in una cartella nuova e seguire il README alla lettera.
**Fatto quando:** funziona senza dover indovinare niente.
Etichette: `qualità`, `bloccante`

### M8-T3 · Screenshot e video
Tre screenshot dei cruscotti e un video breve della pipeline che gira.

### M8-T4 · Decidere la sorte della demo online
Verificare quanto pesa il database. Se non sta nei piani gratuiti, si pubblica
una fetta ridotta oppure si sostituisce con il video — e nel README si scrive
quale delle due e perché.
**Fatto quando:** la decisione è presa e motivata per iscritto.

### M8-T5 · Raccogliere le metriche dell'hero
Righe caricate, durata del caricamento, test superati, righe escluse. Numeri
misurati, presi dalle documentazioni di milestone.

### M8-T6 · Scrivere il case study MDX
`src/content/projects/it/bi-pipeline.mdx` e la versione inglese: togliere
`draft: true`, compilare `architecture`, `metrics`, `stack`, `links`.
**Fatto quando:** `npm run build` genera le due pagine e i test dei contenuti
passano.

### M8-T7 · Copertina e immagini
`public/images/projects/bi-pipeline/`: copertina e diagramma dello schema.

### M8-T8 · Verifica finale del portfolio
`npm run check` e `npm run build`, con il progetto visibile e in ordine.

### M8-T9 · Documentazione della milestone M8
La chiusura: cosa si è imparato, cosa si rifarebbe diversamente.
Etichette: `documentazione`

---

## Ordine e dipendenze

```
M1 ──► M2 ──► M3 ──► M4 ──► M5 ──► M7 ──► M8
                              │      ▲
                              └► M6 ─┘
```

M6 (orchestrazione) dipende da M5 ma non blocca M7: i cruscotti si possono
costruire mentre il flusso Prefect prende forma. Tutto il resto è in sequenza,
perché ogni strato legge quello sotto.

**I tre task che bloccano tutto,** se saltati:

- **M1-T1** — se la licenza non fosse quella che dice, il progetto non si può
  pubblicare. Va verificata prima di scrivere una riga di codice.
- **M2-T8** — senza idempotenza ogni rilancio raddoppia i dati, e ci si accorge
  del problema quando il fatturato è già sbagliato in dashboard.
- **M5-T7** — la quadratura dei totali è l'unico test che accorge se le righe
  spariscono lungo la strada.
