# M4 — Schema a stella

Chiusa il 20/08/2026 · commit iniziale `d6477b7` · commit finale `d7043ec`

Undici task su undici. Un fatto da 1.021.137 righe e quattro dimensioni, con
chiavi surrogate, membro *Sconosciuto*, fatto incrementale e indici misurati.

## 1. Cosa è stato costruito

Lo schema a stella. `stg_vendite` era una vista piatta: adesso c'è un fatto
materializzato che punta a quattro dimensioni, e le domande si fanno con un
join invece che con una scansione.

Il totale non è cambiato di una riga: 1.021.137 in staging, 1.021.137 nel
fatto, stesso valore complessivo. Nessuna vendita si è persa nei join — che
è la cosa che di solito succede e che nessuno controlla.

## 2. File creati e modificati

| Percorso | Scopo |
| --- | --- |
| `dbt/models/marts/dim_data.sql` | Il calendario generato, con festivi e giorni lavorativi |
| `dbt/models/marts/dim_prodotto.sql` | Anagrafica prodotti con prima/ultima vendita e prezzo medio |
| `dbt/models/marts/dim_cliente.sql` | Anagrafica clienti più il membro *Sconosciuto* |
| `dbt/models/marts/dim_paese.sql` | Paesi normalizzati con la tabella di raccordo |
| `dbt/models/marts/fct_vendite.sql` | Il fatto: incrementale, con gli indici in `post_hook` |
| `dbt/models/marts/_marts.yml` | Descrizione di ogni colonna e 91 test |
| `dbt/seeds/paesi.csv` | 43 valori della sorgente → nome, macro-area, nota |
| `dbt/seeds/festivi_regno_unito.csv` | 25 festività 2009-2011, generate dalle regole |
| `scripts/genera_festivi_uk.py` | Calcola i festivi, Pasqua compresa |
| `scripts/genera_diagramma.py` | Disegna `docs/schema-a-stella.png` e `.svg` |
| `scripts/confronto_indici.py` | Cronometra le query con e senza indici |
| `docs/schema-a-stella.png`, `.svg` | Il diagramma del case study |
| `docs/confronto-indici.md` | Il confronto misurato |

## 3. Decisioni tecniche

### Scelta: i festivi si calcolano, non si copiano
**Alternativa scartata:** scrivere a mano le date del 2009-2011.
**Perché:** l'elenco ufficiale di gov.uk parte dal 2019 e non copre il periodo
dei dati. Le regole però sono pubbliche: Pasqua con l'algoritmo gregoriano,
primo e ultimo lunedì per le feste di maggio e agosto, spostamento al primo
giorno feriale libero per quelle a data fissa. Scriverle a memoria è il modo
più rapido per sbagliare di un giorno e non accorgersene mai. L'unica voce
scritta a mano è il 29 aprile 2011, il matrimonio reale, perché non discende
da nessuna regola.

### Scelta: il join con la tabella di raccordo dei paesi è esterno
**Alternativa scartata:** join interno, che è la cosa naturale.
**Perché:** se domani comparisse un paese non ancora mappato, un join interno
lo farebbe sparire dalla dimensione **e con lui tutte le sue vendite**. È il
modo più silenzioso di perdere fatturato. Con il join esterno il paese entra
comunque, con il nome della sorgente e macro-area «Non attribuito», e la
colonna `da_mappare` diventa vera. Un test dedicato pretende che resti falsa
ovunque: il problema si vede come test rosso, non come numero sbagliato.

### Scelta: `delete+insert` sul giorno, non append
**Alternativa scartata:** aggiungere in coda le righe nuove.
**Perché:** l'append si fida che nessun giorno venga mai ricaricato. Basta un
caricamento ripetuto e le righe si duplicano. Con `delete+insert` su
`data_key`, i giorni che rientrano nella finestra vengono cancellati e
riscritti: rilanciare non duplica, ed è la stessa proprietà che l'ingestione
si è presa in M2-T8.

Il filtro riparte **dall'ultimo giorno già presente**, non dal successivo:
quel giorno potrebbe essere stato caricato a metà.

### Scelta: la chiave delle dimensioni nasce da un ordinamento stabile
**Perché:** `row_number() over (order by codice)` assegna le stesse chiavi a
ogni ricostruzione. Se dipendesse dall'ordine di lettura, ricostruire una
dimensione cambierebbe le chiavi sotto un fatto incrementale che continua a
puntare alle vecchie — e i prodotti si mescolerebbero fra loro senza che
nessun test se ne accorga.

### Scelta: il diagramma si genera da uno script
**Alternativa scartata:** disegnarlo in uno strumento grafico.
**Perché:** un'immagine disegnata a mano invecchia in silenzio, e nel case
study finisce per raccontare uno schema che non esiste più. I conteggi che
compaiono nel diagramma sono letti dal database al momento della generazione,
quindi l'immagine dice quanto c'è davvero.

## 4. Numeri misurati

### Le tabelle

| Tabella | Righe | Nota |
| --- | ---: | --- |
| `dim_data` | 739 | 01/12/2009 → 09/12/2011, senza salti. 17 giorni festivi |
| `dim_prodotto` | 4.909 | |
| `dim_cliente` | 5.876 | 5.875 clienti più il membro *Sconosciuto* |
| `dim_paese` | 43 | zero paesi non mappati |
| `fct_vendite` | **1.021.137** | come `stg_vendite`: nessuna riga persa nei join |

`fct_vendite` pesa **126 MB** compresi i 28 MB di indici.

Chiavi nulle nel fatto: **zero**. Righe orfane rispetto alle dimensioni:
**zero**. Righe che puntano allo *Sconosciuto*: **226.979**, il 22,2 %.

### Il fatto incrementale

| | Righe elaborate | Totale in tabella |
| --- | ---: | ---: |
| Prima esecuzione (costruzione) | 1.021.137 | 1.021.137 |
| Seconda esecuzione (incrementale) | **1.616** | 1.021.137 |

La seconda esecuzione ha toccato solo l'ultimo giorno, e il totale è rimasto
identico — che è esattamente il criterio di M4-T6.

### Gli indici

| Interrogazione | Senza indici | Con indici | Differenza |
| --- | ---: | ---: | ---: |
| Fatturato per mese, tutti i paesi | 0,197 s | 0,136 s | 1,4 volte |
| Fatturato per mese, solo l'Italia | 0,045 s | 0,003 s | **17 volte** |

Due interrogazioni di proposito. L'aggregazione completa deve leggere tutte le
righe comunque, e il database sceglie la scansione sequenziale: gli indici lì
non servono, e dirlo è più onesto che nasconderlo. L'interrogazione selettiva
tocca millecinquecento righe su un milione, ed è il caso dei filtri dei
cruscotti — cioè quello che succede davvero quando qualcuno usa la dashboard.

Il dettaglio, con i piani di esecuzione, è in
[`docs/confronto-indici.md`](../confronto-indici.md).

### I due target

| Target | Schema | Righe nel fatto | `dbt build` |
| --- | --- | ---: | ---: |
| `prod` | `marts` | 1.021.137 | 40 s |
| `dev` | `marts_dev` | 204.415 | 28 s |

Adesso che i marts sono tabelle la differenza si vede: in M3, con il solo
staging fatto di viste, erano 26 s contro 20 s.

### I test

`dbt build` esegue **102 nodi**: 3 seed, 8 modelli, **91 test**. Tutti verdi.

Fra questi ci sono già i quattro `relationships` del fatto verso le dimensioni
che il backlog colloca in M5-T3: esistendo il fatto, aspettare una milestone
per verificare che non abbia righe orfane non aveva senso.

### I cinque indicatori, in anteprima

Calcolati sul fatto appena costruito. Diventeranno domande salvate in M7-T3.

| Indicatore | Valore |
| --- | ---: |
| Fatturato netto | £ 18.927.523 |
| Fatturato lordo | £ 19.642.326 |
| Valore dei resi | £ 714.802 |
| Ordini | 39.516 |
| Scontrino medio | £ 478,98 |
| Tasso di reso (sul valore) | 3,64 % |
| Clienti attivi (senza *Sconosciuto*) | 5.875 |

## 5. Problemi incontrati

**Il diagramma usciva con il testo sovrapposto.** L'altezza dei riquadri era
scritta a mano, e le tabelle con più colonne facevano finire il sottotitolo
sopra l'ultima riga. Riscritto in modo che l'altezza si calcoli dal numero di
colonne: adesso aggiungerne una sposta il bordo invece di rompere il disegno.

**Le etichette del Natale 2011 erano invertite.** Le date erano giuste, i nomi
no: il 26 dicembre 2011 era lunedì — quindi Santo Stefano vero — e il Natale,
caduto di domenica, slittava al 27. Lo script spostava le feste in un
passaggio solo, e il Natale si prendeva il 26. Corretto con due passaggi:
prima si fissano le feste che cadono già in giorno feriale, poi si spostano
le altre.

**Una descrizione YAML con i due punti ha bloccato tutto il progetto dbt.**
`description: Come mostrarlo in un grafico: il codice…` — il parser ha letto i
due punti come una mappa e si è fermato con un errore che parlava di sintassi
alla riga 119, senza dire che il problema erano i due punti. Basta virgolettare.

**Un numero sbagliato era finito nella relazione di M3.** Il conteggio del
target `dev` (204.414) era stato misurato *prima* della correzione del
determinismo della deduplica; il valore giusto è 204.415. Corretto nel
documento. È il rischio dei numeri annotati: vanno rimisurati quando cambia la
logica che li produce, non ricopiati.

**Windows blocca anche `dot`**, cioè Graphviz, che non è installato: il
pacchetto Python c'è ma senza il binario non disegna niente. Il diagramma si
fa con matplotlib, che è una dipendenza di sviluppo in più ma non chiede
nulla al sistema operativo.

## 6. Cosa resta aperto

- **La macro `limite_periodo` filtra sul fatto in `dev` solo di riflesso.**
  Il fatto legge `stg_vendite`, che è già tagliato: va bene, ma se un domani
  qualcuno leggesse direttamente da `raw` in un modello marts, il taglio non
  si applicherebbe.
- **Le dimensioni si ricostruiscono da zero a ogni esecuzione.** Su queste
  dimensioni (poche migliaia di righe) è la scelta giusta; su un'anagrafica da
  milioni di righe servirebbe altro.
- **Il test di quadratura fra `raw` e `fct_vendite` non c'è ancora.** È
  M5-T7, ed è il test che dà senso a `stg_esclusioni`.
- **Nessuna riga del fatto è verificata contro il valore totale di `raw`**:
  oggi il controllo è manuale (l'ho fatto: coincide), in M5 diventa un test.
- **`dim_prodotto` non ha un membro *Sconosciuto*.** Non serve: ogni riga di
  vendita ha un codice prodotto. Se un giorno servisse, la strada è quella di
  `dim_cliente`.

## 7. Come verificarlo

```bash
make up
make ingest
make build TARGET=prod
```

Poi, in `psql`:

```sql
-- il fatto non perde righe rispetto allo staging
select count(*) from marts.fct_vendite;      -- 1021137
select count(*) from staging.stg_vendite;    -- 1021137

-- nessuna chiave nulla, nessun paese non mappato
select count(*) from marts.fct_vendite
 where data_key is null or prodotto_key is null
    or cliente_key is null or paese_key is null;   -- 0
select count(*) from marts.dim_paese where da_mappare;  -- 0

-- il membro Sconosciuto esiste ed è usato
select count(*) from marts.fct_vendite where cliente_key = -1;  -- 226979
```

L'incrementale si prova rilanciando solo il fatto: elabora poche migliaia di
righe e il totale non cambia.

```bash
uv run python scripts/esegui_dbt.py run --select fct_vendite --target prod
```

Il confronto sugli indici e il diagramma si rigenerano con:

```bash
uv run python -m scripts.confronto_indici
uv run python -m scripts.genera_diagramma
```
