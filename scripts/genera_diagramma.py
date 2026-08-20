"""Disegna il diagramma dello schema a stella (M4-T10).

Il diagramma si genera da uno script e non si disegna a mano: quando una
colonna cambia, si aggiorna una riga di codice e si rilancia. Un'immagine
disegnata in un editor invece invecchia in silenzio, e nel case study finisce
per raccontare uno schema che non esiste più.

I conteggi delle righe non sono scritti nel codice: si leggono dal database,
così l'immagine dice quanto c'è davvero. Se il database non è raggiungibile,
il diagramma esce comunque, con i valori attesi dal piano.

Produce `docs/schema-a-stella.png` (per il case study) e `.svg` (per il
repository: si apre nel browser, si legge nei diff, non sfoca ingrandendo).

Uso:

    uv run python -m scripts.genera_diagramma
"""

from __future__ import annotations

import io
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # nessuna finestra: si scrive su file e basta

import matplotlib.patches as patches
import matplotlib.pyplot as plt
from matplotlib.axes import Axes

from ingestion.formato import numero

for _flusso in (sys.stdout, sys.stderr):
    if isinstance(_flusso, io.TextIOWrapper) and _flusso.encoding.lower() != "utf-8":
        _flusso.reconfigure(encoding="utf-8", errors="replace")

RADICE = Path(__file__).resolve().parent.parent
USCITA = RADICE / "docs" / "schema-a-stella"

# La tavolozza del mockup: blu marchio per il fatto, grafite per il testo.
BLU = "#509EE3"
GRAFITE = "#2E353B"
GRIGIO = "#7C868D"
FILO = "#C4CCD2"
FONDO = "#FFFFFF"
CHIARO = "#F1F7FC"

# Misure verticali, in unità del disegno. L'altezza di un riquadro si calcola
# da queste invece di essere scritta a mano: altrimenti ci si accorge che il
# testo esce dal bordo solo guardando l'immagine finita, e di solito tardi.
ALTEZZA_TITOLO = 0.62
ALTEZZA_RIGA = 0.34
ALTEZZA_SOTTOTITOLO = 0.52


@dataclass(frozen=True)
class Riquadro:
    """Una tabella disegnata, con i bordi a cui attaccare le linee."""

    sinistra: float
    destra: float
    sotto: float
    sopra: float
    centro_x: float
    centro_y: float


def conteggi() -> dict[str, int]:
    """Le righe di ogni tabella. Vuoto se il database non risponde."""
    try:
        from ingestion.db import connessione

        tabelle = (
            "dim_data",
            "dim_prodotto",
            "dim_cliente",
            "dim_paese",
            "fct_vendite",
        )
        with connessione() as conn, conn.cursor() as cur:
            risultato: dict[str, int] = {}
            for tabella in tabelle:
                cur.execute(f"select count(*) from marts.{tabella}")
                riga = cur.fetchone()
                risultato[tabella] = 0 if riga is None else int(riga[0])
            return risultato
    except Exception as errore:
        print(
            f"database non raggiungibile ({errore.__class__.__name__}): "
            "il diagramma esce con i valori attesi dal piano"
        )
        return {}


def _riquadro(
    ax: Axes,
    centro_x: float,
    centro_y: float,
    larghezza: float,
    titolo: str,
    colonne: list[str],
    sottotitolo: str,
    colore: str,
    e_fatto: bool = False,
) -> Riquadro:
    """Disegna una tabella e restituisce i suoi bordi.

    L'altezza dipende da quante colonne contiene: aggiungerne una non fa
    finire il testo sopra il bordo.
    """
    altezza = ALTEZZA_TITOLO + len(colonne) * ALTEZZA_RIGA + ALTEZZA_SOTTOTITOLO
    sinistra = centro_x - larghezza / 2
    sotto = centro_y - altezza / 2
    cima = sotto + altezza

    ax.add_patch(
        patches.FancyBboxPatch(
            (sinistra, sotto),
            larghezza,
            altezza,
            boxstyle="round,pad=0.02,rounding_size=0.14",
            linewidth=2.4 if e_fatto else 1.4,
            edgecolor=colore,
            facecolor=CHIARO if e_fatto else FONDO,
            zorder=3,
        )
    )

    ax.text(
        centro_x,
        cima - ALTEZZA_TITOLO / 2,
        titolo,
        ha="center",
        va="center",
        fontsize=14 if e_fatto else 12,
        fontweight="bold",
        color=colore,
        zorder=4,
    )

    for indice, colonna in enumerate(colonne):
        ax.text(
            sinistra + 0.26,
            cima - ALTEZZA_TITOLO - (indice + 0.5) * ALTEZZA_RIGA,
            colonna,
            ha="left",
            va="center",
            fontsize=9.6,
            color=GRAFITE,
            zorder=4,
        )

    ax.text(
        centro_x,
        sotto + ALTEZZA_SOTTOTITOLO / 2,
        sottotitolo,
        ha="center",
        va="center",
        fontsize=8.8,
        color=GRIGIO,
        style="italic",
        zorder=4,
    )

    return Riquadro(sinistra, sinistra + larghezza, sotto, cima, centro_x, centro_y)


def _collega(ax: Axes, da: tuple[float, float], a: tuple[float, float]) -> None:
    ax.annotate(
        "",
        xy=a,
        xytext=da,
        arrowprops={"arrowstyle": "-", "color": FILO, "linewidth": 1.5},
        zorder=2,
    )
    ax.text(
        (da[0] + a[0]) / 2,
        (da[1] + a[1]) / 2,
        "1 : N",
        ha="center",
        va="center",
        fontsize=8.4,
        color=GRIGIO,
        bbox={"facecolor": FONDO, "edgecolor": "none", "pad": 2.0},
        zorder=4,
    )


def disegna(righe: dict[str, int]) -> None:
    def quante(tabella: str, attese: str) -> str:
        return f"{numero(righe[tabella])} righe" if tabella in righe else attese

    figura, ax = plt.subplots(figsize=(14, 11))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 11)
    ax.axis("off")
    figura.patch.set_facecolor(FONDO)

    fatto = _riquadro(
        ax,
        7.0,
        5.2,
        4.9,
        "fct_vendite",
        [
            "data_key · prodotto_key",
            "cliente_key · paese_key",
            "numero_fattura   (dim. degenere)",
            "quantita · prezzo_unitario",
            "valore · is_reso · data_ora",
        ],
        f"{quante('fct_vendite', '~1.000.000 righe')} · una riga di fattura",
        BLU,
        e_fatto=True,
    )

    data = _riquadro(
        ax,
        7.0,
        8.35,
        4.6,
        "dim_data",
        [
            "data_key  (PK)",
            "anno · trimestre · mese",
            "settimana · giorno_settimana",
            "is_weekend · is_festivo · is_lavorativo",
        ],
        f"{quante('dim_data', '~740 righe')} · generata, non letta",
        GRAFITE,
    )

    prodotto = _riquadro(
        ax,
        2.3,
        5.2,
        4.2,
        "dim_prodotto",
        [
            "prodotto_key  (PK)",
            "codice_prodotto",
            "descrizione",
            "prima_vendita · ultima_vendita",
            "prezzo_medio · pezzi_venduti",
        ],
        quante("dim_prodotto", "~5.000 righe"),
        GRAFITE,
    )

    cliente = _riquadro(
        ax,
        11.7,
        5.2,
        4.2,
        "dim_cliente",
        [
            "cliente_key  (PK)",
            "codice_cliente",
            "paese_principale · ordini",
            "prima_fattura · ultima_fattura",
            "is_sconosciuto",
        ],
        f"{quante('dim_cliente', '~6.000 righe')} · Sconosciuto = -1",
        GRAFITE,
    )

    paese = _riquadro(
        ax,
        7.0,
        1.75,
        4.6,
        "dim_paese",
        [
            "paese_key  (PK)",
            "paese_sorgente → nome",
            "macro_area · is_regno_unito",
        ],
        f"{quante('dim_paese', '~40 righe')} · non sono negozi",
        GRAFITE,
    )

    _collega(ax, (data.centro_x, data.sotto), (fatto.centro_x, fatto.sopra))
    _collega(ax, (prodotto.destra, prodotto.centro_y), (fatto.sinistra, fatto.centro_y))
    _collega(ax, (cliente.sinistra, cliente.centro_y), (fatto.destra, fatto.centro_y))
    _collega(ax, (paese.centro_x, paese.sopra), (fatto.centro_x, fatto.sotto))

    ax.text(
        0.2,
        10.62,
        "BI Pipeline — schema a stella",
        fontsize=16,
        fontweight="bold",
        color=GRAFITE,
    )
    ax.text(
        0.2,
        10.24,
        "Un fatto, quattro dimensioni, chiavi surrogate.",
        fontsize=10,
        color=GRIGIO,
    )
    ax.text(
        0.2,
        9.94,
        "La fattura sta dentro il fatto: una dim_fattura sarebbe un join in più "
        "per zero informazione.",
        fontsize=10,
        color=GRIGIO,
    )
    ax.text(
        13.8,
        0.18,
        "Online Retail II · UCI Machine Learning Repository · CC BY 4.0",
        fontsize=8.2,
        color=GRIGIO,
        ha="right",
    )

    for estensione in ("png", "svg"):
        percorso = USCITA.with_suffix(f".{estensione}")
        figura.savefig(percorso, dpi=200, bbox_inches="tight", facecolor=FONDO)
        print(f"scritto {percorso}")
    plt.close(figura)


def main() -> int:
    disegna(conteggi())
    return 0


if __name__ == "__main__":
    sys.exit(main())
