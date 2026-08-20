"""Prepara l'istanza Metabase (M7-T1, M7-T2).

Amministratore, database in sola lettura, sincronizzazione dello schema.

Da eseguire una volta dopo `make up`. È idempotente: se l'istanza è già
configurata, si limita a controllare che il database sia collegato e a
risincronizzare lo schema.

Uso:

    uv run python -m metabase.prepara
"""

from __future__ import annotations

import io
import os
import sys
import time
from typing import Any

from metabase.api import ErroreMetabase, Metabase

for _flusso in (sys.stdout, sys.stderr):
    if isinstance(_flusso, io.TextIOWrapper) and _flusso.encoding.lower() != "utf-8":
        _flusso.reconfigure(encoding="utf-8", errors="replace")

NOME_DATABASE = "BI Pipeline"

# Le tabelle che Metabase deve vedere. Se ne mancano, la sincronizzazione non
# è finita: si aspetta invece di proseguire e trovarsi domande rotte.
TABELLE_ATTESE = 7


def _dettagli_connessione() -> dict[str, Any]:
    return {
        # `db` e non `localhost`: Metabase gira dentro Docker e raggiunge
        # PostgreSQL sulla rete di compose, con il nome del servizio.
        "host": "db",
        "port": 5432,
        "dbname": os.environ["POSTGRES_DB"],
        "user": os.environ.get("METABASE_DB_USER", "metabase_lettura"),
        "password": os.environ["METABASE_DB_PASSWORD"],
        # Metabase vede soltanto `marts`. Non `raw`, non `staging`: uno
        # strumento di analisi non ha motivo di guardare i dati sporchi, e
        # nemmeno di sapere che esistono.
        "schema-filters-type": "inclusion",
        "schema-filters-patterns": "marts",
        "ssl": False,
    }


def collega_database(mb: Metabase) -> int:
    esistenti = {d["name"]: d for d in mb.get("/api/database")["data"]}

    if NOME_DATABASE in esistenti:
        id_database = int(esistenti[NOME_DATABASE]["id"])
        mb.put(
            f"/api/database/{id_database}",
            {
                "name": NOME_DATABASE,
                "engine": "postgres",
                "details": _dettagli_connessione(),
            },
        )
        print(f"database già collegato, id {id_database}")
    else:
        creato = mb.post(
            "/api/database",
            {
                "engine": "postgres",
                "name": NOME_DATABASE,
                "details": _dettagli_connessione(),
                "is_full_sync": True,
            },
        )
        id_database = int(creato["id"])
        print(f"database collegato, id {id_database}")

    # Il database di esempio non serve: un progetto con dati veri non tiene in
    # giro quelli finti.
    for database in mb.get("/api/database")["data"]:
        if database["engine"] == "sqlite":
            mb.chiama("DELETE", f"/api/database/{database['id']}")
            print("rimosso il database di esempio")

    return id_database


def sincronizza(mb: Metabase, id_database: int) -> list[str]:
    mb.post(f"/api/database/{id_database}/sync_schema", {})

    tabelle: list[str] = []
    for _ in range(40):
        metadati = mb.get(f"/api/database/{id_database}/metadata")
        tabelle = sorted(t["name"] for t in metadati.get("tables", []))
        if len(tabelle) >= TABELLE_ATTESE:
            return tabelle
        time.sleep(3)

    raise ErroreMetabase(
        f"Metabase vede {len(tabelle)} tabelle invece di {TABELLE_ATTESE}: {tabelle}"
    )


def main() -> int:
    email = os.environ["METABASE_ADMIN_EMAIL"]
    password = os.environ["METABASE_ADMIN_PASSWORD"]

    mb = Metabase()
    print(f"attendo {mb.indirizzo}")
    mb.aspetta()

    try:
        creato = mb.prepara_amministratore(email, password)
    except ErroreMetabase as errore:
        # Metabase rifiuta le password che riconosce come comuni, e risponde
        # con un JSON che parla di «specific-errors». Chi segue il README alla
        # lettera merita di sapere cosa deve cambiare.
        if "too common" in str(errore) or "valid password" in str(errore):
            raise ErroreMetabase(
                "Metabase ha rifiutato METABASE_ADMIN_PASSWORD perché la "
                "considera troppo comune. Scegline una più lunga e meno "
                "prevedibile in .env, poi rilancia."
            ) from errore
        raise

    if creato:
        print(f"creato l'amministratore {email}")
    else:
        print("istanza già configurata")
        mb.entra(email, password)

    id_database = collega_database(mb)
    tabelle = sincronizza(mb, id_database)
    print(f"Metabase vede {len(tabelle)} tabelle in marts: {', '.join(tabelle)}")

    print()
    print("ora: uv run python -m metabase.configura")
    return 0


if __name__ == "__main__":
    sys.exit(main())
