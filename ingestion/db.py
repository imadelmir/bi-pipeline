"""Connessione a PostgreSQL.

Le credenziali arrivano da `.env`, mai dal codice. `load_dotenv` non
sovrascrive le variabili già presenti nell'ambiente: in locale vince il file,
in CI vincono le variabili del runner, e non serve un ramo `if` per distinguere
i due casi.
"""

from __future__ import annotations

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.rows import TupleRow

from ingestion.percorsi import RADICE

CARTELLA_SQL = Path(__file__).resolve().parent / "sql"


class ConfigurazioneMancante(RuntimeError):
    """Manca una variabile d'ambiente senza la quale non si va da nessuna parte."""


def _variabile(nome: str) -> str:
    valore = os.environ.get(nome)
    if not valore:
        raise ConfigurazioneMancante(
            f"manca la variabile {nome}. Copia .env.example in .env e riempilo:\n"
            f"  cp .env.example .env"
        )
    return valore


def stringa_di_connessione() -> str:
    """La stringa libpq costruita dalle variabili di `.env`."""
    load_dotenv(RADICE / ".env")

    utente = _variabile("POSTGRES_USER")
    password = _variabile("POSTGRES_PASSWORD")
    database = _variabile("POSTGRES_DB")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    porta = os.environ.get("POSTGRES_PORT", "5432")

    return (
        f"host={host} port={porta} dbname={database} user={utente} password={password}"
    )


def connessione() -> psycopg.Connection[TupleRow]:
    """Apre una connessione. Chi la chiama la chiude, di solito con un `with`.

    `autocommit` resta spento di proposito: il caricamento di M2-T8 deve poter
    cancellare e ricaricare dentro una transazione sola, e con l'autocommit
    acceso un'interruzione a metà lascerebbe la tabella vuota.
    """
    return psycopg.connect(stringa_di_connessione())


def esegui_file_sql(nome: str) -> None:
    """Esegue uno dei file in `ingestion/sql/`. Sono tutti idempotenti."""
    percorso = CARTELLA_SQL / nome
    istruzioni = percorso.read_text(encoding="utf-8")

    with connessione() as conn:
        with conn.cursor() as cur:
            cur.execute(istruzioni)
        conn.commit()

    print(f"eseguito {percorso.name}")
