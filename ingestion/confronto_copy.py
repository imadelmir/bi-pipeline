"""COPY contro `pandas.to_sql`, cronometrati (M2-T6).

Il piano dice che `COPY` è più veloce. Dirlo non basta: questo modulo carica le
stesse centomila righe nei due modi, sullo stesso database, e misura.

`to_sql` costruisce istruzioni `INSERT` e le manda al server; `COPY` apre un
flusso solo e ci scrive dentro senza analizzare una istruzione per riga. Il
rapporto fra i due tempi è uno dei numeri che finiscono nel case study.

Il confronto lavora in uno schema `prova`, creato e cancellato dal modulo:
`raw` non si tocca.

Uso:

    uv run python -m ingestion.confronto_copy
    uv run python -m ingestion.confronto_copy --righe 50000
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from ingestion.db import connessione, stringa_di_connessione
from ingestion.formato import numero
from ingestion.percorsi import CARTELLA_CSV, RADICE

RIGHE = 100_000
SCHEMA = "prova"
RELAZIONE = RADICE / "docs" / "confronto-copy.md"


def _url_sqlalchemy() -> str:
    """La stessa connessione di `db.py`, nella forma che vuole SQLAlchemy."""
    parti = dict(pezzo.split("=", 1) for pezzo in stringa_di_connessione().split(" "))
    return (
        f"postgresql+psycopg://{parti['user']}:{parti['password']}"
        f"@{parti['host']}:{parti['port']}/{parti['dbname']}"
    )


def prepara_schema() -> None:
    with connessione() as conn:
        with conn.cursor() as cur:
            cur.execute(f"drop schema if exists {SCHEMA} cascade")
            cur.execute(f"create schema {SCHEMA}")
        conn.commit()


def pulisci_schema() -> None:
    with connessione() as conn:
        with conn.cursor() as cur:
            cur.execute(f"drop schema if exists {SCHEMA} cascade")
        conn.commit()


def campione(percorso: Path, righe: int) -> pd.DataFrame:
    """Le prime N righe del CSV, lette una volta sola.

    La lettura sta fuori dai cronometri di proposito: si misura la scrittura
    verso il database, non la velocità di pandas nel leggere un file.
    """
    return pd.read_csv(percorso, nrows=righe, dtype=str)


def misura_copy(dati: pd.DataFrame) -> float:
    """Carica con COPY e restituisce i secondi impiegati."""
    colonne = [f'"{c}"' for c in dati.columns]
    definizione = ", ".join(f"{c} text" for c in colonne)

    with connessione() as conn:
        with conn.cursor() as cur:
            cur.execute(f"drop table if exists {SCHEMA}.con_copy")
            cur.execute(f"create table {SCHEMA}.con_copy ({definizione})")
        conn.commit()

        righe = dati.astype(object).where(pd.notna(dati), None).values.tolist()

        inizio = time.perf_counter()
        with (
            conn.cursor() as cur,
            cur.copy(
                f"copy {SCHEMA}.con_copy ({', '.join(colonne)}) from stdin"
            ) as copia,
        ):
            for riga in righe:
                copia.write_row(riga)
        conn.commit()
        return time.perf_counter() - inizio


def misura_to_sql(dati: pd.DataFrame) -> float:
    """Carica con pandas.to_sql e restituisce i secondi impiegati."""
    motore = create_engine(_url_sqlalchemy())

    with motore.begin() as conn:
        conn.execute(text(f"drop table if exists {SCHEMA}.con_to_sql"))

    inizio = time.perf_counter()
    dati.to_sql(
        "con_to_sql",
        motore,
        schema=SCHEMA,
        if_exists="replace",
        index=False,
    )
    durata = time.perf_counter() - inizio

    motore.dispose()
    return durata


def _conta(tabella: str) -> int:
    with connessione() as conn, conn.cursor() as cur:
        cur.execute(f"select count(*) from {SCHEMA}.{tabella}")
        riga = cur.fetchone()
    return 0 if riga is None else int(riga[0])


def scrivi_relazione(righe: int, tempo_copy: float, tempo_to_sql: float) -> Path:
    rapporto = tempo_to_sql / tempo_copy
    al_secondo_copy = numero(int(righe / tempo_copy))
    al_secondo_to_sql = numero(int(righe / tempo_to_sql))
    testo = f"""# COPY contro `pandas.to_sql`

Generato da `uv run python -m ingestion.confronto_copy` il \
{datetime.now().astimezone():%d/%m/%Y} (M2-T6).

Stesse **{numero(righe)} righe**, stesso database, stesso momento. La lettura
del CSV è fuori dal cronometro: si misura la scrittura verso PostgreSQL.

| Metodo | Secondi | Righe al secondo |
| --- | --- | --- |
| `COPY` (psycopg) | **{tempo_copy:.2f}** | {al_secondo_copy} |
| `pandas.to_sql` (SQLAlchemy) | **{tempo_to_sql:.2f}** | {al_secondo_to_sql} |

**`COPY` è {rapporto:.1f} volte più veloce.**

Proiettato sul milione di righe del dataset: circa
{tempo_copy * 1_067_371 / righe:.0f} secondi contro
{tempo_to_sql * 1_067_371 / righe:.0f}.

## Perché

`to_sql` traduce ogni riga in un'istruzione `INSERT`: il server la riceve, la
analizza, la pianifica e la esegue, una per una. `COPY` apre un flusso e ci
scrive dentro il blocco di righe: nessuna istruzione da analizzare, nessun
piano da costruire, e il server scrive direttamente nelle pagine della tabella.

La differenza non è di configurazione: sono due protocolli diversi. Ed è il
motivo per cui l'ingestione di questo progetto usa `COPY` (M2-T5) e non la
scorciatoia di una riga di pandas.
"""
    RELAZIONE.write_text(testo, encoding="utf-8")
    return RELAZIONE


def main() -> int:
    lettore = argparse.ArgumentParser(description="Confronta COPY e pandas.to_sql.")
    lettore.add_argument("--righe", type=int, default=RIGHE)
    opzioni = lettore.parse_args()

    file_csv = sorted(CARTELLA_CSV.glob("vendite_*.csv"))
    if not file_csv:
        raise FileNotFoundError(f"nessun CSV in {CARTELLA_CSV}")

    dati = campione(file_csv[0], opzioni.righe)
    righe = len(dati)
    print(f"campione: {numero(righe)} righe da {file_csv[0].name}")

    prepara_schema()
    try:
        tempo_copy = misura_copy(dati)
        print(f"COPY:       {tempo_copy:6.2f} s  ({numero(_conta('con_copy'))} righe)")

        tempo_to_sql = misura_to_sql(dati)
        print(
            f"to_sql:     {tempo_to_sql:6.2f} s  ({numero(_conta('con_to_sql'))} righe)"
        )

        print(f"\nCOPY è {tempo_to_sql / tempo_copy:.1f} volte più veloce")
        print(f"scritto {scrivi_relazione(righe, tempo_copy, tempo_to_sql)}")
    finally:
        # Lo schema di prova sparisce anche se il confronto fallisce: non deve
        # restare in giro una tabella che somiglia a un dato vero.
        pulisci_schema()

    return 0


if __name__ == "__main__":
    sys.exit(main())
