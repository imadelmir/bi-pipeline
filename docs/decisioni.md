# Decisioni

Registro delle decisioni tecniche prese durante il progetto. Una voce per
decisione: cosa è stato scelto, cosa è stato scartato, perché.

Le relazioni di milestone in `docs/milestones/` raccontano *cosa è stato
costruito*. Questo file raccoglie *perché è fatto così*, anche quando la
decisione attraversa più milestone.

---

## D1 — La sorgente e la sua licenza

**Milestone:** M1-T1 · **Verificata il:** 19/08/2026 · **Bloccante**

Sorgente scelta: **Online Retail II**, UCI Machine Learning Repository.

| Campo | Valore letto sulla scheda UCI |
|---|---|
| Licenza | **Creative Commons Attribution 4.0 International (CC BY 4.0)** |
| Testo della licenza | «This allows for the sharing and adaptation of the datasets for any purpose, provided that the appropriate credit is given.» |
| DOI | `10.24432/C5CG6D` |
| Righe dichiarate | 1.067.371 |
| File | `online_retail_II.xlsx` — 43,5 MB |
| Data di donazione | 20/09/2019 |
| Scheda | <https://archive.ics.uci.edu/dataset/502/online+retail+ii> |

**Citazione completa, da riportare nel README e nel piede dei cruscotti:**

> Chen, D. (2012). *Online Retail II* [Dataset]. UCI Machine Learning
> Repository. <https://doi.org/10.24432/C5CG6D>

**Perché è il primo task di tutti.** CC BY consente il riuso *a condizione* di
citare la fonte. Se la licenza fosse risultata diversa — non commerciale, o
senza opere derivate — il progetto non sarebbe stato pubblicabile, e scoprirlo
dopo aver scritto la pipeline avrebbe significato buttare il lavoro. Costa due
minuti verificarlo prima.

**Alternative scartate** (dal piano, per completezza): Rossmann — solo incasso
giornaliero per negozio, niente prodotto né cliente, lo schema a stella non sta
in piedi; Instacart — 32 milioni di righe senza prezzi, il fatturato non si
calcola; H&M — prezzi scalati di un fattore non dichiarato e nessun numero di
scontrino; Olist — buono, ma è il dataset più usato al mondo per esercitarsi;
dunnhumby — il più ricco, resta come aggiornamento futuro.

**Conseguenza operativa:** il file sorgente **non entra nel repository**. 43 MB
in git restano per sempre, anche dopo una cancellazione. Si scarica con uno
script che ne verifica lo SHA-256 (M2-T1).

---

## D2 — L'hook pre-commit è uno script versionato, non il framework `pre-commit`

**Milestone:** M1-T5

`ruff` e `mypy` girano prima di ogni commit tramite `.githooks/pre-commit`, uno
script eseguito grazie a `git config core.hooksPath .githooks`.

**Alternativa scartata:** il framework `pre-commit` (file
`.pre-commit-config.yaml`).

**Perché:** il framework installa i propri ambienti isolati e vuole le versioni
degli strumenti dichiarate una seconda volta, dentro il suo YAML. Le versioni di
`ruff` e `mypy` sono già bloccate in `pyproject.toml` e installate nell'ambiente
del progetto: duplicarle significa che un giorno divergeranno, e il commit
locale passerà mentre la CI fallisce — o il contrario. Con uno script che invoca
`uv run`, lo strumento che gira in locale è **lo stesso identico** che gira in
CI, e non c'è una seconda lista di versioni da tenere allineata.

Il costo è una riga di configurazione da eseguire dopo il clone
(`git config core.hooksPath .githooks`), documentata nel README.

---

## D3 — Metabase non è in `docker-compose.yml` fin da M1

**Milestone:** M1-T6

`docker-compose.yml` contiene per ora **solo PostgreSQL 16**. Metabase entra in
M7-T1, quando serve davvero.

**Perché:** M1 chiude quando `docker compose up` alza un database funzionante.
Aggiungere subito un servizio che nessuno userà per sei milestone significa
allungare l'avvio, consumare memoria e — soprattutto — non poter dire se un
fallimento dipende dal database o da un contenitore inutile. Il servizio si
aggiunge quando c'è uno schema `marts` da mostrargli.

---

## D4 — Le versioni si fissano ovunque, non solo in `pyproject.toml`

**Milestone:** M1-T4, M1-T6

Fissate al valore esatto: le dipendenze Python (`==`, più `uv.lock`
committato), l'immagine del database (`postgres:16.14`, non `postgres:16`) e
la versione di Python (`>=3.12,<3.13`).

**Alternativa scartata:** intervalli (`>=`) e tag mobili (`postgres:16`).

**Perché:** con un intervallo, due macchine — o la stessa macchina a due mesi di
distanza — installano cose diverse. Il giorno che qualcosa si rompe non si sa se
è colpa del codice o di un aggiornamento arrivato di nascosto, e la prima ora se
ne va a capirlo. Le versioni si alzano di proposito, con un commit che lo dice e
la CI che lo verifica.

Il prezzo è che gli aggiornamenti di sicurezza non arrivano da soli. Su un
progetto di portfolio, con un database che gira in locale, è un prezzo
accettabile — e dichiararlo è meglio che subirlo.

---

## D5 — `make.ps1` accanto al `Makefile`

**Milestone:** M1-T9

I comandi esistono in due file: il `Makefile` e uno script PowerShell che
espone gli stessi nomi.

**Alternativa scartata:** installare GNU Make su Windows e tenere un file solo.

**Perché:** su questa macchina `make` non è installato, e chiedere a chi clona il
repository di installarlo prima ancora di poter alzare un database è un attrito
inutile. Il `Makefile` resta il contratto — è quello citato nel README e nel
mockup — e `make.ps1` è la porta di servizio per Windows.

Il costo è reale: due file da tenere allineati. È accettabile perché ogni
comando è una riga sola, ed è dichiarato in testa a entrambi i file. Se un
giorno i comandi diventassero script veri e propri, la logica passerebbe negli
script e i due file tornerebbero a essere due elenchi di nomi.

---

## D6 — Il checksum atteso è misurato da noi, non pubblicato da UCI

**Milestone:** M2-T1

`ingestion/sources/online_retail.py` confronta lo SHA-256 dell'Excel con un
valore costante nel codice:
`bcbe73b35f5b7babf197fb0cb983a11f5d9ff929078d4aa53d171b1f2df2e980`, misurato al
primo scaricamento del 19/08/2026.

**Cosa garantisce e cosa no.** UCI non pubblica un checksum ufficiale del
dataset. Quel valore quindi non dice «il file è quello che UCI ha voluto
pubblicare»: dice «il file è identico a quello su cui sono stati misurati tutti
i numeri di questo progetto». È una garanzia di riproducibilità, non di
autenticità, e vale la pena non confonderle.

**Perché serve lo stesso.** Uno scaricamento troncato o una sorgente aggiornata
in silenzio produrrebbero numeri diversi senza alcun segnale: il conteggio
righe cambierebbe, la quadratura di M5-T7 fallirebbe, e si perderebbe mezza
giornata a cercare l'errore nei modelli invece che nel file.

**Se un giorno non corrisponde più:** non si aggiorna la costante e via. Si
guarda cosa è cambiato, perché ogni numero scritto nelle relazioni di milestone
si riferisce al file vecchio.

---

## D7 — Il campo vuoto diventa `NULL`, non stringa vuota

**Milestone:** M2-T5

Nel passaggio dal CSV a `raw.vendite`, un campo vuoto entra come `NULL`.

**Alternativa scartata:** caricare `''` e lasciare che sia staging a decidere.

**Perché:** «campo vuoto» nel CSV significa *qui non c'è niente*, ed è
esattamente ciò che `NULL` rappresenta in SQL. Tenere la stringa vuota
costringerebbe ogni modello di staging a scrivere `nullif(colonna, '')` su ogni
colonna, e basta dimenticarlo una volta perché un conteggio di valori mancanti
torni zero mentre i valori mancanti ci sono — 243.007, per la precisione.

Non è una violazione della regola «raw non trasforma»: nessun valore viene
cambiato, corretto o filtrato. Cambia solo il modo di rappresentare un'assenza,
e si sceglie quello che il database capisce.

---

## D8 — Il registro dei caricamenti scrive su una connessione propria

**Milestone:** M2-T7

`ingestion/registry.py` apre una connessione separata, in autocommit, invece di
usare quella del caricamento.

**Alternativa scartata:** scrivere il registro nella stessa transazione dei dati.

**Perché:** il registro deve raccontare anche — soprattutto — i caricamenti che
falliscono. Dentro la stessa transazione, il rollback che annulla i dati
annullerebbe pure la riga che dice «è fallito»: resterebbe una tabella vuota e
nessuna traccia del perché.

Verificato con un CSV malformato: zero righe entrate, e nel registro un record
`fallito` con il messaggio di PostgreSQL. Se il processo viene ucciso di netto,
invece, il record resta `in corso` — ed è giusto così: è la firma di un
processo morto, e ripulirla in automatico significherebbe cancellare l'unica
prova che qualcosa è andato storto.

---

## D9 — I motivi di esclusione hanno una priorità

**Milestone:** M3-T6, M3-T7, M3-T8, M3-T10

Una riga esclusa viene contata su **un solo** motivo, il primo che la coglie:
codice di servizio, poi prezzo non positivo, poi duplicato esatto.

**Alternativa scartata:** contare ogni condizione separatamente.

**Perché:** le condizioni si sovrappongono — un codice di servizio può avere
prezzo zero ed essere anche duplicato. Contandolo tre volte, la somma delle
esclusioni supererebbe le righe escluse e la quadratura di M5-T7 non tornerebbe
mai. Con la priorità ogni riga finisce in una casella sola e la somma torna al
pezzo.

**Conseguenza da ricordare:** i numeri di `stg_esclusioni` non coincidono con
quelli di `docs/profilazione.md`, che contava le condizioni una per una. Non è
un errore: 6.202 righe hanno prezzo zero, ma 6.168 sono escluse *per* il prezzo
— le altre erano già uscite come codici di servizio.

---

## D10 — La deduplica tiene la riga che vale, e lo fa sempre allo stesso modo

**Milestone:** M3-T8

`row_number()` ordina per prezzo decrescente, con descrizione, cliente e file
d'origine come spareggio.

**Alternativa scartata:** ordinare per data di caricamento, che era la prima
versione.

**Perché:** la chiave di deduplica del piano — fattura, prodotto, quantità,
istante — non comprende il prezzo. Dentro un gruppo possono quindi finire righe
con prezzi diversi, tipicamente una a prezzo pieno e una a zero. Con
`order by caricato_il`, identico per tutte le righe della stessa transazione,
la scelta di quale riga tenere la faceva il database: se toccava a quella a
prezzo zero, veniva scartata dal filtro sui prezzi e la gemella valida spariva
come duplicato.

Il conteggio della stessa vista cambiava fra un'esecuzione e l'altra:
1.021.131, poi 1.021.134, poi 1.021.137. Un modello non deterministico mente a
caso, ed è il genere di errore che in un cruscotto non si nota mai.

---

## D11 — `dev` e `prod` scrivono in schemi diversi

**Milestone:** M3-T3

`prod` scrive in `staging` e `marts`; `dev` in `staging_dev` e `marts_dev`.

**Alternativa scartata:** stesso schema per entrambi, come veniva naturale.

**Perché:** con un nome solo, un `dbt build --target dev` riscrive le viste che
Metabase sta leggendo — e le riscrive con un trimestre di dati invece di due
anni. Il cruscotto mostrerebbe numeri sbagliati senza che nessuno abbia toccato
niente, e per giunta nel momento in cui si sta lavorando ad altro.

---

## D12 — I festivi si calcolano dalle regole, non si copiano da un elenco

**Milestone:** M4-T1

`scripts/genera_festivi_uk.py` genera `dbt/seeds/festivi_regno_unito.csv`
applicando le regole di Inghilterra e Galles: Pasqua con l'algoritmo gregoriano
anonimo, primo e ultimo lunedì per le feste di maggio e agosto, spostamento al
primo giorno feriale libero per quelle a data fissa.

**Alternativa scartata:** scrivere a mano le 25 date del 2009-2011.

**Perché:** l'elenco ufficiale pubblicato da gov.uk parte dal 2019 e non copre
il periodo dei dati. Le regole invece sono pubbliche e stabili. Scrivere le
date a memoria significa sbagliarne una e non accorgersene mai: un festivo
sbagliato non rompe niente, cambia solo di poco un confronto fra giorni
lavorativi — il tipo di errore che sopravvive per anni.

L'unica voce scritta a mano è il **29 aprile 2011**, festività straordinaria
per il matrimonio reale: non discende da nessuna regola, e sta nel codice con
il suo commento.

**Trappola trovata:** spostando le feste fisse in un passaggio solo, nel 2011
il Natale si prendeva il 26 dicembre (lunedì) e Santo Stefano il 27. Le date
erano giuste ma i nomi scambiati. Servono due passaggi: prima si fissano le
feste che cadono già in giorno feriale, poi si spostano quelle di weekend.

---

## D13 — Il raccordo dei paesi si unisce con un join esterno

**Milestone:** M4-T4

`dim_paese` nasce dai paesi presenti nei dati, uniti in `left join` alla seed
`paesi.csv`.

**Alternativa scartata:** join interno, che sarebbe la cosa naturale visto che
la seed copre tutti i 43 valori esistenti.

**Perché:** copre tutti i valori *oggi*. Il giorno che nella sorgente comparisse
un paese nuovo, un join interno lo farebbe sparire dalla dimensione **e con lui
tutte le sue vendite dal fatto**: il fatturato calerebbe senza che nessun test
fallisca. Con il join esterno il paese entra comunque, con macro-area «Non
attribuito», e la colonna `da_mappare` diventa vera. Un test pretende che resti
falsa: il problema si presenta come test rosso, non come numero sbagliato.

---

## D14 — Il fatto è incrementale con `delete+insert` sul giorno

**Milestone:** M4-T6

`fct_vendite` è `materialized='incremental'`, `unique_key='data_key'`,
`incremental_strategy='delete+insert'`, e riparte dall'ultimo giorno già
presente in tabella.

**Alternativa scartata:** aggiungere in coda le sole righe più recenti.

**Perché:** l'append si fida che nessun giorno venga mai ricaricato, e basta un
caricamento ripetuto perché le righe si duplichino — lo stesso problema che
l'ingestione ha risolto in M2-T8, ripresentato uno strato più in alto. Con
`delete+insert` i giorni che rientrano nella finestra vengono cancellati e
riscritti.

Riparte **dall'**ultimo giorno e non dal successivo perché quel giorno potrebbe
essere stato caricato a metà.

**Prezzo dichiarato:** se cambia la logica dei modelli a monte, il fatto non se
ne accorge — i giorni vecchi restano come sono. Dopo una modifica a
`stg_vendite` serve `--full-refresh`.

---

## D15 — La quadratura verifica due cose, e la seconda solo su `prod`

**Milestone:** M5-T7 · **Bloccante**

`tests/quadratura_totali.sql` controlla che il fatto non perda righe rispetto a
staging (su entrambi i target) e, **solo su `prod`**, che la somma di
`stg_esclusioni` corrisponda alle righe di `raw`.

**Alternativa scartata:** un confronto secco fra `raw` e `fct_vendite`.

**Perché:** il target `dev` taglia il periodo a tre mesi mentre `raw` contiene
tutto. Un confronto secco sarebbe rosso per costruzione in sviluppo — e un test
che si sa già rosso viene prima ignorato, poi disattivato, poi cancellato.

Il test restituisce `controllo`, `atteso`, `trovato` e `differenza`, non un
semplice conteggio di righe: un test che dice soltanto «FAIL» costringe a rifare
a mano l'indagine che aveva già fatto.

**Verificato che fallisce:** cancellate 1.271 righe dal fatto, il test è
diventato rosso indicando atteso 1.021.137, trovato 1.019.866, differenza 1.271.
Un test mai visto fallire non è un test, è una speranza.

---

## D16 — La CI lavora sui dati veri, non su un campione

**Milestone:** M5-T10

Il lavoro «dati» della CI alza un PostgreSQL di servizio, scarica i 43,5 MB da
UCI, carica il milione di righe ed esegue `dbt build` con tutti i test.

**Alternativa scartata:** un campione ridotto o dati generati.

**Perché:** dati finti non contengono i 34.153 duplicati esatti, le 3.457
rettifiche a quantità negativa e la fattura di reso con quantità positiva —
cioè esattamente ciò che i test devono intercettare. Verificare la pipeline su
dati che non hanno i problemi per cui è stata scritta significa non verificarla.

Costa 199 secondi a esecuzione, con la sorgente in cache. In cambio, ogni push
dimostra che la pipeline produce gli stessi numeri su una macchina che non ha
mai visto il progetto: 1.067.371 → 1.021.137 → 1.021.137.

---

## D17 — I cruscotti si costruiscono da codice, non a clic

**Milestone:** M7-T3, M7-T4, M7-T5, M7-T6, M7-T7

Le quindici domande e i tre cruscotti sono definiti in `metabase/domande.py` e
creati via API da `metabase/configura.py`. `make cruscotti` li ricostruisce
identici su un'istanza vuota.

**Alternativa scartata:** disegnarli nell'interfaccia di Metabase, che è il
modo per cui lo strumento è fatto.

**Perché:** un cruscotto costruito a mano vive su una macchina sola. Non si
legge in una pull request, non si rifà altrove, e il giorno che qualcuno
chiede perché un numero è cambiato non c'è niente da guardare. Le stesse tre
proprietà che il progetto pretende dalle trasformazioni — versionate,
leggibili, ripetibili — valgono per le pagine che le mostrano.

Il prezzo è reale: l'API di Metabase non è pensata per questo uso e i payload
delle schede sono verbosi. È un costo che si paga una volta.

---

## D18 — Gli indicatori si calcolano in dbt, a più livelli di aggregazione

**Milestone:** M7-T3

`agg_indicatori_periodo` calcola i cinque indicatori con `grouping sets` su
cinque livelli: `tutto`, `anno`, `mese`, `paese`, `anno_paese`.

**Alternativa scartata:** una tabella alla grana più fine, lasciando che
Metabase aggreghi.

**Perché:** due indicatori su cinque non sono additivi. I **clienti attivi**
sono un conteggio di valori distinti — lo stesso cliente compra a gennaio e a
marzo, e sommare i mesi lo conta due volte. Lo **scontrino medio** e il **tasso
di reso** sono rapporti, e il rapporto delle somme non è la somma dei
rapporti. Un cruscotto che sommasse i valori mensili mostrerebbe numeri
sbagliati in eccesso, senza che nulla lo segnali.

**Conseguenza:** ogni domanda deve filtrare `livello`. Un test dbt pretende che
il livello «tutto» abbia una riga sola, perché è l'errore più facile da
introdurre aggiungendo un raggruppamento.

---

## D19 — Nessuna demo online, e il motivo sta nel README

**Milestone:** M8-T4

Il case study non promette un cruscotto da visitare. Al suo posto ci sono gli
screenshot, il repository e quattro comandi che ricostruiscono tutto.

**Alternative scartate:** pubblicare il database su un piano gratuito, oppure
pubblicarne una fetta ridotta.

**Perché.** Il database pesa **491 MB**: 272 MB lo schema `raw`, 190 MB i
`marts`. I piani gratuiti che reggerebbero quella dimensione non offrono un
motore di interrogazione sempre acceso, e Metabase Cloud non ha un piano
gratuito: servirebbe una macchina a pagamento per tenere in piedi una demo che
nessuno interroga.

La fetta ridotta — l'ultimo trimestre, circa 200.000 righe e 40 MB — starebbe
comodamente ovunque. Ma mostrerebbe **numeri diversi da quelli del case
study**: chi apre la demo dopo aver letto «1.067.371 righe» ne troverebbe
duecentomila, e o si fida meno di tutto il resto o va spiegato in ogni pagina.

Una promessa che scade fra sei mesi, quando il piano gratuito cambia
condizioni, vale meno di uno screenshot onesto.

**Conseguenza:** il README dichiara la scelta e il peso del database, invece di
tacere sull'assenza della demo.
