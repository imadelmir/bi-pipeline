# M3 — Staging

Chiusa il 20/08/2026 · commit iniziale `8992ed6` · commit finale `b0ffcdf`

Undici task su undici. Da 1.067.371 righe grezze escono 1.021.137 righe pulite,
e le 46.234 che restano fuori sono contate una per una con il loro motivo.

## 1. Cosa è stato costruito

Un progetto dbt con due target, tre modelli di staging e una seed. I dati
entrano da `raw` come testo ed escono tipizzati, deduplicati, con i nomi in
italiano e una descrizione sola per prodotto.

La cosa che regge tutto il resto è la **contabilità delle esclusioni**: nessuna
riga sparisce in silenzio. `stg_esclusioni` dice quante righe se ne sono andate
e perché, e la somma con le righe tenute dà esattamente le righe della sorgente.
È la base del test di quadratura di M5-T7.

## 2. File creati e modificati

| Percorso | Scopo |
| --- | --- |
| `dbt/dbt_project.yml` | Progetto dbt: staging come viste, marts come tabelle |
| `dbt/profiles.yml.example` | Connessione dalle stesse variabili di `.env` |
| `dbt/models/staging/_sources.yml` | La sorgente `raw`, con il controllo di freschezza |
| `dbt/models/staging/stg_vendite_classificate.sql` | Tipi, resi, e il motivo di esclusione riga per riga |
| `dbt/models/staging/stg_vendite.sql` | Le righe tenute, con una descrizione per prodotto |
| `dbt/models/staging/stg_esclusioni.sql` | Quante righe per motivo, e quanto valore |
| `dbt/models/staging/_staging.yml` | Descrizioni di ogni colonna e 24 test |
| `dbt/seeds/codici_di_servizio.csv` | I 26 codici che non sono prodotti |
| `dbt/macros/limite_periodo.sql` | Il taglio del periodo per il target `dev` |
| `dbt/macros/generate_schema_name.sql` | Schemi `staging`/`marts`, con suffisso in dev |
| `scripts/esegui_dbt.py` | Avvia dbt senza passare dall'eseguibile bloccato da Windows |
| `Makefile`, `make.ps1` | `make build`, `make test`, `make docs` fanno il lavoro vero |

## 3. Decisioni tecniche

### Scelta: un modello intermedio che classifica invece di due che filtrano
**Alternativa scartata:** `stg_vendite` con i suoi filtri e `stg_esclusioni` con
i filtri opposti.
**Perché:** sarebbero due copie della stessa logica, e basta cambiarne una per
avere una quadratura che non torna più — con la beffa che il test di M5-T7
segnalerebbe il problema senza dire dov'è. `stg_vendite_classificate` tiene
**tutte** le righe e attribuisce a ognuna un `motivo_esclusione`; gli altri due
modelli leggono lo stesso giudizio da lati opposti.

### Scelta: i motivi di esclusione hanno una priorità
**Alternativa scartata:** contare ogni motivo separatamente.
**Perché:** una riga può essere insieme un codice di servizio *e* avere prezzo
zero *e* essere un duplicato. Contandola tre volte, la somma delle esclusioni
supererebbe le righe escluse e la quadratura non tornerebbe mai. Con la
priorità — servizio, poi prezzo, poi duplicato — ogni riga finisce in una
casella sola. È anche il motivo per cui i numeri qui non coincidono con quelli
della profilazione di M2, che contava le condizioni una per una.

### Scelta: `dev` e `prod` scrivono in schemi diversi
**Alternativa scartata:** stesso schema, dati diversi.
**Perché:** con un nome solo, un `dbt build --target dev` riscriverebbe le
viste che Metabase sta leggendo — e con un trimestre di dati invece di due
anni. Il cruscotto mostrerebbe numeri sbagliati senza che nessuno abbia toccato
niente. `prod` scrive in `staging`, `dev` in `staging_dev`.

### Scelta: il taglio di `dev` è relativo alla data più recente dei dati
**Alternativa scartata:** filtrare sugli ultimi tre mesi da oggi.
**Perché:** la sorgente si ferma al 09/12/2011. Un filtro su `today()` lascerebbe
zero righe, e il target di sviluppo sarebbe inutilizzabile.

### Scelta: i codici di servizio stanno in una seed, non nel SQL
**Perché:** è un dato, non una regola. Si aggiorna aggiungendo una riga al CSV
senza toccare un modello, e chi legge vede l'elenco completo con il motivo
accanto a ciascun codice.

## 4. Numeri misurati

### Le esclusioni, e la quadratura

| Motivo | Righe | Valore |
| --- | ---: | ---: |
| **tenute** | **1.021.137** | £ 18.927.524 |
| duplicato esatto | 34.153 | £ 456.489 |
| prezzo non positivo | 6.168 | £ 0 |
| codice di servizio | 5.913 | −£ 96.374 |
| **somma** | **1.067.371** | |
| righe in `raw.vendite` | 1.067.371 | |

La somma torna al pezzo.

### Cosa c'è in `stg_vendite`

| | |
| --- | ---: |
| Righe | 1.021.137 |
| Fatture distinte | 46.922 |
| Prodotti distinti | 4.909 |
| Clienti distinti | 5.875 |
| Paesi | 43 |
| Righe di reso | 17.913 |
| Righe senza cliente | 226.979 |
| Periodo | 01/12/2009 → 09/12/2011 |

Ogni codice prodotto ha **esattamente una** descrizione (M3-T9 verificato: zero
codici con più di una descrizione, zero righe senza descrizione).

### I due target

| Target | Schema | Righe | Periodo | `dbt build` |
| --- | --- | ---: | --- | ---: |
| `prod` | `staging` | 1.021.137 | 01/12/2009 → 09/12/2011 | 26 s |
| `dev` | `staging_dev` | 204.415 | 09/09/2011 → 09/12/2011 | 20 s |

Gli stessi identici modelli: cambia solo la macro `limite_periodo`. La
differenza di tempo è modesta perché lo staging è fatto di viste, che si
creano in un istante — il tempo se ne va nei test, che i dati li leggono
davvero. Su `marts`, che sono tabelle, la distanza si vedrà (M4).

### I test

24 test generici, tutti verdi: `not_null` sulle colonne che non possono mancare,
`unique` sui motivi di esclusione e sui codici della seed, `accepted_values` su
`is_reso` e su `motivo_esclusione`.

`dbt build` esegue 28 nodi: 1 seed, 3 modelli, 24 test.

## 5. Problemi incontrati

**La stessa vista dava conteggi diversi.** Prima misura: 1.021.131 righe.
Qualche minuto dopo, senza aver toccato niente: 1.021.134. Poi 1.021.137.

La causa stava nella deduplica. La chiave del piano è fattura + prodotto +
quantità + istante, e **non comprende il prezzo**: dentro un gruppo di
«duplicati» possono quindi finire righe con prezzi diversi, tipicamente una a
prezzo pieno e una a zero. L'ordinamento della `row_number()` era
`order by caricato_il`, che è identico per tutte le righe caricate nella stessa
transazione: quale riga sopravvivesse lo decideva il database, a seconda di come
gli capitava di leggere le pagine. Se toccava alla riga a prezzo zero, veniva
scartata dal filtro sui prezzi — e la sua gemella valida spariva come duplicato.

Corretto ordinando per prezzo decrescente, con tre colonne di spareggio per
rendere l'ordine totale. Ora cinque letture consecutive danno cinque volte
1.021.137. **Un modello che non è deterministico è un modello che mente a caso**,
ed è il tipo di errore che in un cruscotto non si nota mai.

**Windows blocca l'eseguibile di dbt.** `.venv/Scripts/dbt.exe` risponde
«os error 4551»: il criterio di controllo delle applicazioni non lo lascia
partire. Il pacchetto però funziona: `scripts/esegui_dbt.py` ne importa la
funzione di ingresso e la chiama. Il file non può chiamarsi `dbt.py`, o
oscurerebbe il pacchetto vero.

**dbt aggiunge un prefisso ai nomi degli schemi.** Con profilo `staging` e
modelli in `+schema: staging` nasceva `staging_staging`. Serve a far convivere
più sviluppatori nello stesso database, ma qui gli schemi devono chiamarsi come
nel piano — anche perché Metabase e le interrogazioni scritte a mano li cercano
con quel nome. Risolto con `generate_schema_name`, che è poi lo stesso posto
dove si è aggiunta la separazione fra `dev` e `prod`.

**La sintassi dei test generici è cambiata.** dbt 1.12 vuole gli argomenti sotto
la chiave `arguments:`, e senza avvisa con una deprecazione a ogni esecuzione.
Aggiornata.

## 6. Cosa resta aperto

- **Le 4.382 righe senza descrizione non sono un motivo di esclusione.** Non
  serve: hanno tutte prezzo zero e se ne vanno già con quel filtro. In
  `stg_vendite` non resta nessuna riga senza descrizione.
- **`dbt_project.yml` avvisa che la configurazione di `marts` non si applica a
  nessuna risorsa.** È vero: i modelli di marts arrivano in M4.
- **Il controllo di freschezza è dichiarato ma non ancora in esecuzione**
  (`dbt source freshness`): entra nella catena in M5-T8.
- **La seed dei codici di servizio esclude anche i buoni regalo**
  (`gift_0001_*`). Sono strumenti di pagamento, non merce: contarli come vendita
  significherebbe contare due volte lo stesso fatturato, una alla vendita del
  buono e una quando viene speso. Vale la pena ridiscuterlo se qualcuno cerca il
  fatturato lordo contabile invece di quello di magazzino.
- **`stg_vendite` è una vista.** Ogni interrogazione rilegge il milione di righe
  di `raw`. Va bene finché sopra ci sono i marts materializzati; se un giorno
  qualcuno interrogasse lo staging dai cruscotti, il tempo di risposta lo
  ricorderebbe.

## 7. Come verificarlo

```bash
make up
make ingest
make build TARGET=prod     # oppure: .\make.ps1 build
make test  TARGET=prod
make psql
```

Dentro `psql`, la quadratura si legge a occhio:

```sql
select motivo, righe, valore from staging.stg_esclusioni order by righe desc;
select sum(righe) from staging.stg_esclusioni;   -- 1067371
select count(*) from raw.vendite;                -- 1067371
```

E la deduplica è ripetibile:

```sql
select count(*) from staging.stg_vendite;   -- 1021137, sempre
```
