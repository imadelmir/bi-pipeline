"""Registro dei caricamenti (M2-T7).

Un record per ogni tentativo: quale file, con che checksum, quando è iniziato,
quando è finito, quante righe, com'è andata. Serve a rispondere alla domanda
che prima o poi arriva sempre — «questo numero da dove viene?» — senza doverlo
ricostruire a memoria.

**Il registro scrive su una connessione tutta sua.** Se condividesse la
transazione del caricamento, un fallimento porterebbe con sé anche la riga che
dice «è fallito»: resterebbe una tabella vuota e nessuna traccia del perché.
Il registro deve sopravvivere proprio ai casi che deve raccontare.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import psycopg
from psycopg.rows import TupleRow

from ingestion.db import connessione


@dataclass(frozen=True)
class VoceRegistro:
    """Una riga del registro, come si legge."""

    id: int
    file_origine: str
    checksum: str
    iniziato_il: datetime
    finito_il: datetime | None
    righe_caricate: int | None
    esito: str
    messaggio: str | None


def _connessione_indipendente() -> psycopg.Connection[TupleRow]:
    conn = connessione()
    conn.autocommit = True
    return conn


def apri(file_origine: str, checksum: str) -> int:
    """Registra l'inizio di un caricamento e restituisce l'identificativo."""
    with _connessione_indipendente() as conn, conn.cursor() as cur:
        cur.execute(
            "insert into raw.registro_caricamenti "
            "(file_origine, checksum, esito) values (%s, %s, 'in corso') "
            "returning id",
            (file_origine, checksum),
        )
        riga = cur.fetchone()

    if riga is None:  # pragma: no cover - insert ... returning restituisce sempre
        raise RuntimeError("l'inserimento nel registro non ha restituito un id")
    return int(riga[0])


def chiudi(identificativo: int, righe: int) -> None:
    """Segna il caricamento come completato, con quante righe sono entrate."""
    with _connessione_indipendente() as conn, conn.cursor() as cur:
        cur.execute(
            "update raw.registro_caricamenti "
            "set finito_il = now(), righe_caricate = %s, esito = 'completato' "
            "where id = %s",
            (righe, identificativo),
        )


def fallisci(identificativo: int, messaggio: str) -> None:
    """Segna il caricamento come fallito, con il motivo."""
    with _connessione_indipendente() as conn, conn.cursor() as cur:
        cur.execute(
            "update raw.registro_caricamenti "
            "set finito_il = now(), esito = 'fallito', messaggio = %s "
            "where id = %s",
            # Il messaggio di un'eccezione può essere lunghissimo: qui interessa
            # riconoscere l'errore, non conservarne il romanzo.
            (messaggio[:2000], identificativo),
        )


def elenco(quanti: int = 20) -> list[VoceRegistro]:
    """Gli ultimi caricamenti, dal più recente."""
    with connessione() as conn, conn.cursor() as cur:
        cur.execute(
            "select id, file_origine, checksum, iniziato_il, finito_il, "
            "righe_caricate, esito, messaggio "
            "from raw.registro_caricamenti order by id desc limit %s",
            (quanti,),
        )
        righe = cur.fetchall()

    return [
        VoceRegistro(
            id=int(riga[0]),
            file_origine=str(riga[1]),
            checksum=str(riga[2]),
            iniziato_il=riga[3],
            finito_il=riga[4],
            righe_caricate=None if riga[5] is None else int(riga[5]),
            esito=str(riga[6]),
            messaggio=None if riga[7] is None else str(riga[7]),
        )
        for riga in righe
    ]
