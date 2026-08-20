# M8 — Pubblicazione

Chiusa il 20/08/2026 · commit iniziale `e071f08` · commit finale `fb31577`

Nove task su nove. Il repository è pubblico e documentato, il case study è nel
portfolio in due lingue, e la prova su macchina pulita ha trovato quattro
difetti che ora non ci sono più.

## 1. Cosa è stato costruito

Un README che porta chi non conosce il progetto dal `git clone` ai cruscotti
senza dover indovinare niente, e un case study bilingue nel portfolio con
architettura, decisioni, metriche misurate e quattro immagini.

In mezzo, la parte che è servita davvero: **clonare il repository in una
cartella nuova e seguire il README alla lettera**, che ha rivelato quattro cose
rotte che nessun test avrebbe intercettato.

## 2. File creati e modificati

| Percorso | Scopo |
| --- | --- |
| `README.md` | Riscritto: numeri in cima, diagramma, cruscotti, avvio, limiti |
| `docker/init/01-database-metabase.sh` | Crea il database di appoggio di Metabase |
| `docker-compose.yml` | Volumi senza nome fisso, `start_period` a 300 s |
| `.env.example` | Password d'esempio che Metabase accetta davvero |
| `metabase/prepara.py` | Messaggio comprensibile se la password viene rifiutata |
| `metabase/configura.py` | Archivia le domande che non esistono più nel codice |
| `docs/screenshot/*.png` | Le tre pagine, catturate dopo le correzioni |
| `docs/decisioni.md` | D19: la sorte della demo online |
| `portfolio: it/bi-pipeline.mdx`, `en/bi-pipeline.mdx` | Il case study |
| `portfolio: public/images/projects/bi-pipeline/` | Copertina, tre cruscotti, diagramma |

## 3. Decisioni tecniche

### Scelta: nessuna demo online (D19)
**Alternative scartate:** pubblicare il database, o una sua fetta ridotta.
**Perché:** il database pesa 491 MB — 272 lo schema `raw`, 190 i `marts` — e
non sta nei piani gratuiti che offrano anche un motore di interrogazione sempre
acceso. Una fetta ridotta starebbe ovunque, ma mostrerebbe numeri diversi da
quelli del case study: chi legge «1.067.371 righe» e ne trova duecentomila si
fida meno di tutto il resto. Il README dichiara la scelta e il peso, invece di
tacere sull'assenza.

### Scelta: la copertina è il cruscotto, non il diagramma
**Perché:** in una vetrina di progetti l'immagine deve dire in un secondo cosa
si è costruito. Il diagramma dell'architettura racconta *come*, ed è la seconda
cosa che si guarda — infatti sta fra gli screenshot.

### Scelta: il case study dichiara i limiti invece di aggirarli
**Perché:** il margine assente, la demo che non c'è, il font di Metabase che
l'edizione open source non lascia cambiare. Ognuna di queste righe è una
domanda in meno in un colloquio, e una promessa in meno da mantenere.

## 4. Numeri misurati

### La prova su macchina pulita

Clone in una cartella nuova, `.env` copiato da `.env.example` senza modifiche,
e il README seguito riga per riga:

| Passo | Tempo |
| --- | ---: |
| `git clone` + `.env` + `uv sync` | **5 s** |
| `make up` (PostgreSQL e Metabase da zero) | **59 s** |
| Scaricamento, checksum e conversione | **100 s** |
| Caricamento con `COPY` | **9,1 s** |
| `dbt seed` + `dbt build` (122 nodi) | **63 s** |
| `make cruscotti` su istanza vuota | **11 s** |
| **Totale** | **circa 4 minuti** |

I conteggi finali: 1.067.371 in `raw`, 1.021.137 in `staging`, 1.021.137 nel
fatto. Identici a questa macchina e al runner della CI.

### Il portfolio

`npm run check` verde — TypeScript, ESLint, 124 test unitari — e
`npm run build` genera 30 pagine statiche in 27 secondi, comprese
`/it/projects/bi-pipeline` e `/en/projects/bi-pipeline`.

### Il progetto, alla fine

| | |
| --- | ---: |
| Milestone chiuse | 8 su 8 |
| Task | 78 |
| Commit | oltre 30, uno per gruppo di task |
| Modelli dbt | 10 |
| Test dbt | 109 |
| Decisioni documentate | 19 |
| Relazioni di milestone | 8 |

## 5. Problemi incontrati

La prova su macchina pulita ha trovato **quattro difetti**, e nessuno di questi
sarebbe emerso continuando a lavorare sulla macchina di sviluppo.

**Il database di appoggio di Metabase non lo creava nessuno.** Durante lo
sviluppo l'avevo creato a mano con un comando che non stava in nessun file. Su
un volume vuoto Metabase muore con `connection checkout timed out`, che non
dice niente a chi non conosce già il problema. Risolto con uno script in
`docker-entrypoint-initdb.d`, che PostgreSQL esegue alla prima inizializzazione.

**I volumi Docker avevano un nome fisso.** Due copie del repository sullo
stesso computer finivano sullo stesso database: il clone nuovo trovava quello
vecchio e falliva l'autenticazione con la password di `.env.example`. Tolto il
nome fisso, Compose antepone il nome della cartella.

**`make up` usciva in errore.** Metabase impiega due o tre minuti al primo
avvio e il `start_period` di 120 secondi non bastava: `docker compose --wait` si
arrendeva mentre il servizio stava ancora partendo.

**Metabase rifiutava la password di esempio.** `cambiami-almeno-otto-caratteri`
viene considerata «troppo comune», e la risposta dell'API è un JSON che non lo
dice in modo leggibile. Cambiato il valore e aggiunto un messaggio chiaro.

**E un falso positivo istruttivo:** il primo clone, fatto in una cartella
temporanea, non riusciva a importare un modulo di dbt. Il file c'era: il
percorso arrivava a 252 caratteri e sfiorava il limite dei 260 di Windows.
Rifatta la prova in una cartella con percorso corto, tutto funziona. Vale la
pena saperlo prima di dare la colpa al progetto.

**Gli screenshot hanno trovato quello che l'API non poteva.** Guardando le
pagine vere sono emersi tre difetti invisibili da un controllo automatico: una
voce «Altro» che era la seconda barra più lunga di una classifica, una barra
impilata illeggibile, e due schede che nascondevano righe dietro una barra di
scorrimento. Verificare che una query restituisca dati non è verificare che il
grafico si legga.

## 6. Cosa resta aperto

- **Il video breve della pipeline** (parte di M8-T3) non è stato registrato.
  Il README e il case study funzionano senza; se lo si vuole, il momento buono
  è un `make flow` che stampa i tempi di ogni passo.
- **Il case study è nel portfolio ma non ancora pubblicato**: i file sono
  scritti e la build passa, il push al repository del portfolio è una decisione
  dell'autore.
- **`dbt/target/` e i cataloghi generati non sono versionati.** La
  documentazione dbt con il lineage si guarda in locale con `make docs`; per
  pubblicarla servirebbe una pagina statica, che non è fra i task.
- **Nessun monitoraggio dei tempi.** Se un modello diventasse dieci volte più
  lento, la CI resterebbe verde. I tempi si misurano a mano, e sono nelle
  relazioni.
- **L'istanza Metabase vive solo in locale.** I cruscotti si ricostruiscono con
  un comando, ma nessuno li vede senza far girare il progetto.

## 7. Come verificarlo

La verifica di questa milestone è la milestone stessa: clonare in una cartella
nuova — con un percorso breve, su Windows — e seguire il README.

```bash
git clone https://github.com/imadelmir/bi-pipeline.git
cd bi-pipeline
cp .env.example .env
cp dbt/profiles.yml.example dbt/profiles.yml
uv sync
make up
make ingest
make build TARGET=prod
make cruscotti
```

In quattro minuti Metabase è su <http://localhost:3000> con le tre pagine, e i
conteggi sono quelli scritti nel README.

Per il portfolio:

```bash
cd "Portfolio Imad El mir/portfolio"
npm run check
npm run build
```
