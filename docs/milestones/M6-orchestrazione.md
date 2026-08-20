# M6 — Orchestrazione

Chiusa il 20/08/2026 · commit iniziale `643f152` · commit finale `e1dfd74`

Sei task su sei. Un comando porta da file sorgente a marts testati in 54
secondi, e se qualcosa si rompe si capisce dove senza aprire un registro.

## 1. Cosa è stato costruito

`orchestration/flow.py`: cinque passi in fila — scaricamento, caricamento in
`raw`, `dbt run`, `dbt test`, freschezza — ognuno un task Prefect.

Rispetto a uno script che chiama le stesse funzioni una dopo l'altra, si
guadagnano tre cose concrete: i **ritentativi** dove hanno senso, i **tempi per
passo** registrati senza cronometrare a mano, e la **catena che si ferma** al
primo passo fallito invece di proseguire su dati che non ci sono.

## 2. File creati e modificati

| Percorso | Scopo |
| --- | --- |
| `orchestration/flow.py` | Il flusso completo, i task, il riepilogo, lo scheduler |
| `Makefile`, `make.ps1` | `make flow` esegue il flusso vero |

## 3. Decisioni tecniche

### Scelta: `dbt run` e `dbt test` sono due passi, non un `dbt build`
**Alternativa scartata:** un solo task che esegue `dbt build`.
**Perché:** `build` mescola le due cose, e un modello che non compila diventa
lo stesso evento di un test rosso. Sono problemi diversi: «i modelli non si
costruiscono» e «i modelli mentono» si risolvono in due posti diversi, e chi
legge il riepilogo deve capire subito quale dei due ha davanti.

### Scelta: i ritentativi solo sullo scaricamento
**Alternativa scartata:** ritentare ogni passo, che è il default comodo.
**Perché:** una rete che cade è un problema temporaneo e riprovare ha senso.
Un SQL sbagliato è sbagliato anche al terzo tentativo: ritentarlo non lo
aggiusta, ritarda l'errore di un minuto e lo fa sembrare intermittente. Tre
tentativi con attese crescenti (5, 15, 45 secondi) sul solo scaricamento.

### Scelta: la dipendenza fra i passi passa dai dati, non da un `wait_for`
**Perché:** `costruisci_modelli(target, righe_caricate)` riceve il conteggio
delle righe che non gli serve. Serve a Prefect: da quel parametro capisce che
il passo viene *dopo* il caricamento. Senza, i due partirebbero insieme e dbt
leggerebbe una tabella vuota. Legare i passi con i dati invece che con una
dichiarazione a parte significa che la dipendenza non si può dimenticare —
non compila.

### Scelta: dbt gira nello stesso processo, con `dbtRunner`
**Alternativa scartata:** lanciare un sottoprocesso.
**Perché:** gli errori arrivano come oggetti invece che come testo da
rileggere con un'espressione regolare, e non c'è di mezzo l'eseguibile che su
Windows il criterio di controllo delle applicazioni blocca.

### Scelta: lo scheduler c'è ma non è acceso
**Perché:** la sorgente si ferma al 9 dicembre 2011. Un'esecuzione notturna
ricaricherebbe ogni notte gli stessi dati per ottenere lo stesso risultato.
L'opzione `--programma "0 3 * * *"` esiste, costa cinque righe, e il giorno
che i dati arrivassero davvero ogni notte non ci sarebbe niente da inventare.

## 4. Numeri misurati

### Un'esecuzione completa, target `prod`

| Passo | Durata | |
| --- | ---: | --- |
| scaricamento | 0,7 s | file già presenti, checksum verificato |
| caricamento | 10,5 s | 1.067.371 righe |
| modelli (`dbt run`) | 19,4 s | 8 costruiti |
| test (`dbt test`) | 22,2 s | 94 superati |
| freschezza | 1,4 s | nei limiti |
| **totale** | **54,1 s** | |

Il processo dura una ventina di secondi in più (74 s): Prefect alza un server
temporaneo per registrare l'esecuzione e lo spegne alla fine.

Con lo scaricamento da rifare da zero il primo passo costa 47 secondi di
download più 62 di conversione, misurati in M2.

### I ritentativi, provati

Puntando il task a un indirizzo inesistente:

```
Task run 'scaricamento' - HTTPError 404 - Retry 1/3 will start 1 second(s) from now
Task run 'scaricamento' - HTTPError 404 - Retry 2/3 will start 1 second(s) from now
Task run 'scaricamento' - HTTPError 404 - Retry 3/3 will start 1 second(s) from now
Task run 'scaricamento' - HTTPError 404 - Retries are exhausted
```

Tre tentativi, poi si arrende invece di restare appeso.

### Il fallimento, provato

Aggiunto un modello con una colonna inesistente e rilanciato il flusso:

```
Database Error in model prova_rotta
Task run 'dbt run (prod)' - Finished in state Failed(...)
Flow run 'divergent-phoenix' - Finished in state Failed(...)
```

**Il task dei test non compare nel registro: non è mai partito.** Il processo
esce con codice 1, che è ciò che serve a uno scheduler esterno per accorgersene.

## 5. Problemi incontrati

**Le liste sono invarianti, e mypy lo fa notare.** `retry_delay_seconds`
accetta `list[float]`, e passargli `[5, 15, 45]` — una `list[int]` — è un
errore di tipo, non una svista da ignorare: se qualcuno inserisse un valore
non intero nella lista, il tipo dichiarato non lo proteggerebbe più.
Annotata come `list[float]`.

**Prefect si lamenta se un task gira fuori da un flusso.** Nella prova dei
ritentativi il task è stato invocato da solo, e Prefect ha avvisato di non
poter mandare i registri all'API senza un flow run. Funziona lo stesso, ma è
il segnale che quella è una prova manuale e non il modo di usarlo.

**Il risultato di un task fallito non si serializza.** Quando il task esce con
un'eccezione, Prefect prova a salvarne il risultato e con `HTTPError` non ci
riesce. È un avviso, non un errore, e non cambia l'esito — ma leggerlo per la
prima volta mentre si guarda un fallimento fa perdere qualche minuto a
chiedersi se sia quello il problema.

## 6. Cosa resta aperto

- **Nessuna notifica.** Il flusso fallisce e lo si scopre guardando. Il piano
  cita una notifica fra i passi; senza un canale scelto (posta, Slack) sarebbe
  codice che non si può provare, quindi resta fuori dichiarandolo.
- **Lo scheduler non gira.** L'opzione c'è, il processo che la usa dovrebbe
  restare acceso, e su dati storici non ha uno scopo.
- **Il flusso non passa dalla CI.** La CI esegue gli stessi passi ma
  singolarmente: verificare anche l'orchestrazione richiederebbe un altro
  lavoro da tre minuti per coprire cinque chiamate di funzione già coperte.
- **`--salta-scaricamento` si fida dei CSV presenti.** Non ne verifica il
  checksum: quello si controlla sull'Excel, e saltare il passo salta anche il
  controllo.

## 7. Come verificarlo

```bash
make up
make flow                  # oppure: .\make.ps1 flow
```

Alla fine stampa il riepilogo con i tempi di ogni passo.

Per vedere la catena fermarsi:

```bash
printf 'select colonna_che_non_esiste from {{ ref("stg_vendite") }}' > dbt/models/marts/prova_rotta.sql
make flow                  # dbt run fallisce, i test non partono, uscita 1
rm dbt/models/marts/prova_rotta.sql
```

Per l'esecuzione programmata:

```bash
uv run python -m orchestration.flow --programma "0 3 * * *"
```
