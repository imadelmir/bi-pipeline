"""Crea l'utente con cui Metabase legge lo schema marts (M7-T2).

Metabase non si collega come amministratore. Ha un ruolo suo che sa fare una
cosa sola: `select` su `marts`. Non su `raw`, non su `staging`, e in nessun
caso `insert`, `update` o `delete`.

Non è teoria: uno strumento di analisi con permessi di scrittura è una riga di
SQL nativo dentro una domanda salvata dal cancellare una tabella. Il costo di
evitarlo è questo file.

I permessi si danno anche **per il futuro**: `alter default privileges` fa sì
che le tabelle create domani da dbt siano leggibili senza dover rilanciare
niente. Senza, ogni nuovo modello sarebbe invisibile a Metabase finché
qualcuno non se ne accorge.

Lo script è idempotente: rilanciarlo aggiorna la password e riconferma i
permessi.

Uso:

    uv run python -m scripts.utente_metabase
"""

from __future__ import annotations

import io
import os
import sys

from psycopg import sql

from ingestion.db import connessione

for _flusso in (sys.stdout, sys.stderr):
    if isinstance(_flusso, io.TextIOWrapper) and _flusso.encoding.lower() != "utf-8":
        _flusso.reconfigure(encoding="utf-8", errors="replace")

SCHEMA_LEGGIBILE = "marts"


def crea_utente(nome: str, password: str, database: str, proprietario: str) -> None:
    with connessione() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            utente = sql.Identifier(nome)

            cur.execute("select 1 from pg_roles where rolname = %s", (nome,))
            if cur.fetchone() is None:
                cur.execute(
                    sql.SQL("create role {} login password {}").format(
                        utente, sql.Literal(password)
                    )
                )
                print(f"creato il ruolo {nome}")
            else:
                cur.execute(
                    sql.SQL("alter role {} with login password {}").format(
                        utente, sql.Literal(password)
                    )
                )
                print(f"aggiornata la password di {nome}")

            # Connettersi al database, ma non creare oggetti in nessuno schema.
            cur.execute(
                sql.SQL("grant connect on database {} to {}").format(
                    sql.Identifier(database), utente
                )
            )

            # Vedere lo schema marts e leggerne le tabelle esistenti.
            cur.execute(
                sql.SQL("grant usage on schema {} to {}").format(
                    sql.Identifier(SCHEMA_LEGGIBILE), utente
                )
            )
            cur.execute(
                sql.SQL("grant select on all tables in schema {} to {}").format(
                    sql.Identifier(SCHEMA_LEGGIBILE), utente
                )
            )

            # E anche quelle che dbt creerà domani.
            cur.execute(
                sql.SQL(
                    "alter default privileges for role {} in schema {} "
                    "grant select on tables to {}"
                ).format(
                    sql.Identifier(proprietario),
                    sql.Identifier(SCHEMA_LEGGIBILE),
                    utente,
                )
            )

            # Esplicito ciò che già non ha: i permessi non si ereditano da
            # `public` per caso, ma dichiararlo rende il file una risposta
            # completa alla domanda «cosa può fare questo utente?».
            for schema in ("raw", "staging"):
                cur.execute(
                    sql.SQL("revoke all on schema {} from {}").format(
                        sql.Identifier(schema), utente
                    )
                )

            print(f"{nome}: select su {SCHEMA_LEGGIBILE}, niente altro")


def verifica(nome: str) -> None:
    """Controlla che l'utente legga marts e non scriva da nessuna parte."""
    with connessione() as conn, conn.cursor() as cur:
        cur.execute(
            "select has_schema_privilege(%s, 'marts', 'USAGE'), "
            "has_table_privilege(%s, 'marts.fct_vendite', 'SELECT'), "
            "has_table_privilege(%s, 'marts.fct_vendite', 'INSERT'), "
            "has_schema_privilege(%s, 'raw', 'USAGE'), "
            "has_schema_privilege(%s, 'staging', 'USAGE')",
            (nome, nome, nome, nome, nome),
        )
        riga = cur.fetchone()

    if riga is None:
        raise RuntimeError("la verifica dei permessi non ha restituito nulla")

    usa_marts, legge, scrive, vede_raw, vede_staging = riga
    print()
    print("verifica dei permessi")
    print(f"  usa lo schema marts     {usa_marts}   (atteso: True)")
    print(f"  legge fct_vendite       {legge}   (atteso: True)")
    print(f"  scrive su fct_vendite   {scrive}  (atteso: False)")
    print(f"  vede lo schema raw      {vede_raw}  (atteso: False)")
    print(f"  vede lo schema staging  {vede_staging}  (atteso: False)")

    if not (usa_marts and legge) or scrive or vede_raw or vede_staging:
        raise RuntimeError("i permessi non sono quelli attesi")


def main() -> int:
    nome = os.environ.get("METABASE_DB_USER", "metabase_lettura")
    password = os.environ.get("METABASE_DB_PASSWORD")
    if not password:
        raise RuntimeError(
            "manca METABASE_DB_PASSWORD: copia .env.example in .env e riempilo"
        )

    crea_utente(
        nome=nome,
        password=password,
        database=os.environ["POSTGRES_DB"],
        proprietario=os.environ["POSTGRES_USER"],
    )
    verifica(nome)
    return 0


if __name__ == "__main__":
    sys.exit(main())
