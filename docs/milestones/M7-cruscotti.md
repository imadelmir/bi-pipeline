# M7 — Cruscotti

Chiusa il 20/08/2026 · commit iniziale `34aa1c1` · commit finale `e071f08`

Otto task su nove. Tre cruscotti, quindici domande, due filtri — tutti definiti
in file versionati e ricostruibili con un comando. Restano da fare gli
screenshot, che richiedono un browser: vedi la sezione 6.

## 1. Cosa è stato costruito

Metabase in `docker-compose.yml`, collegato allo schema `marts` con un utente
che sa fare `select` e nient'altro. Sopra, tre pagine costruite **via API da
codice versionato**, non a clic.

I cinque indicatori non si calcolano dentro un grafico: due nuovi modelli dbt
li producono già pronti, e le domande salvate scelgono una riga e mostrano una
colonna.

## 2. File creati e modificati

| Percorso | Scopo |
| --- | --- |
| `docker-compose.yml` | Metabase v0.63.14, con il proprio database su PostgreSQL |
| `scripts/utente_metabase.py` | Crea `metabase_lettura` e verifica che non possa scrivere |
| `metabase/api.py` | Cliente minimo dell'API, senza dipendenze in più |
| `metabase/prepara.py` | Amministratore, collegamento del database, sincronizzazione |
| `metabase/domande.py` | Le 15 domande e i 3 cruscotti, con il loro SQL |
| `metabase/configura.py` | Crea o aggiorna domande, cruscotti e filtri |
| `metabase/cruscotti.md` | Cosa contiene ogni pagina e perché |
| `dbt/models/marts/agg_indicatori_giorno.sql` | Misure additive per giorno, paese, prodotto |
| `dbt/models/marts/agg_indicatori_periodo.sql` | I cinque indicatori a cinque livelli |
| `dbt/tests/un_solo_totale.sql` | Il livello «tutto» deve avere una riga sola |
| `dbt/models/marts/dim_cliente.sql` | Il paese del cliente ora è il nome normalizzato |
| `Makefile`, `make.ps1` | `make cruscotti` rifà tutto |

## 3. Decisioni tecniche

### Scelta: i cruscotti si costruiscono da codice, non a clic
**Alternativa scartata:** disegnarli nell'interfaccia, che è il modo previsto.
**Perché:** un cruscotto costruito a mano vive su una macchina sola. Non si
legge in una pull request, non si rifà altrove, e quando qualcuno chiede
«perché questo numero è cambiato» non c'è niente da guardare. Con
`metabase/domande.py` il SQL sta in git, e `make cruscotti` lo riporta
identico su un'istanza vuota.

Il prezzo è reale: l'API di Metabase non è pensata per questo uso, e i payload
delle schede sono verbosi. Vale comunque il costo.

### Scelta: gli indicatori nascono in dbt, a cinque livelli di aggregazione
**Alternativa scartata:** lasciare che Metabase aggreghi il fatto.
**Perché:** due indicatori su cinque non si possono sommare. I **clienti
attivi** sono un conteggio di valori distinti — lo stesso cliente compra a
gennaio e a marzo, e sommare i mesi lo conta due volte. Lo **scontrino medio**
e il **tasso di reso** sono rapporti: la media delle medie non è la media.

`agg_indicatori_periodo` li calcola con `grouping sets` a cinque livelli
(`tutto`, `anno`, `mese`, `paese`, `anno_paese`) in una passata sola. Ogni
domanda filtra il livello che le serve.

### Scelta: i filtri sono obbligatori
**Perché:** avendo cinque livelli nella stessa tabella, una domanda senza
filtro sommerebbe il totale insieme ai suoi addendi e mostrerebbe il doppio
del fatturato. Un test dbt pretende che il livello «tutto» abbia una riga sola.

### Scelta: niente interruttore «con o senza resi»
**Alternativa scartata:** il filtro previsto dal piano.
**Perché:** chi guarda uno schermo non sa in quale posizione si trova
l'interruttore, e un fatturato senza resi somiglia molto a un fatturato con
pochi resi. La scheda «Lordo, resi, netto» mostra le tre misure insieme: si
vede sempre quale si sta guardando, e quanto pesa la differenza. È una
deviazione dal backlog, ed è dichiarata.

### Scelta: Metabase tiene i propri dati in PostgreSQL, non in H2
**Perché:** il file H2 predefinito vive dentro il contenitore. Un
`docker compose down` porterebbe via cruscotti, domande e utenti. Con un
database dedicato sullo stesso PostgreSQL, il lavoro sopravvive — ed è
separato dai dati delle vendite.

## 4. Numeri misurati

### I cinque indicatori, letti da Metabase (anno 2011)

| Indicatore | Valore |
| --- | ---: |
| Fatturato netto | £ 9.014.102,19 |
| Ordini | 18.223 |
| Scontrino medio | £ 494,66 |
| Tasso di reso | 4,82 % |
| Clienti attivi | 4.231 |

Coincidono con la stessa interrogazione lanciata sul database — che è il
criterio di M7-T3.

### I tempi di risposta (M7-T8)

| Pagina | Schede | Tempo totale |
| --- | ---: | ---: |
| 1 — Andamento | 8 | **1,05 s** |
| 2 — Prodotti e clienti | 4 | **2,60 s** |
| 3 — Geografia | 3 | **0,57 s** |

La soglia del backlog è tre secondi: **nessuna pagina la supera, quindi non
sono stati aggiunti modelli pre-aggregati per prestazioni.** I due modelli
`agg_*` esistono per calcolare gli indicatori, non per accelerare le pagine —
la distinzione conta, perché ottimizzare prima di misurare è il modo più
comune di aggiungere complicazione senza guadagno.

La scheda più lenta è «Primi clienti per fatturato», 0,98 s: legge il fatto e
non un aggregato, perché deve unire clienti e fatture.

### Cosa mostrano le pagine

Alcuni numeri che il cruscotto rende evidenti:

- **Il Regno Unito vale l'84,2 % del fatturato del 2011** (e il 91,9 % delle
  righe): con lui nella classifica per paese, tutte le altre barre diventano
  trattini.
- **L'Italia nel 2011: £ 14.642,84, 33 ordini, 12 clienti.** La scheda mostra
  anche il numero di clienti proprio per questo — dodici clienti non fanno una
  tendenza, e la pagina lo dichiara invece di far finta di niente.
- **Metà delle fatture sta sotto i 150 £**, mentre lo scontrino medio è
  £ 494,66: la media descrive un cliente che non esiste, ed è il motivo per cui
  accanto c'è l'istogramma.

### L'utente di sola lettura

| Permesso | Esito |
| --- | --- |
| `USAGE` su `marts` | ✅ concesso |
| `SELECT` su `marts.fct_vendite` | ✅ concesso |
| `INSERT` su `marts.fct_vendite` | ❌ negato |
| `USAGE` su `raw` | ❌ negato |
| `USAGE` su `staging` | ❌ negato |

Verificato con `has_table_privilege` dallo script stesso, che fallisce se i
permessi non sono quelli attesi.

### Il progetto dbt adesso

**122 nodi**: 3 seed, 10 modelli, 109 test. Tutti verdi.

## 5. Problemi incontrati

**I cinque indicatori uscivano vuoti.** Le domande cercavano la riga del
livello «anno» con `nome_paese is null`, e non la trovavano: dentro i
`grouping sets` avevo scritto `max(nome_paese)`, che restituisce un nome anche
quando i paesi sono tutti insieme — il massimo alfabetico. Quella riga non
parla degli Stati Uniti, parla di tutti, e il nome andava messo a `null`
esplicitamente in base a `grouping()`.

**Il fatturato lordo era nullo per due righe.** Nel dicembre 2009 il Giappone
e la Nigeria hanno **soltanto resi e nessuna vendita**, e `sum() filter`
restituisce `null`. Ma il lordo di chi non ha venduto niente è **zero**, non
«sconosciuto». Il test `not_null` l'ha intercettato prima che finisse in un
grafico.

**Lo stesso paese aveva due nomi nella stessa dashboard.** La pagina della
geografia diceva «Paesi Bassi», quella dei clienti «Netherlands»:
`dim_cliente.paese_principale` conservava il valore della sorgente. Ora la
dimensione passa dalla seed di raccordo. Non è un dettaglio estetico: due nomi
per la stessa cosa fanno dubitare di tutto il resto.

**Il tag dell'immagine Metabase che avevo scritto non esisteva.** `v0.56.6` era
inventato: l'ho verificato sul registro delle immagini e sostituito con
`v0.63.14`, che esiste davvero. È lo stesso errore delle action di GitHub in
M1 — un tag va verificato, non ricordato.

**Metabase risponde «ok» prima di essere pronto.** Il primo `docker compose up
--wait` è andato in timeout dopo dieci minuti: l'istanza stava ancora migrando
il proprio database e l'health check restituiva 503. Non è un errore, è il
tempo che ci mette; l'attesa è passata da `--wait` a un ciclo che guarda lo
stato del contenitore.

## 6. Cosa resta aperto

- **Gli screenshot dei tre cruscotti (M7-T9) non sono stati fatti.** Richiedono
  un browser che mostri le pagine, e in questa sessione il pannello non è
  visibile. I cruscotti funzionano — ogni scheda è stata eseguita via API e
  restituisce dati — ma le immagini per il case study vanno catturate a mano.
  I link sono nella sezione 7.
- **I link pubblici sono attivi.** Servivano a guardare le pagine senza
  autenticarsi; su un'istanza locale non è un problema, ma prima di esporre
  Metabase fuori dalla macchina vanno spenti.
- **Il filtro sui resi non è un interruttore** (vedi le decisioni). Se lo si
  vuole come da backlog, la strada è una colonna in più nei modelli aggregati.
- **Le domande non hanno test.** Se qualcuno cambia un modello e rompe una
  domanda, se ne accorge guardando la pagina. Un controllo automatico che
  esegua tutte le domande e verifichi che restituiscano righe sarebbe una
  quindicina di righe di codice: vale la pena, ma non rientra in M7.
- **La scheda Italia dipende dall'anno scelto.** Con il 2009 mostra pochi
  ordini e i numeri diventano rumore. Il testo della pagina lo dice, la scheda
  no.

## 7. Come verificarlo

```bash
make up          # PostgreSQL e Metabase (la prima volta ~2 minuti)
make ingest
make build TARGET=prod
make cruscotti   # utente di lettura, istanza, domande, cruscotti
```

Poi si aprono le tre pagine:

- <http://localhost:3000/dashboard/2> — Andamento
- <http://localhost:3000/dashboard/3> — Prodotti e clienti
- <http://localhost:3000/dashboard/4> — Geografia

Le credenziali dell'amministratore sono in `.env`
(`METABASE_ADMIN_EMAIL`, `METABASE_ADMIN_PASSWORD`).

Per verificare che i numeri del cruscotto siano quelli del database:

```sql
select valore_netto, ordini, scontrino_medio, tasso_reso_percentuale, clienti_attivi
from marts.agg_indicatori_periodo
where livello = 'anno' and anno = 2011 and nome_paese is null;
```

Per verificare che Metabase non possa scrivere:

```bash
uv run python -m scripts.utente_metabase   # stampa i permessi e fallisce se sono sbagliati
```
