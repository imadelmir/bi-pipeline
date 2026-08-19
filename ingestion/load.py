"""Caricamento dei CSV nello schema raw con COPY (M2-T5, M2-T8, M2-T9).

Tre proprietà, e ognuna costa una riga di codice in più:

**COPY invece di INSERT.** `pandas.to_sql` emette un `INSERT` per riga: un
milione di andate e ritorni con il server. `COPY` apre un flusso solo e ci
scrive dentro. Il confronto misurato è in `ingestion/confronto_copy.py`.

**Idempotente.** Ogni file cancella le proprie righe prima di ricaricarle, e
lo fa dentro la stessa transazione: rilanciare l'ingestione dieci volte lascia
sempre lo stesso conteggio. Senza, ogni rilancio raddoppierebbe i dati — e ce
ne si accorgerebbe dal cruscotto, con il fatturato già sbagliato.

**Tutto o niente.** Il `delete` e il `copy` stanno in una transazione sola: se
il processo muore a metà, PostgreSQL annulla entrambi. Il conteggio in tabella
è sempre zero o completo, mai un valore intermedio.

Uso:

    uv run python -m ingestion.load
    uv run python -m ingestion.load --solo vendite_2009_2010.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow

from ingestion import registry
from ingestion.db import connessione, esegui_file_sql
from ingestion.formato import numero, secondi
from ingestion.percorsi import CARTELLA_CSV
from ingestion.sources.online_retail import calcola_sha256

# Le colonne della tabella di atterraggio, nell'ordine in cui stanno nel CSV.
# `file_origine` si aggiunge in coda a ogni riga; `caricato_il` lo mette il
# database con il suo default.
COLONNE = (
    "invoice",
    "stock_code",
    "description",
    "quantity",
    "invoice_date",
    "price",
    "customer_id",
    "country",
    "file_origine",
)

# Ogni quante righe stampare a che punto siamo. Su un milione di righe, un
# messaggio ogni centomila dà dieci righe di uscita: abbastanza per capire che
# non è bloccato, poche da non sporcare il registro di un'esecuzione notturna.
BLOCCO = 100_000


def _righe_del_csv(percorso: Path) -> list[list[str | None]]:
    """Legge il CSV e restituisce le righe pronte per COPY.

    L'unica cosa che cambia rispetto al file è che il campo vuoto diventa
    `NULL` invece di stringa vuota. Non è una pulizia: è la traduzione fedele
    di «qui non c'è niente». Tenere `''` costringerebbe ogni modello di staging
    a scrivere `nullif(colonna, '')`, e prima o poi qualcuno se ne dimentica.
    """
    with percorso.open(encoding="utf-8", newline="") as file:
        lettore = csv.reader(file)
        next(lettore)  # l'intestazione
        return [
            [valore if valore != "" else None for valore in riga] for riga in lettore
        ]


def carica_file(
    conn: psycopg.Connection[TupleRow],
    percorso: Path,
    righe: list[list[str | None]],
) -> int:
    """Cancella le righe di questo file e le ricarica. Da chiamare in transazione."""
    nome = percorso.name

    with conn.cursor() as cur:
        cur.execute("delete from raw.vendite where file_origine = %s", (nome,))
        cancellate = cur.rowcount
        if cancellate > 0:
            print(f"  cancellate {numero(cancellate)} righe del caricamento precedente")

        caricate = 0
        with cur.copy(
            "copy raw.vendite (invoice, stock_code, description, quantity, "
            "invoice_date, price, customer_id, country, file_origine) from stdin"
        ) as copia:
            for riga in righe:
                copia.write_row([*riga, nome])
                caricate += 1
                if caricate % BLOCCO == 0:
                    print(f"  {numero(caricate)} righe…")

    return caricate


def carica(cartella: Path, solo: str | None = None) -> int:
    """Carica tutti i CSV della cartella. Restituisce le righe caricate."""
    file_csv = sorted(cartella.glob("vendite_*.csv"))
    if solo is not None:
        file_csv = [p for p in file_csv if p.name == solo]
    if not file_csv:
        raise FileNotFoundError(
            f"nessun CSV da caricare in {cartella}: esegui prima "
            "`uv run python -m ingestion.sources.online_retail`"
        )

    totale = 0
    for percorso in file_csv:
        print(f"{percorso.name}")
        inizio = time.perf_counter()

        checksum = calcola_sha256(percorso)
        identificativo = registry.apri(percorso.name, checksum)

        try:
            righe = _righe_del_csv(percorso)
            # Il `with` sulla connessione è la transazione: si chiude con un
            # commit se il blocco finisce bene, con un rollback se alza.
            with connessione() as conn:
                caricate = carica_file(conn, percorso, righe)
        except BaseException as errore:
            # Anche KeyboardInterrupt: un Ctrl-C deve lasciare il registro
            # coerente quanto la tabella (M2-T9).
            registry.fallisci(identificativo, f"{type(errore).__name__}: {errore}")
            raise

        registry.chiudi(identificativo, caricate)
        durata = time.perf_counter() - inizio
        print(f"  {numero(caricate)} righe in {secondi(durata)}")
        totale += caricate

    return totale


def conteggio() -> int:
    """Quante righe ci sono adesso in raw.vendite."""
    with connessione() as conn, conn.cursor() as cur:
        cur.execute("select count(*) from raw.vendite")
        riga = cur.fetchone()
    return 0 if riga is None else int(riga[0])


def main() -> int:
    lettore = argparse.ArgumentParser(
        description="Carica i CSV nello schema raw con COPY. Rilanciarlo non duplica."
    )
    lettore.add_argument(
        "--solo", help="carica un solo file, per nome (es. vendite_2009_2010.csv)"
    )
    opzioni = lettore.parse_args()

    esegui_file_sql("raw.sql")

    inizio = time.perf_counter()
    caricate = carica(CARTELLA_CSV, solo=opzioni.solo)
    durata = time.perf_counter() - inizio

    print(f"\ncaricate {numero(caricate)} righe in {secondi(durata)}")
    print(f"in tabella: {numero(conteggio())} righe")
    return 0


if __name__ == "__main__":
    sys.exit(main())
