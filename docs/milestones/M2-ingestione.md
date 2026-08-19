# M2 — Ingestione

Chiusa il 20/08/2026 · commit iniziale `d5d39ec` · commit finale `bec940e`

Dieci task su dieci. In `raw.vendite` ci sono 1.067.371 righe, e rilanciare
l'ingestione quante volte si vuole ne lascia sempre 1.067.371.

## 1. Cosa è stato costruito

Un'ingestione che si può rilanciare senza pensarci. Scarica l'archivio da UCI,
ne verifica lo SHA-256, converte i due fogli Excel in CSV una volta sola, e li
carica in PostgreSQL con `COPY` dentro una transazione che cancella e ricarica
per file d'origine.

Attorno al caricamento ci sono tre cose che di solito mancano: un **registro**
che dice cosa è stato caricato e com'è andata, una **profilazione** che ha
sostituito un numero misurato a ogni «circa» del piano, e un **confronto
cronometrato** fra `COPY` e `pandas.to_sql`.

Nessuna trasformazione: le colonne sono tutte testo, i dati sporchi entrano
sporchi. A pulirli ci penserà dbt in M3.

## 2. File creati e modificati

| Percorso | Scopo |
| --- | --- |
| `ingestion/sources/online_retail.py` | Scarica, verifica il checksum, estrae, converte in CSV |
| `ingestion/sql/raw.sql` | Schema `raw`, tabella di atterraggio, indice, registro |
| `ingestion/db.py` | Connessione da `.env`, esecuzione dei file SQL |
| `ingestion/load.py` | `COPY` a blocchi, cancella-e-ricarica in transazione |
| `ingestion/registry.py` | Un record per tentativo, su connessione propria |
| `ingestion/profilazione.py` | Genera `docs/profilazione.md` |
| `ingestion/confronto_copy.py` | Genera `docs/confronto-copy.md` |
| `ingestion/percorsi.py`, `ingestion/formato.py` | Percorsi dei dati, numeri leggibili |
| `docs/profilazione.md`, `docs/confronto-copy.md` | I due documenti generati |
| `Makefile`, `make.ps1` | `make ingest` fa il lavoro vero; aggiunti `profila` e `confronto` |
| `pyproject.toml` | `sqlalchemy` dichiarato, serve solo al confronto di M2-T6 |

## 3. Decisioni tecniche

Per esteso in [`docs/decisioni.md`](../decisioni.md): D6 (cosa garantisce
davvero il checksum), D7 (il vuoto diventa `NULL`), D8 (il registro su
connessione propria). In sintesi le altre:

### Scelta: la conversione in CSV avviene una volta sola
**Alternativa scartata:** leggere l'Excel a ogni caricamento.
**Perché:** 62 secondi contro 8. openpyxl deve interpretare XML compresso cella
per cella; un CSV si legge in streaming. Il file convertito resta su disco e il
caricamento parte da lì.

### Scelta: tutte le colonne di `raw` sono `text`
**Alternativa scartata:** i tipi giusti già in atterraggio.
**Perché:** un `numeric` rifiuterebbe la riga con il prezzo scritto male, e il
caricamento morirebbe a metà file proprio sul dato che volevamo vedere. In
`raw` si entra sempre; la selezione avviene dopo, contata e documentata.

### Scelta: un indice su `file_origine`, l'unico dello strato
**Alternativa scartata:** nessun indice, «tanto è uno strato di atterraggio».
**Perché:** ogni ricaricamento comincia con `delete ... where file_origine = ...`.
Senza indice sarebbe una scansione completa del milione di righe a ogni
esecuzione. L'indice pesa 23 MB e si ripaga al primo rilancio.

### Scelta: il valore atteso del checksum si scopre sbagliando
**Alternativa scartata:** scrivere subito il valore giusto.
**Perché:** il primo `SHA256_EXCEL` era un segnaposto, e la prima esecuzione è
fallita apposta. È così che si è visto che il controllo funziona davvero e che
il messaggio d'errore è leggibile — cosa che scrivendo subito il valore giusto
non si sarebbe mai verificata.

## 4. Numeri misurati

### La sorgente

| Cosa | Valore |
| --- | --- |
| Archivio scaricato | 45.622.418 byte (43,5 MiB), in **47 s** |
| Excel estratto | 45.622.278 byte — SHA-256 `bcbe73b3…2df2e980` |
| Conversione in CSV | **62 s** |
| CSV prodotti | `vendite_2009_2010.csv` 47,3 MB · `vendite_2010_2011.csv` 48,6 MB |
| Righe | 525.461 + 541.910 = **1.067.371**, il numero dichiarato da UCI |
| Periodo | dal 01/12/2009 07:45 al 09/12/2011 12:50 |

### Il caricamento

| Cosa | Valore |
| --- | --- |
| Primo caricamento completo | **7,9 s** |
| Secondo e terzo (con cancellazione delle righe precedenti) | 9,1 s · 9,8 s |
| Righe in tabella dopo tre esecuzioni | 1.067.371, sempre |
| `raw.vendite` su disco | 159 MB, più 23 MB di indice — **182 MB** |
| Profilazione dell'intero dataset | 10 s |

### `COPY` contro `pandas.to_sql`, su centomila righe

| Metodo | Secondi | Righe al secondo |
| --- | --- | --- |
| `COPY` | **0,17** | 588.235 |
| `pandas.to_sql` | **2,99** | 33.444 |

**`COPY` è 17,6 volte più veloce.** Proiettato sul milione di righe: 2 secondi
contro 32. Il dettaglio è in [`docs/confronto-copy.md`](../confronto-copy.md).

### Lo sporco, verificato (M2-T3)

Tutte le ipotesi del piano confermate. Il documento completo è
[`docs/profilazione.md`](../profilazione.md).

| Ipotesi | Misurato | Quota |
| --- | --- | --- |
| Resi (fattura per `C`) | 19.494 | 1,83 % |
| `Customer ID` mancante — il piano diceva «circa un quarto» | 243.007 | 22,77 % |
| Codici di servizio del piano | 5.134 | 0,48 % |
| Codici fuori dalla forma di un codice prodotto | 6.094 | 0,57 % |
| Prezzo pari a zero | 6.202 | 0,58 % |
| Prezzo negativo | 5 | 0,00 % |
| Duplicati esatti | 34.604 | 3,24 % |
| Descrizione mancante | 4.382 | 0,41 % |
| Codici con più di una descrizione | 1.232 | — |
| Descrizioni con spazi iniziali o finali | 213.035 | 19,96 % |
| Quantità negativa | 22.950 | 2,15 % |

E i paesi: 43 valori distinti, Regno Unito al **91,94 %** delle righe. L'Italia
ha **1.534 righe e 17 clienti** — un numero da tenere a mente quando in M7-T6
si deciderà se la scheda Italia ha senso.

## 5. Problemi incontrati

**Due test di M5 sarebbero falliti, e si è scoperto qui.** La profilazione ha
trovato 3.457 righe con quantità negativa su fatture che non iniziano per `C`, e
una fattura di reso con quantità positiva: esattamente i due casi che i test di
coerenza dei resi (M5-T6) dichiarano impossibili. Guardandole da vicino: le
prime hanno **tutte** prezzo zero — sono rettifiche di magazzino, con
descrizioni come `damages`, `check`, `missing`, `thrown away` — e la seconda ha
codice `M`, cioè *Manual*. Le esclusioni già previste in M3-T6 e M3-T7 le
tolgono tutte. Il test passerà, ma **passerà per merito di due esclusioni
scritte altrove**: è una dipendenza fra file lontani, e sta scritta in
`docs/profilazione.md` perché chi un giorno allentasse la regola sui prezzi
capisca subito perché si è rotto un test che parla d'altro.

**mypy contro le righe di psycopg.** La connessione era annotata
`Connection[tuple[object, ...]]`, e ogni `int(riga[0])` diventava un errore:
`object` non si converte a intero. La soluzione non era mettere `cast` ovunque
ma usare il tipo che psycopg dichiara per le proprie righe, `TupleRow`.

**Il primo tentativo di uccidere il caricamento è arrivato tardi.** Il file si
carica in 4,5 secondi e il processo era già finito. In più, `$!` in Git Bash
restituisce il PID di bash, che `taskkill` non conosce. Rifatto avviando il
processo da PowerShell e uccidendo l'albero con `taskkill /T /F` sul PID vero,
a tre secondi dall'avvio.

**Il registro sarebbe sparito proprio quando serviva.** Nella prima versione
usava la connessione del caricamento: il rollback che annulla i dati avrebbe
annullato anche la riga «fallito». Corretto con una connessione indipendente in
autocommit (D8), e verificato con un CSV malformato.

**`sqlalchemy` c'era senza essere stato chiesto.** `pandas.to_sql` ne ha
bisogno, e funzionava perché arriva come dipendenza di Prefect. Appoggiarsi a
una dipendenza transitiva significa che il giorno che Prefect cambia idea si
rompe il confronto: dichiarata esplicitamente fra le dipendenze di sviluppo.

## 6. Cosa resta aperto

- **Un record del registro è fermo su `in corso`**, quello del caricamento
  ucciso. Non c'è pulizia automatica ed è voluto: è la firma di un processo
  morto, e cancellarla vorrebbe dire perdere l'unica prova che è successo.
- **I CSV si riconvertono solo se mancano.** Con `--forza` si rifà tutto. È il
  compromesso fra 62 secondi di conversione e il rischio di lavorare su un file
  vecchio; il checksum dell'Excel protegge dal secondo caso.
- **`raw.vendite` non ha chiave primaria né vincoli.** È la regola dello strato,
  non una dimenticanza: i duplicati esatti sono 34.604 e devono poter entrare,
  altrimenti non si potrebbero contare.
- **Il caricamento tiene le righe in memoria** prima di scriverle: circa 500.000
  righe per file. Funziona senza problemi su questa macchina; con un file dieci
  volte più grande andrebbe trasformato in streaming.
- **La CI non prova ancora niente di tutto questo.** Servono un PostgreSQL di
  servizio e dei dati: arriva con M5-T10.

## 7. Come verificarlo

Con Docker acceso e le dipendenze installate:

```bash
make up                 # PostgreSQL
make ingest             # scarica, verifica il checksum, carica in raw
make ingest             # e ancora: il conteggio non cambia
make ingest             # tre volte, sempre 1.067.371

make psql
```

Dentro `psql`:

```sql
select count(*) from raw.vendite;                    -- 1067371
select file_origine, count(*) from raw.vendite group by 1;
select id, file_origine, righe_caricate, esito from raw.registro_caricamenti;
```

Per rigenerare i due documenti:

```bash
make profila            # docs/profilazione.md
make confronto          # docs/confronto-copy.md
```

Per rivedere il comportamento all'interruzione: avviare `make ingest` e
ucciderlo a metà. Il conteggio in tabella resta quello di prima, mai un valore
intermedio, e nel registro compare un record fermo su `in corso`.
