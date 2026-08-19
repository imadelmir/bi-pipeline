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
