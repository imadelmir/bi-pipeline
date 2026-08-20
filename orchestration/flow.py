"""Il flusso completo, da file vuoto a marts pronti (M6).

Quattro passi in fila:

    scaricamento → caricamento in raw → dbt run → dbt test

Ognuno è un task Prefect, e questo dà tre cose che uno script sequenziale non
dà: i **ritentativi** dove servono, i **tempi per passo** registrati senza
doverli cronometrare a mano, e la **catena che si ferma** quando un passo
fallisce, invece di proseguire su dati che non ci sono.

Perché `dbt run` e `dbt test` sono due passi e non `dbt build`: `build` li
mescola, e un modello rotto e un test rosso diventano lo stesso evento. Qui
si distinguono — «i modelli non si costruiscono» e «i modelli mentono» sono
due problemi diversi, e chi legge il riepilogo deve capire quale dei due ha.

Uso:

    uv run python -m orchestration.flow
    uv run python -m orchestration.flow --target dev
    uv run python -m orchestration.flow --salta-scaricamento

    # resta in ascolto ed esegue ogni notte alle 3 (M6-T5)
    uv run python -m orchestration.flow --programma "0 3 * * *"
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass, field
from typing import Any

from prefect import flow, get_run_logger, task

from ingestion import load
from ingestion.formato import numero, secondi
from ingestion.percorsi import CARTELLA_CSV, CARTELLA_GREZZI, prepara_cartelle
from ingestion.sources import online_retail

# Tre tentativi sullo scaricamento, con attese crescenti. Solo lì: ritentare
# una trasformazione fallita non ha senso — se il SQL è sbagliato, è sbagliato
# anche al terzo tentativo, e riprovarlo nasconde l'errore dietro un'attesa.
TENTATIVI_RETE = 3
# `float` e non `int`: Prefect dichiara `list[float]`, e una lista di interi
# non è una lista di float per il sistema dei tipi — le liste sono invarianti.
ATTESE_RETE: list[float] = [5, 15, 45]


@dataclass
class Passo:
    """Quanto è durato un passo e quante righe ha toccato."""

    nome: str
    secondi: float
    righe: int | None = None
    nota: str = ""


@dataclass
class Riepilogo:
    passi: list[Passo] = field(default_factory=list)

    def aggiungi(self, passo: Passo) -> None:
        self.passi.append(passo)

    def righe_stampabili(self) -> list[str]:
        larghezza = max((len(p.nome) for p in self.passi), default=10)
        righe = ["", "riepilogo dell'esecuzione", "-" * (larghezza + 34)]
        for passo in self.passi:
            quante = f"{numero(passo.righe):>12} righe" if passo.righe else " " * 18
            righe.append(
                f"  {passo.nome:<{larghezza}}  {secondi(passo.secondi):>10}"
                f"  {quante}  {passo.nota}"
            )
        totale = sum(p.secondi for p in self.passi)
        righe.append("-" * (larghezza + 34))
        righe.append(f"  {'totale':<{larghezza}}  {secondi(totale):>10}")
        return righe


def _dbt(comando: list[str]) -> Any:
    """Esegue dbt nello stesso processo e restituisce il risultato.

    Si usa `dbtRunner` invece di lanciare un sottoprocesso: gli errori
    arrivano come oggetti invece che come testo da rileggere, e non c'è di
    mezzo l'eseguibile che su Windows il criterio di controllo delle
    applicazioni blocca (vedi `scripts/esegui_dbt.py`).
    """
    from dbt.cli.main import dbtRunner

    return dbtRunner().invoke(
        [*comando, "--project-dir", "dbt", "--profiles-dir", "dbt"]
    )


@task(
    name="scaricamento",
    retries=TENTATIVI_RETE,
    retry_delay_seconds=ATTESE_RETE,
    task_run_name="scaricamento",
)
def scarica_sorgente(forza: bool = False) -> int:
    """Scarica l'archivio, verifica il checksum, converte in CSV.

    È l'unico passo che parla con l'esterno, quindi l'unico che ritenta: una
    rete che cade a metà è un problema temporaneo, e ripartire da capo per
    colpa di un timeout sarebbe uno spreco.
    """
    logger = get_run_logger()
    prepara_cartelle()

    archivio = online_retail.scarica_archivio(CARTELLA_GREZZI, forza=forza)
    excel = online_retail.estrai_excel(archivio, CARTELLA_GREZZI)
    online_retail.verifica_checksum(excel)
    csv = online_retail.converti_in_csv(excel, CARTELLA_CSV, forza=forza)

    logger.info("pronti %d CSV", len(csv))
    return len(csv)


@task(name="caricamento", task_run_name="caricamento in raw")
def carica_in_raw() -> int:
    """Cancella e ricarica per file d'origine, dentro una transazione."""
    logger = get_run_logger()

    from ingestion.db import esegui_file_sql

    esegui_file_sql("raw.sql")
    righe = load.carica(CARTELLA_CSV)

    logger.info("caricate %s righe in raw", numero(righe))
    return righe


@task(name="modelli", task_run_name="dbt run ({target})")
def costruisci_modelli(target: str, righe_caricate: int) -> int:
    """Costruisce i modelli. Il conteggio in ingresso crea la dipendenza.

    `righe_caricate` non serve al corpo della funzione: serve a Prefect, che
    da quel parametro capisce che questo passo viene *dopo* il caricamento.
    Senza, i due partirebbero insieme e dbt leggerebbe una tabella vuota.
    """
    logger = get_run_logger()
    esito = _dbt(["run", "--target", target])

    if not esito.success:
        raise RuntimeError(
            f"dbt run è fallito: {esito.exception or 'vedi il registro'}"
        )

    costruiti = len(esito.result or [])
    logger.info("costruiti %d modelli su %d righe caricate", costruiti, righe_caricate)
    return costruiti


@task(name="test", task_run_name="dbt test ({target})")
def esegui_test(target: str, modelli_costruiti: int) -> int:
    """Esegue i test. Parte solo se i modelli sono stati costruiti."""
    logger = get_run_logger()
    esito = _dbt(["test", "--target", target])

    if not esito.success:
        raise RuntimeError("almeno un test è fallito: i marts non sono affidabili")

    passati = len(esito.result or [])
    logger.info("%d test superati su %d modelli", passati, modelli_costruiti)
    return passati


@task(name="freschezza", task_run_name="freschezza della sorgente")
def controlla_freschezza(target: str, test_passati: int) -> None:
    """Controlla da quanto tempo non arrivano dati nuovi."""
    logger = get_run_logger()
    esito = _dbt(["source", "freshness", "--target", target])
    stato = "nei limiti" if esito.success else "oltre la soglia"
    logger.info("freschezza %s (dopo %d test superati)", stato, test_passati)


@flow(name="bi-pipeline", log_prints=True)
def pipeline(
    target: str = "prod",
    salta_scaricamento: bool = False,
    forza_scaricamento: bool = False,
) -> Riepilogo:
    """Dal file sorgente ai marts pronti, con i tempi di ogni passo."""
    logger = get_run_logger()
    logger.info("target: %s", target)
    riepilogo = Riepilogo()

    if salta_scaricamento:
        logger.info("scaricamento saltato su richiesta")
        riepilogo.aggiungi(Passo("scaricamento", 0.0, nota="saltato"))
    else:
        inizio = time.perf_counter()
        file_csv = scarica_sorgente(forza=forza_scaricamento)
        riepilogo.aggiungi(
            Passo("scaricamento", time.perf_counter() - inizio, nota=f"{file_csv} CSV")
        )

    inizio = time.perf_counter()
    righe = carica_in_raw()
    riepilogo.aggiungi(Passo("caricamento", time.perf_counter() - inizio, righe=righe))

    inizio = time.perf_counter()
    modelli = costruisci_modelli(target, righe)
    riepilogo.aggiungi(
        Passo("modelli", time.perf_counter() - inizio, nota=f"{modelli} costruiti")
    )

    inizio = time.perf_counter()
    test = esegui_test(target, modelli)
    riepilogo.aggiungi(
        Passo("test", time.perf_counter() - inizio, nota=f"{test} superati")
    )

    inizio = time.perf_counter()
    controlla_freschezza(target, test)
    riepilogo.aggiungi(Passo("freschezza", time.perf_counter() - inizio))

    for riga in riepilogo.righe_stampabili():
        print(riga)

    return riepilogo


def main() -> int:
    lettore = argparse.ArgumentParser(description="Esegue la pipeline completa.")
    lettore.add_argument("--target", default="prod", choices=["dev", "prod"])
    lettore.add_argument(
        "--salta-scaricamento",
        action="store_true",
        help="usa i CSV già presenti invece di ricontrollare la sorgente",
    )
    lettore.add_argument(
        "--forza-scaricamento",
        action="store_true",
        help="riscarica e riconverte anche se i file ci sono",
    )
    lettore.add_argument(
        "--programma",
        metavar="CRON",
        help='esegue il flusso a ripetizione secondo un cron (es. "0 3 * * *") '
        "invece di una volta sola. Il processo resta in ascolto.",
    )
    opzioni = lettore.parse_args()

    if opzioni.programma:
        # `serve` tiene vivo il processo e fa partire il flusso all'ora
        # stabilita. Su dati storici non serve a niente — la sorgente è ferma
        # al 2011 — ma è il pezzo che mancherebbe il giorno che i dati
        # arrivassero ogni notte, e costa cinque righe averlo pronto.
        pipeline.serve(
            name="bi-pipeline-notturna",
            cron=opzioni.programma,
            parameters={
                "target": opzioni.target,
                "salta_scaricamento": opzioni.salta_scaricamento,
            },
        )
        return 0

    pipeline(
        target=opzioni.target,
        salta_scaricamento=opzioni.salta_scaricamento,
        forza_scaricamento=opzioni.forza_scaricamento,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
