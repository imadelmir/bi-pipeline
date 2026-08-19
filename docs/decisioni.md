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
