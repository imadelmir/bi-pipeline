# BI Pipeline — piano di progetto

**Imad El Mir** · progetto 3 del portfolio · categoria `data-bi`
Python · PostgreSQL · dbt · Prefect · Docker · Metabase

---

## In una frase

Un milione di righe di vendite grezze entrano da un file, escono da un cruscotto
con cinque indicatori, e in mezzo attraversano quattro strati che si possono
rilanciare uno per uno senza sporcare niente.

---

## Indice

1. [La sorgente, e perché questa](#1-la-sorgente-e-perché-questa)
2. [Cosa questi dati non possono dire](#2-cosa-questi-dati-non-possono-dire)
3. [Lo sporco che ci aspettiamo](#3-lo-sporco-che-ci-aspettiamo)
4. [Architettura, quattro strati](#4-architettura-quattro-strati)
5. [Il modello dimensionale](#5-il-modello-dimensionale)
6. [I cinque indicatori](#6-i-cinque-indicatori)
7. [La qualità dei dati](#7-la-qualità-dei-dati)
8. [Struttura del repository](#8-struttura-del-repository)
9. [Le milestone in sintesi](#9-le-milestone-in-sintesi)
10. [Come entra nel portfolio](#10-come-entra-nel-portfolio)
11. [Cosa non fare](#11-cosa-non-fare)

---

## 1. La sorgente, e perché questa

**Online Retail II**, UCI Machine Learning Repository.

| | |
|---|---|
| Contenuto | Tutte le transazioni di un grossista inglese di articoli da regalo |
| Periodo | 01/12/2009 – 09/12/2011 |
| Righe | 1.067.371 |
| File | `online_retail_II.xlsx`, 43,5 MB, un solo scaricamento |
| Licenza | **CC BY 4.0** — riuso libero con attribuzione |
| DOI | 10.24432/C5CG6D |
| Citazione | Chen, D. (2012). *Online Retail II* [Dataset]. UCI Machine Learning Repository |

Otto colonne, e non una di più:

```
Invoice       codice fattura. Se inizia per C e' un reso
StockCode     codice prodotto
Description   nome del prodotto, testo libero
Quantity      pezzi. Negativa sui resi
InvoiceDate   data e ora
Price         prezzo unitario in sterline
Customer ID   codice cliente. Mancante in circa un quarto delle righe
Country       paese del cliente
```

### Perché non un marchio famoso

Nessuna catena pubblica i propri scontrini: sono il dato commerciale più
protetto che esista. I marchi noti che compaiono nei dataset aperti hanno
pubblicato sempre la fetta che non fa male, e infatti sono inutilizzabili qui:

| Sorgente | Marchio | Perché è stata scartata |
|---|---|---|
| Rossmann | vero | Solo incasso giornaliero per negozio: **nessun prodotto, nessun cliente**. Due dimensioni: lo schema a stella non sta in piedi |
| Instacart | vero | 32 milioni di righe **senza prezzi**. Non si calcola un fatturato |
| H&M | vero | Prezzi scalati di un fattore non dichiarato, 31,8 milioni di righe, 3,5 GB, nessun numero di scontrino |
| Olist | Brasile | Buono, ma è il dataset più usato al mondo per esercitarsi: si riconosce a colpo d'occhio |
| dunnhumby | anonimo | Il più ricco di tutti. Resta come aggiornamento futuro: stessa architettura, dimensioni più profonde |

Online Retail II vince su tre cose concrete: licenza verificata e permissiva,
quarantatré megabyte senza registrarsi, e **prezzi in valuta vera**.

### L'attribuzione non è un dettaglio

CC BY significa che il riuso è libero *a condizione* di citare la fonte. Nel
README e nel piede del cruscotto va la citazione completa con il DOI. Costa
due righe e distingue chi ha letto la licenza da chi ha scaricato e basta.

---

## 2. Cosa questi dati non possono dire

Prima di progettare, si scrive cosa **non** si potrà mostrare. È la parte che
di solito manca, e che poi produce indicatori inventati.

### Il margine è fuori

Il piano originale prevedeva il margine fra i cinque indicatori. **Non è
calcolabile**: serve il costo d'acquisto, e nessun dataset pubblico al mondo lo
contiene — è l'informazione più riservata di un'azienda commerciale.

Aggiungere una colonna `cost` inventata renderebbe finto tutto il cruscotto.
Il margine esce dagli indicatori, e nel README c'è scritto perché.

### Le dimensioni a evoluzione lenta sono fuori

Il piano prevedeva una SCD di tipo 2 su `dim_prodotto`. Anche questa **non è
onesta**: una dimensione storicizzata registra le versioni successive dello
stesso record, e qui esiste una sola fotografia. Simularla vorrebbe dire
inventare cambiamenti mai avvenuti.

Al suo posto entrano i **modelli incrementali** di dbt, che questi dati
reggono davvero perché sono ordinati nel tempo.

### Il negozio non esiste

È un rivenditore *senza punti vendita*: vende solo online. La dimensione
`dim_negozio` del piano diventa `dim_paese` — i clienti sono distribuiti su una
quarantina di paesi, quindi la geografia c'è ed è vera. Non si finge che i
paesi siano negozi: si chiamano paesi.

---

## 3. Lo sporco che ci aspettiamo

Questo elenco è un'**ipotesi da verificare in M2**, non un dato acquisito. La
prima cosa che fa la milestone di ingestione è contare quanto di questo è vero,
e scriverlo nella documentazione con i numeri misurati.

| Problema atteso | Perché è un problema | Cosa si farà |
|---|---|---|
| Fatture che iniziano per `C` | Sono resi, con quantità negative. Ignorarli gonfia il fatturato | Restano nel fatto, marcati. Il netto è la somma, il lordo esclude i negativi |
| `Customer ID` mancante | Circa un quarto delle righe. Sono vendite vere, ma non attribuibili | Chiave verso un membro *Sconosciuto* nella dimensione, non righe buttate |
| Codici di servizio | `POST`, `DOT`, `M`, `BANK CHARGES`, `AMAZONFEE`, `CARRIAGE` non sono prodotti | Esclusi dal fatto e censiti in una tabella a parte, con il motivo |
| Prezzo pari o inferiore a zero | Rettifiche contabili, non vendite | Esclusi, contati e documentati |
| Righe duplicate esatte | Stessa fattura, prodotto, quantità e istante | Deduplica in staging, con il conteggio prima e dopo |
| Descrizioni incoerenti | Lo stesso `StockCode` con nomi diversi | Si tiene la descrizione più frequente per codice |
| Spazi e maiuscole | `Description` è testo libero digitato a mano | Normalizzazione in staging |

**Regola:** nessuna riga sparisce in silenzio. Ogni esclusione produce un
numero, e quel numero finisce nella documentazione della milestone.

---

## 4. Architettura, quattro strati

```
   file .xlsx
       │
       ▼
┌──────────────┐   Python. Nessuna trasformazione: i dati entrano
│  1. raw      │   come sono, con l'aggiunta della sola data di carico.
└──────┬───────┘   Idempotente: ricaricare non duplica.
       │
       ▼
┌──────────────┐   dbt. Tipi, nomi, pulizia, deduplica.
│  2. staging  │   Un modello per ogni tabella sorgente, nessun join.
└──────┬───────┘
       │
       ▼
┌──────────────┐   dbt. Schema a stella: un fatto, quattro dimensioni.
│  3. marts    │   Il fatto e' incrementale, le dimensioni si ricostruiscono.
└──────┬───────┘
       │
       ▼
┌──────────────┐   Metabase. Cinque indicatori, tre cruscotti.
│ 4. presentaz.│   Legge solo da marts, mai da staging o raw.
└──────────────┘
```

| Strato | Strumento | Regola invariabile |
|---|---|---|
| `raw` | Python + `COPY` | Nessuna trasformazione. Se il dato è sporco entra sporco |
| `staging` | dbt, viste | Un modello per sorgente. Nessun join fra sorgenti diverse |
| `marts` | dbt, tabelle | Solo qui si uniscono le cose. Solo qui nascono le chiavi |
| presentazione | Metabase | Nessuna logica di business nei grafici. Se serve un calcolo, si fa in dbt |

### Perché ELT e non ETL

Le trasformazioni restano scritte in SQL dentro il repository: versionate,
leggibili in una pull request, testabili con un comando. In un ETL classico la
logica vive dentro uno strumento e si rivede solo aprendo quello strumento.

### Perché ogni strato è idempotente

Se la pipeline muore a metà, la si rilancia e basta. Senza idempotenza un
fallimento lascia dati a metà, e l'unica via d'uscita è capire a mano cos'era
entrato e cosa no — di notte, con il cruscotto già rotto.

### Perché `COPY` e non `to_sql`

Caricare un milione di righe con `pandas.to_sql` significa un `INSERT` per riga
e diversi minuti di attesa. `COPY` di PostgreSQL fa lo stesso lavoro in
secondi. Il confronto misurato fra i due va nella documentazione di M2: è il
genere di numero che rende credibile il resto.

---

## 5. Il modello dimensionale

```
                   ┌──────────────┐
                   │   dim_data   │
                   └──────┬───────┘
                          │
  ┌──────────────┐   ┌────▼─────────────────┐   ┌──────────────┐
  │ dim_prodotto ├───┤     fct_vendite      ├───┤  dim_cliente │
  └──────────────┘   │                      │   └──────────────┘
                     │  numero_fattura (DD) │
                     └────┬─────────────────┘
                          │
                   ┌──────▼───────┐
                   │  dim_paese   │
                   └──────────────┘
```

### `fct_vendite`

**Grana: una riga di fattura.** Un prodotto, su una fattura, in un istante.
È la grana più fine disponibile, e da lì si aggrega verso l'alto senza mai
dover tornare alla sorgente.

| Colonna | Tipo | Nota |
|---|---|---|
| `data_key` | int | → `dim_data` |
| `prodotto_key` | int | → `dim_prodotto` |
| `cliente_key` | int | → `dim_cliente`, punta a *Sconosciuto* quando manca |
| `paese_key` | int | → `dim_paese` |
| `numero_fattura` | text | Dimensione degenere: sta nel fatto, non ha tabella propria |
| `quantita` | int | Negativa sui resi |
| `prezzo_unitario` | numeric(10,2) | Sterline |
| `valore` | numeric(12,2) | `quantita * prezzo_unitario`, negativo sui resi |
| `is_reso` | boolean | Vero se la fattura inizia per `C` |

### Le quattro dimensioni

| Dimensione | Righe attese | Contenuto |
|---|---|---|
| `dim_data` | ~740 | Generata, non letta: data, anno, trimestre, mese, settimana, giorno della settimana, festivo, weekend |
| `dim_prodotto` | ~5.000 | Codice, descrizione normalizzata, prima e ultima vendita, prezzo medio |
| `dim_cliente` | ~6.000 | Codice, paese principale, prima e ultima fattura, numero di ordini |
| `dim_paese` | ~40 | Nome normalizzato, macro-area, flag Regno Unito |

### La fattura come dimensione degenere

`numero_fattura` sta dentro il fatto e non ha una tabella. Una `dim_fattura`
conterrebbe solo la chiave e nient'altro: sarebbe un join in più per zero
informazione. È un caso da manuale, e vale la pena spiegarlo nel case study.

### Perché le chiavi surrogate

Il fatto non punta a `StockCode` ma a un intero generato. Costa un passaggio in
più, e restituisce tre cose: join più veloci, indipendenza dai codici della
sorgente, e la possibilità di avere un membro *Sconosciuto* con chiave `-1` per
le righe senza cliente — che altrimenti andrebbero buttate.

### `dim_data` si genera, non si legge

Le date presenti nelle vendite hanno buchi: i giorni di chiusura non compaiono.
Se la dimensione nascesse dai dati, un grafico per giorno salterebbe le
domeniche e nessuno se ne accorgerebbe. Si genera il calendario completo del
periodo, e i giorni senza vendite restano visibili come zeri.

---

## 6. I cinque indicatori

| Indicatore | Formula | Dove si rompe se non stai attento |
|---|---|---|
| **Fatturato netto** | `SUM(valore)` | Include i resi come negativi. Il lordo, senza resi, è un secondo numero: la differenza fra i due **è** l'indicatore dei resi |
| **Ordini** | `COUNT(DISTINCT numero_fattura)` escludendo i resi | Contare le righe invece delle fatture moltiplica il numero per il carrello medio |
| **Scontrino medio** | `fatturato netto / ordini` | Se al numeratore ci sono i resi e al denominatore no, il valore è distorto verso il basso |
| **Tasso di reso** | `valore dei resi / fatturato lordo` | Va sul valore, non sul conteggio: un reso da mille sterline non pesa quanto uno da due |
| **Clienti attivi** | `COUNT(DISTINCT cliente_key)` escludendo *Sconosciuto* | Includere lo *Sconosciuto* lo conta come un cliente solo, sbagliando in difetto |

Cinque numeri, tutti calcolabili dai dati che ci sono. Nessuno stimato.

---

## 7. La qualità dei dati

I test non sono un adempimento: sono la ragione per cui il cruscotto si può
guardare senza controllare a mano. Ogni test che segue nasce da un modo
concreto in cui questi dati possono mentire.

| Test | Su cosa | Cosa impedisce |
|---|---|---|
| `unique` | chiavi delle dimensioni | Una dimensione con chiavi doppie moltiplica il fatturato nei join |
| `not_null` | tutte le chiavi del fatto | Una chiave nulla fa sparire righe da ogni join interno |
| `relationships` | fatto → ogni dimensione | Righe orfane: vendite di prodotti che non esistono in anagrafica |
| `accepted_values` | `is_reso` | Che diventi un terzo stato per errore di tipo |
| singolare: `prezzo_positivo` | `staging` | Che le rettifiche a prezzo zero rientrino di nascosto |
| singolare: `coerenza_resi` | `marts` | Che una riga marcata reso abbia quantità positiva |
| singolare: `quadratura_totali` | `raw` vs `marts` | Che lo scarto fra righe caricate e righe modellate sia diverso dalle esclusioni dichiarate |

L'ultimo è il più importante e quasi nessuno lo scrive: **la somma delle righe
escluse deve tornare**. Se in `raw` ci sono 1.067.371 righe e in `fct_vendite`
ne arrivano 950.000, la differenza deve corrispondere esattamente alle
esclusioni documentate. Se non torna, qualcosa sparisce senza che nessuno lo
sappia.

---

## 8. Struttura del repository

```
bi-pipeline/
├── ingestion/
│   ├── sources/
│   │   └── online_retail.py     # scarica, verifica il checksum, converte
│   ├── load.py                  # COPY a blocchi verso lo schema raw
│   └── registry.py              # registro dei caricamenti: cosa, quando, quante righe
├── dbt/
│   ├── models/
│   │   ├── staging/
│   │   │   ├── _sources.yml
│   │   │   ├── _staging.yml     # test e documentazione
│   │   │   └── stg_vendite.sql
│   │   └── marts/
│   │       ├── _marts.yml
│   │       ├── dim_data.sql
│   │       ├── dim_prodotto.sql
│   │       ├── dim_cliente.sql
│   │       ├── dim_paese.sql
│   │       └── fct_vendite.sql
│   ├── tests/                   # i test singolari
│   ├── macros/
│   ├── dbt_project.yml
│   └── profiles.yml.example
├── orchestration/
│   └── flow.py                  # Prefect: ingestione, dbt, test, notifica
├── metabase/
│   └── cruscotti.md             # cosa contiene ogni cruscotto e perche'
├── docs/
│   ├── milestones/              # una relazione per milestone
│   │   ├── M1-fondamenta.md
│   │   └── ...
│   ├── schema-a-stella.png      # il diagramma del case study
│   └── decisioni.md
├── docker-compose.yml           # PostgreSQL + Metabase
├── .env.example
├── Makefile                     # make up, make ingest, make build, make test
├── pyproject.toml
├── README.md
└── LICENSE
```

### Una relazione per ogni milestone

Come su Football Analytics: quando una milestone chiude, in `docs/milestones/`
nasce un file che racconta cosa è stato costruito, quali decisioni sono state
prese e con quali numeri misurati. Non è burocrazia — è il materiale grezzo
del case study, scritto quando i dettagli sono ancora freschi.

---

## 9. Le milestone in sintesi

Il dettaglio dei task sta in `bi-pipeline-backlog.md`.

| | Milestone | Chiude quando |
|---|---|---|
| **M1** | Fondamenta | `docker compose up` alza PostgreSQL, la CI è verde |
| **M2** | Ingestione | Un milione di righe in `raw`, ricaricabili senza duplicare |
| **M3** | Staging | `stg_vendite` pulito, con i conteggi delle esclusioni |
| **M4** | Schema a stella | Un fatto e quattro dimensioni, chiavi surrogate, fatto incrementale |
| **M5** | Qualità | Tutti i test passano, la quadratura torna |
| **M6** | Orchestrazione | Prefect esegue tutto con un comando, con ritentativi |
| **M7** | Cruscotti | Metabase mostra i cinque indicatori su tre pagine |
| **M8** | Pubblicazione | README con diagramma, case study nel portfolio |

---

## 10. Come entra nel portfolio

Il file è `src/content/projects/{it,en}/bi-pipeline.mdx`, che **esiste già** ed
è marcato `draft: true`. Quando il progetto è finito si toglie quella riga.

Il campo `architecture` del frontmatter è la parte che conta di più:

```yaml
architecture:
  summary: "Quattro stadi indipendenti e idempotenti: ogni stadio si puo'
            rilanciare senza duplicare dati."
  diagram:
    src: /images/projects/bi-pipeline/schema-a-stella.png
    alt: "Schema a stella: fct_vendite al centro, con dim_data,
          dim_prodotto, dim_cliente e dim_paese intorno"
  layers:
    - name: Ingestione
      description: "Scarica, verifica il checksum e scrive in raw. Nessuna trasformazione."
      tech: [python, postgres]
    - name: Staging
      description: "Tipi, nomi, deduplica ed esclusioni, con il conteggio di ognuna."
      tech: [dbt]
    - name: Marts
      description: "Schema a stella: un fatto e quattro dimensioni, con chiavi surrogate."
      tech: [dbt, postgres]
    - name: Presentazione
      description: "Tre cruscotti con i cinque indicatori. Nessun calcolo qui dentro."
      tech: [metabase]
  decisions:
    - choice: "ELT invece di ETL"
      why: "Le trasformazioni restano versionate in SQL e testabili con un comando."
    - choice: "Schema a stella invece di tabelle normalizzate"
      why: "Le query analitiche fanno meno join e restano leggibili."
    - choice: "Idempotenza su ogni stadio"
      why: "Un fallimento a meta' non lascia dati sporchi: si rilancia e basta."

metrics:
  - label: "Righe caricate"
    value: "1.067.371"
    hint: "dalla sorgente, dichiarate e verificate al caricamento"
```

> ⚠️ **La forma di questo blocco non e' libera.** Le chiavi qui sopra rispettano
> `src/lib/content/schema.ts` del portfolio: `diagram` e' un oggetto immagine
> con `src` e `alt` obbligatori, `layers` sono oggetti con `name` e
> `description`, e le decisioni usano `choice` / `why` **in inglese**. Gli slug
> in `tech` sono un enum: un refuso ferma la build. Una versione precedente di
> questo piano usava stringhe semplici e chiavi italiane, e non sarebbe passata.

Le metriche dell'hero sono numeri **misurati**, non stimati: righe caricate,
durata del caricamento, test superati, righe escluse. L'unica gia' certa e'
il conteggio delle righe, perche' lo dichiara la sorgente.

---

## 11. Cosa non fare

- **Non inventare il costo per calcolare il margine.** È la scorciatoia più
  tentante e la più facile da smascherare.
- **Non buttare le righe senza cliente.** Sono un quarto del dataset e sono
  vendite vere: vanno verso un membro *Sconosciuto*.
- **Non cancellare i resi.** Il tasso di reso è uno dei cinque indicatori:
  toglierli significa buttare via l'informazione più interessante.
- **Non mettere logica in Metabase.** Un calcolo scritto dentro un grafico non
  è versionato, non è testato e non lo ritrova nessuno.
- **Non usare `SELECT *` nei modelli dbt.** Il giorno che la sorgente aggiunge
  una colonna, il modello cambia da solo senza che nessuno lo abbia deciso.
- **Non pubblicare il file sorgente nel repository.** 43 MB in git sono 43 MB
  per sempre. Si scarica con uno script, e nel repository c'è il checksum.
- **Non promettere una demo online prima di aver verificato lo spazio.** Un
  database da qualche centinaio di megabyte non sta ovunque: se non ci sta, si
  pubblicano screenshot e un video, e si dice perché.
