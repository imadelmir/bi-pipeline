"""I formati delle colonne, in un posto solo.

Un cruscotto si giudica in tre secondi, e in quei tre secondi la differenza fra
`9014102.19` e `£ 9,0 Mln` è tutta. Metabase sa formattare, ma va detto colonna
per colonna: queste funzioni evitano di ripetere lo stesso dizionario quindici
volte, e soprattutto di scrivere la valuta sbagliata in una scheda sola.

Le chiavi hanno la forma che vuole Metabase: la stringa JSON di
`["name", "<nome della colonna>"]`.
"""

from __future__ import annotations

import json
from typing import Any

# La tavolozza del mockup. Una serie sola è blu: due serie blu non si leggono.
BLU = "#509EE3"
VIOLA = "#A989C5"
VERDE = "#88BF4D"
GIALLO = "#F9CF48"
SALMONE = "#EF8C8C"
GRAFITE = "#2E353B"


def _chiave(colonna: str) -> str:
    return json.dumps(["name", colonna], separators=(",", ":"))


def sterline(colonna: str, decimali: int = 0, compatto: bool = False) -> dict[str, Any]:
    """Importi in sterline. Zero decimali sui totali: le cifre contano.

    `compatto` accorcia i numeri grandi (9,0 Mln): serve nei numeri singoli,
    dove il valore è enorme e lo spazio poco. Nelle tabelle no — lì i valori si
    leggono e si confrontano, e un arrotondamento nasconde le differenze.
    """
    return {
        _chiave(colonna): {
            "number_style": "currency",
            "currency": "GBP",
            "currency_style": "symbol",
            "currency_in_header": False,
            "decimals": decimali,
            "compact": compatto,
        }
    }


def percentuale(colonna: str, decimali: int = 2) -> dict[str, Any]:
    """Percentuali già moltiplicate per cento: si aggiunge il simbolo.

    Non si usa `number_style: percent`, che moltiplicherebbe una seconda volta
    e mostrerebbe 482 % al posto di 4,82 %.
    """
    return {_chiave(colonna): {"decimals": decimali, "suffix": " %"}}


def intero(colonna: str) -> dict[str, Any]:
    return {_chiave(colonna): {"decimals": 0}}


def unisci(*dizionari: dict[str, Any]) -> dict[str, Any]:
    risultato: dict[str, Any] = {}
    for dizionario in dizionari:
        risultato.update(dizionario)
    return risultato
