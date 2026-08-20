"""L'aspetto dell'istanza: quello che l'edizione open source lascia cambiare (M7).

**Font e colori dell'interfaccia non sono modificabili.** Sono dietro la
funzionalità `whitelabel`, che nell'edizione open source non c'è: un
`PUT /api/setting/application-font` risponde 500 dicendolo. Provarlo e
riportare l'esito è più utile che fingere di non saperlo — e chi un domani
avesse una licenza trova qui le impostazioni già scritte.

Resta però tutto quello che conta davvero per la leggibilità, e che in
Metabase si imposta **per colonna e per scheda**: valuta, separatori delle
migliaia, percentuali, forma compatta dei numeri grandi, colori delle serie,
etichette degli assi. È in `metabase/domande.py`, accanto a ogni domanda.

Qui restano le impostazioni globali che l'edizione open source accetta: fuso
orario, primo giorno della settimana, lingua, formati predefiniti di date e
numeri.
"""

from __future__ import annotations

import io
import os
import sys

from metabase.api import Metabase

for _flusso in (sys.stdout, sys.stderr):
    if isinstance(_flusso, io.TextIOWrapper) and _flusso.encoding.lower() != "utf-8":
        _flusso.reconfigure(encoding="utf-8", errors="replace")

# La tavolozza del mockup. I nomi delle chiavi sono quelli di Metabase.
COLORI = {
    "brand": "#509EE3",  # blu marchio: serie principale, elementi attivi
    "summarize": "#88BF4D",  # verde: valori positivi
    "filter": "#A989C5",  # viola: seconda serie, anno precedente
    "accent0": "#509EE3",
    "accent1": "#A989C5",
    "accent2": "#88BF4D",
    "accent3": "#F9CF48",  # giallo: avvisi e soglie
    "accent4": "#EF8C8C",  # salmone: resi e variazioni negative
    "accent5": "#2E353B",  # grafite
    "accent6": "#7C868D",
    "accent7": "#C4CCD2",
    "text-dark": "#2E353B",
    "text-medium": "#7C868D",
    "text-light": "#A7B0B7",
}

# Quelle che l'edizione open source accetta.
IMPOSTAZIONI: dict[str, object] = {
    # Formati predefiniti di date e numeri: valgono ovunque non sia detto
    # altrimenti, e risparmiano di ripetersi su ogni colonna.
    "custom-formatting": {
        "type/Temporal": {"date_style": "D/M/YYYY", "date_separator": "/"},
        "type/Number": {
            "number_separators": ".,",
        },
        "type/Currency": {
            "currency": "GBP",
            "currency_style": "symbol",
            "currency_in_header": False,
        },
    },
    # La settimana comincia di lunedì: è un grossista europeo, e con la
    # domenica in testa i raggruppamenti settimanali spostano il fine
    # settimana a cavallo di due righe.
    "start-of-week": "monday",
    "report-timezone": "Europe/Rome",
    "site-locale": "it",
}

# Quelle che richiedono una licenza a pagamento. Si provano lo stesso, e
# l'esito finisce a schermo: è una riga di documentazione che si aggiorna da
# sola il giorno che l'istanza cambia edizione.
SOLO_A_PAGAMENTO: dict[str, object] = {
    "application-name": "BI Pipeline",
    "application-font": "Inter",
    "application-colors": COLORI,
    "show-metabot": False,
    "loading-message": "running-query",
}


def _prova(mb: Metabase, chiave: str, valore: object) -> bool:
    try:
        mb.put(f"/api/setting/{chiave}", {"value": valore})
    except Exception as errore:  # l'API risponde 500 se la funzione non c'è
        if "whitelabel" in str(errore):
            return False
        raise
    return True


def applica(mb: Metabase) -> None:
    print("impostazioni applicate")
    for chiave, valore in IMPOSTAZIONI.items():
        _prova(mb, chiave, valore)
        mostrato = valore if not isinstance(valore, dict) else "…"
        print(f"  {chiave:<22} {mostrato}")

    print()
    print("non disponibili in questa edizione (richiedono whitelabel)")
    for chiave, valore in SOLO_A_PAGAMENTO.items():
        esito = "applicata" if _prova(mb, chiave, valore) else "rifiutata"
        print(f"  {chiave:<22} {esito}")


def main() -> int:
    mb = Metabase()
    mb.aspetta()
    mb.entra(os.environ["METABASE_ADMIN_EMAIL"], os.environ["METABASE_ADMIN_PASSWORD"])
    print("aspetto")
    applica(mb)
    return 0


if __name__ == "__main__":
    sys.exit(main())
