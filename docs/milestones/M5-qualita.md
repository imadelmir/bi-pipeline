# M5 — Qualità

Chiusa il 20/08/2026 · commit iniziale `00cb1ba` · commit finale `3887597`

Undici task su undici. 94 test verdi, la quadratura torna, e la stessa pipeline
su una macchina che non ha mai visto questo progetto produce gli stessi numeri.

## 1. Cosa è stato costruito

I test che intercettano i modi in cui questi dati possono mentire. Quelli
generici — `unique`, `not_null`, `relationships`, `accepted_values` — erano
già stati scritti insieme ai modelli che proteggono; qui sono arrivati i tre
**test singolari**, cioè quelli che nessun generatore può indovinare al posto
tuo.

E soprattutto è arrivata la **quadratura dei totali**: l'unico controllo che si
accorge se delle righe spariscono lungo la strada. Tutti gli altri verificano
che ciò che è arrivato sia sano; questo verifica che sia arrivato tutto.

Poi la CI ha smesso di controllare solo il codice: adesso alza un PostgreSQL,
scarica la sorgente vera, carica il milione di righe ed esegue `dbt build` con
tutti i test. Una pull request che rompe un test è rossa.

## 2. File creati e modificati

| Percorso | Scopo |
| --- | --- |
| `dbt/tests/prezzo_positivo.sql` | Nessuna vendita a prezzo zero o negativo |
| `dbt/tests/coerenza_resi.sql` | Il segno della quantità concorda con `is_reso` |
| `dbt/tests/quadratura_totali.sql` | Righe in `raw` = righe nel fatto + esclusioni |
| `dbt/models/staging/_sources.yml` | Freschezza spostata sulla tabella `vendite` |
| `dbt/models/marts/fct_vendite.sql` | Dipendenza esplicita da `dim_data` |
| `.github/workflows/ci.yml` | Nuovo lavoro «dati»: PostgreSQL di servizio e `dbt build` |

## 3. Decisioni tecniche

### Scelta: la quadratura verifica due cose, e la seconda solo su `prod`
**Alternativa scartata:** un confronto secco fra `raw` e `fct_vendite`.
**Perché:** il target `dev` taglia il periodo a tre mesi mentre `raw` contiene
tutto. Un confronto secco sarebbe rosso per costruzione in sviluppo, cioè
inutile — e un test che si sa già rosso viene ignorato, poi disattivato, poi
cancellato. Il test verifica sempre che il fatto non perda righe rispetto a
staging, e in più, su `prod`, che la somma delle esclusioni torni con `raw`.

### Scelta: il test dice cosa non torna, non solo che non torna
**Perché:** restituisce `controllo`, `atteso`, `trovato` e `differenza`. Un
test che dice soltanto «FAIL» costringe a rifare a mano l'indagine che il test
aveva già fatto. Con `--store-failures` la riga resta in tabella e si legge.

### Scelta: `fct_vendite` dichiara la dipendenza da `dim_data` a mano
**Perché:** il fatto **non legge** il calendario — la chiave del giorno la
calcola da `data_ora`, evitando un join su un milione di righe per ottenere un
numero che si ricava dalla data. Senza `-- depends_on:`, però, dbt non sapeva
che le due tabelle fossero legate: il grafo mostrava una stella con un braccio
staccato, e nulla garantiva che il calendario esistesse prima del test
`relationships` che lo confronta.

### Scelta: la CI scarica e carica i dati veri
**Alternativa scartata:** un campione ridotto, o dati finti.
**Perché:** i dati finti non hanno i 34.153 duplicati, le 3.457 rettifiche a
quantità negativa e la fattura di reso con quantità positiva — cioè
esattamente le cose che i test devono intercettare. Con la sorgente vera, il
lavoro dura tre minuti e mezzo e dimostra qualcosa: che la pipeline funziona
su una macchina che non ha mai visto questo progetto.

La sorgente scaricata sta in cache, con una chiave che dipende dal modulo che
contiene il checksum atteso: se cambia il file, cambia la chiave.

## 4. Numeri misurati

### I test

| | |
| --- | ---: |
| Test totali | **94** |
| di cui generici | 91 |
| di cui singolari | 3 |
| Nodi eseguiti da `dbt build` | 105 (3 seed, 8 modelli, 94 test) |
| Esito su `prod` | tutti verdi |
| Esito su `dev` | tutti verdi |
| Colonne senza descrizione nel catalogo | **0** |

Cosa protegge ciascuno:

| Test | Su cosa | Cosa impedisce |
| --- | --- | --- |
| `unique` (7) | Chiavi delle dimensioni, codici, seed | Chiavi doppie che moltiplicano il fatturato nei join |
| `not_null` (56) | Chiavi del fatto e colonne obbligatorie | Righe che spariscono da ogni join interno |
| `relationships` (4) | Fatto → le quattro dimensioni | Vendite di prodotti che non esistono in anagrafica |
| `accepted_values` (7) | `is_reso`, `motivo_esclusione`, `da_mappare` | Che un booleano diventi un terzo stato, o che compaia un motivo di esclusione non dichiarato |
| `prezzo_positivo` | `stg_vendite` | Che le rettifiche a prezzo zero rientrino di nascosto |
| `coerenza_resi` | `fct_vendite` | Che un reso sommi al fatturato invece di sottrarre |
| `quadratura_totali` | `raw` vs `marts` | Che delle righe spariscano senza che nessuno lo sappia |

### La prova che il test funziona

Un test che non è mai stato visto fallire non è un test, è una speranza.

Ho cancellato a mano un giorno dal fatto — **1.271 righe** — e rieseguito la
quadratura:

```
FAIL 1 quadratura_totali
il fatto perde righe rispetto a staging | atteso 1.021.137 | trovato 1.019.866 | differenza 1.271
```

Poi `--full-refresh` e il test è tornato verde. Il test non dice soltanto che
qualcosa non va: dice quante righe mancano e da quale confronto.

### La freschezza

`dbt source freshness` su `raw.vendite`: **PASS**. Soglie: avviso a 24 ore,
errore a 48. Su dati storici il controllo dirà sempre la stessa cosa, ma il
meccanismo è al suo posto per il giorno che il caricamento diventasse
periodico.

### Il lineage

```
raw.vendite ─► stg_vendite_classificate ─┬─► stg_esclusioni
                                          └─► stg_vendite ─┬─► dim_data
                                                           ├─► dim_prodotto
                                                           ├─► dim_cliente
                                                           ├─► dim_paese
                                                           └─► fct_vendite
```

Il grafo non è disegnato a mano: nasce dai `ref()` dentro i modelli, e si
guarda con `make docs`.

### La CI, e la riproducibilità

| Lavoro | Durata |
| --- | ---: |
| Formato, lint e tipi | **30 s** |
| Pipeline e test dbt su PostgreSQL | **199 s** |

Il secondo lavoro parte da un runner vuoto: alza PostgreSQL 16.14, scarica i
43,5 MB da UCI, verifica il checksum, converte, carica con `COPY`, costruisce
tutti i modelli ed esegue i 94 test.

I numeri che stampa alla fine:

```
raw.vendite                 1.067.371 righe
staging.stg_vendite         1.021.137 righe
marts.fct_vendite           1.021.137 righe
```

**Sono gli stessi identici numeri misurati su questa macchina.** È la prova che
la pipeline non dipende da niente che sia rimasto attaccato al computer di chi
l'ha scritta.

## 5. Problemi incontrati

**La freschezza faceva fallire il registro dei caricamenti.** `loaded_at_field`
era dichiarato a livello di sorgente, quindi si applicava a tutte le sue
tabelle — e `raw.registro_caricamenti` non ha una colonna `caricato_il`. Il
risultato era un errore di database invece di un messaggio comprensibile.
Spostato sulla tabella `vendite`, che è l'unica a cui la freschezza serve.

**La stella aveva un braccio staccato.** Nel grafo delle dipendenze
`fct_vendite` risultava collegato a tre dimensioni su quattro: `dim_data` non
compariva, perché il fatto la chiave del giorno se la calcola. Funzionava, ma
il lineage raccontava una cosa falsa — e in un case study il lineage è
un'immagine che qualcuno guarda. Risolto con `-- depends_on:`.

**dbt non conserva l'esito dei test.** Dopo il primo fallimento volevo vedere
la riga incriminata e la tabella non esisteva: serve `--store-failures`, che
la materializza in uno schema di servizio. Vale la pena saperlo prima di
trovarsi davanti un `FAIL 1` senza sapere cosa fosse.

**Il riepilogo della CI stampava punti interrogativi.** Su Windows lo sapevamo
già (i flussi rediretti usano cp1252), ma la stessa protezione serviva anche
in un `python -c` dentro il workflow: senza `PYTHONIOENCODING`, un carattere
accentato interrompe lo script a metà.

## 6. Cosa resta aperto

- **La CI dipende dalla rete di UCI.** Con la cache il file si scarica una
  volta sola, ma la prima esecuzione dopo un cambio di checksum bussa a un
  server che non controlliamo. Se un giorno diventasse un problema, la strada
  è ospitare una copia della sorgente.
- **`--store-failures` non è attivo di default.** Va bene così: materializzare
  gli scarti di 94 test a ogni esecuzione riempirebbe il database di tabelle
  che nessuno guarda. Si accende quando serve.
- **Nessun test sulle prestazioni.** Se un domani un modello diventasse dieci
  volte più lento, la CI resterebbe verde. È accettabile finché i tempi si
  misurano a mano nelle relazioni.
- **La quadratura confronta i conteggi, non i valori.** Righe uguali con
  importi diversi passerebbero. Il totale del fatturato coincide (verificato a
  mano in M4), ma non c'è un test che lo pretenda.

## 7. Come verificarlo

```bash
make up
make ingest
make build TARGET=prod     # 105 nodi: 3 seed, 8 modelli, 94 test
make test  TARGET=prod     # solo i 94 test
make docs                  # documentazione e lineage nel browser
```

Per vedere la quadratura fallire davvero, e poi tornare a posto:

```sql
delete from marts.fct_vendite where data_key = 20110315;   -- 1.271 righe
```

```bash
uv run python scripts/esegui_dbt.py test --select quadratura_totali --target prod --store-failures
uv run python scripts/esegui_dbt.py run --select fct_vendite --target prod --full-refresh
uv run python scripts/esegui_dbt.py test --target prod
```

La freschezza:

```bash
uv run python scripts/esegui_dbt.py source freshness --target prod
```
