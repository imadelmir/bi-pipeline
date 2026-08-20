"""Costruisce cruscotti e domande su Metabase, da capo e senza clic (M7).

Idempotente: rilanciarlo aggiorna ciò che esiste invece di creare doppioni.
È il motivo per cui esiste — un cruscotto costruito a mano vive su una
macchina sola, e quando quella macchina si perde si perde anche il lavoro.

Uso:

    uv run python -m metabase.configura
    uv run python -m metabase.configura --solo-domande
"""

from __future__ import annotations

import argparse
import io
import os
import sys
import time
from typing import Any

from metabase import aspetto
from metabase.api import ErroreMetabase, Metabase
from metabase.domande import (
    ANNO_PREDEFINITO,
    CRUSCOTTI,
    DOMANDE,
    DOMANDE_PER_CHIAVE,
    Domanda,
    Scheda,
)

for _flusso in (sys.stdout, sys.stderr):
    if isinstance(_flusso, io.TextIOWrapper) and _flusso.encoding.lower() != "utf-8":
        _flusso.reconfigure(encoding="utf-8", errors="replace")

NOME_DATABASE = "BI Pipeline"

# I due filtri comuni a tutte le pagine (M7-T7). Gli identificativi sono
# scritti a mano e non generati: devono restare gli stessi a ogni esecuzione,
# altrimenti i collegamenti con le schede si spezzano.
FILTRI: list[dict[str, Any]] = [
    {
        "id": "f1000001",
        "name": "Anno",
        "slug": "anno",
        "type": "number/=",
        "sectionId": "number",
        "default": [ANNO_PREDEFINITO],
    },
    {
        "id": "f1000002",
        "name": "Paese",
        "slug": "paese",
        "type": "string/=",
        "sectionId": "string",
        "default": ["tutti"],
    },
]


def _database(mb: Metabase) -> int:
    for database in mb.get("/api/database")["data"]:
        if database["name"] == NOME_DATABASE:
            return int(database["id"])
    raise ErroreMetabase(
        f"il database «{NOME_DATABASE}» non è collegato: "
        "esegui prima `uv run python -m metabase.prepara`"
    )


def _corpo_domanda(domanda: Domanda, id_database: int) -> dict[str, Any]:
    return {
        "name": domanda.nome,
        "description": domanda.descrizione,
        "display": domanda.display,
        "visualization_settings": domanda.impostazioni,
        "dataset_query": {
            "type": "native",
            "database": id_database,
            "native": {
                "query": domanda.sql.strip(),
                "template-tags": domanda.tag(),
            },
        },
    }


def sincronizza_domande(mb: Metabase, id_database: int) -> dict[str, int]:
    """Crea o aggiorna ogni domanda. Restituisce chiave → id."""
    esistenti = {c["name"]: c for c in mb.get("/api/card")}
    identificativi: dict[str, int] = {}

    for domanda in DOMANDE:
        corpo = _corpo_domanda(domanda, id_database)
        gia = esistenti.get(domanda.nome)

        if gia is None:
            creata = mb.post("/api/card", corpo)
            identificativi[domanda.chiave] = int(creata["id"])
            print(f"  creata   {domanda.nome}")
        else:
            mb.put(f"/api/card/{gia['id']}", corpo)
            identificativi[domanda.chiave] = int(gia["id"])
            print(f"  aggiornata {domanda.nome}")

    return identificativi


def _mappature(domanda: Domanda, id_card: int) -> list[dict[str, Any]]:
    """Collega i filtri del cruscotto ai parametri della domanda."""
    mappature: list[dict[str, Any]] = []
    tag = domanda.tag()

    for filtro in FILTRI:
        nome = str(filtro["slug"])
        if nome not in tag:
            continue
        mappature.append(
            {
                "parameter_id": filtro["id"],
                "card_id": id_card,
                "target": ["variable", ["template-tag", nome]],
            }
        )
    return mappature


def _scheda(scheda: Scheda, indice: int, domande: dict[str, int]) -> dict[str, Any]:
    """Una scheda del cruscotto: una domanda oppure del testo.

    Gli identificativi negativi dicono a Metabase «questa è nuova»: le schede
    si riscrivono tutte a ogni esecuzione, così la posizione nel file è sempre
    quella sullo schermo.
    """
    comune: dict[str, Any] = {
        "id": -(indice + 1),
        "row": scheda.riga,
        "col": scheda.colonna,
        "size_x": scheda.larghezza,
        "size_y": scheda.altezza,
    }

    if scheda.chiave is None:
        # Scheda di testo: in Metabase è una «carta virtuale», cioè una scheda
        # senza domanda dietro.
        tipo = "heading" if scheda.titolo else "text"
        return {
            **comune,
            "card_id": None,
            "parameter_mappings": [],
            "visualization_settings": {
                "virtual_card": {
                    "name": None,
                    "display": tipo,
                    "visualization_settings": {},
                    "dataset_query": {},
                    "archived": False,
                },
                "text": scheda.testo or "",
                "text.align_vertical": "middle",
                "dashcard.background": not scheda.titolo,
            },
        }

    domanda = DOMANDE_PER_CHIAVE[scheda.chiave]
    id_card = domande[scheda.chiave]
    return {
        **comune,
        "card_id": id_card,
        "parameter_mappings": _mappature(domanda, id_card),
        "visualization_settings": {},
    }


def sincronizza_cruscotti(mb: Metabase, domande: dict[str, int]) -> list[str]:
    esistenti = {d["name"]: d for d in mb.get("/api/dashboard")}
    indirizzi: list[str] = []

    for cruscotto in CRUSCOTTI:
        gia = esistenti.get(cruscotto.nome)
        if gia is None:
            creato = mb.post(
                "/api/dashboard",
                {"name": cruscotto.nome, "description": cruscotto.descrizione},
            )
            id_cruscotto = int(creato["id"])
            print(f"  creato   {cruscotto.nome}")
        else:
            id_cruscotto = int(gia["id"])
            print(f"  aggiorno {cruscotto.nome}")

        schede = [
            _scheda(scheda, indice, domande)
            for indice, scheda in enumerate(cruscotto.schede)
        ]

        mb.put(
            f"/api/dashboard/{id_cruscotto}",
            {
                "name": cruscotto.nome,
                "description": cruscotto.descrizione,
                "parameters": FILTRI,
                "dashcards": schede,
            },
        )
        indirizzi.append(f"{mb.indirizzo}/dashboard/{id_cruscotto}")

    return indirizzi


def verifica(mb: Metabase, domande: dict[str, int]) -> None:
    """Esegue le domande degli indicatori e ne stampa il risultato.

    Serve al criterio di M7-T3: ogni numero mostrato dal cruscotto deve
    coincidere con la stessa interrogazione lanciata sul database.
    """
    print()
    print("i cinque indicatori come li vede Metabase")
    for chiave in (
        "fatturato_netto",
        "ordini",
        "scontrino_medio",
        "tasso_reso",
        "clienti_attivi",
    ):
        risposta = mb.post(f"/api/card/{domande[chiave]}/query", {})
        righe = risposta.get("data", {}).get("rows", [])
        # Le domande degli indicatori restituiscono la serie degli anni: il
        # valore da mostrare è l'ultimo, e sta nella seconda colonna — la
        # prima è il periodo che serve a Metabase per calcolare la variazione.
        valore = righe[-1][1] if righe and len(righe[-1]) > 1 else "—"
        precedente = righe[-2][1] if len(righe) > 1 else None
        confronto = ""
        if precedente not in (None, 0):
            variazione = (float(valore) - float(precedente)) / float(precedente) * 100
            confronto = f"  ({variazione:+.1f} % sull'anno prima)"
        print(f"  {DOMANDE_PER_CHIAVE[chiave].nome:<20} {valore}{confronto}")


def main() -> int:
    lettore = argparse.ArgumentParser(description="Configura domande e cruscotti.")
    lettore.add_argument(
        "--solo-domande",
        action="store_true",
        help="aggiorna le domande senza toccare i cruscotti",
    )
    opzioni = lettore.parse_args()

    mb = Metabase()
    mb.aspetta()
    mb.entra(os.environ["METABASE_ADMIN_EMAIL"], os.environ["METABASE_ADMIN_PASSWORD"])

    aspetto.applica(mb)
    print()

    id_database = _database(mb)
    print(f"database «{NOME_DATABASE}», id {id_database}")

    print("domande")
    domande = sincronizza_domande(mb, id_database)

    if not opzioni.solo_domande:
        print("cruscotti")
        indirizzi = sincronizza_cruscotti(mb, domande)
        print()
        for indirizzo in indirizzi:
            print(f"  {indirizzo}")

    time.sleep(1)
    verifica(mb, domande)
    return 0


if __name__ == "__main__":
    sys.exit(main())
