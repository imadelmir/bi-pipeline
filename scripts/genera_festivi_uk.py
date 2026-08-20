"""Genera la seed dei giorni festivi del Regno Unito (M4-T1).

Perché generarli invece di scriverli a mano: l'elenco ufficiale di gov.uk
parte dal 2019, e i dati di questo progetto vanno dal 2009 al 2011. Le regole
però sono pubbliche e stabili, quindi si applicano invece di andare a memoria —
che su una tabella di date è il modo più rapido per sbagliare di un giorno e
non accorgersene mai.

Le regole per Inghilterra e Galles:

- Capodanno, Natale e Santo Stefano sono a data fissa. Se cadono di sabato o
  domenica, la festa si sposta al primo giorno feriale libero.
- Venerdì Santo e Lunedì dell'Angelo dipendono dalla Pasqua, calcolata con
  l'algoritmo gregoriano anonimo.
- Early May è il primo lunedì di maggio, Spring l'ultimo di maggio, Summer
  l'ultimo di agosto.
- Il 29 aprile 2011 è una festività straordinaria, concessa per il matrimonio
  reale. È l'unica voce scritta a mano, perché non discende da nessuna regola.

Uso:

    uv run python scripts/genera_festivi_uk.py 2009 2011
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
from datetime import date, timedelta
from pathlib import Path

for _flusso in (sys.stdout, sys.stderr):
    if isinstance(_flusso, io.TextIOWrapper) and _flusso.encoding.lower() != "utf-8":
        _flusso.reconfigure(encoding="utf-8", errors="replace")

RADICE = Path(__file__).resolve().parent.parent
SEED = RADICE / "dbt" / "seeds" / "festivi_regno_unito.csv"

# Festività straordinarie, quelle che nessuna regola prevede.
STRAORDINARIE = {
    date(2011, 4, 29): "Matrimonio reale",
}


def pasqua(anno: int) -> date:
    """Domenica di Pasqua secondo l'algoritmo gregoriano anonimo."""
    a = anno % 19
    b, c = divmod(anno, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    to = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * to) // 451
    mese, giorno = divmod(h + to - 7 * m + 114, 31)
    return date(anno, mese, giorno + 1)


def primo_lunedi(anno: int, mese: int) -> date:
    giorno = date(anno, mese, 1)
    return giorno + timedelta(days=(7 - giorno.weekday()) % 7)


def ultimo_lunedi(anno: int, mese: int) -> date:
    giorno = date(anno, mese + 1, 1) - timedelta(days=1)
    return giorno - timedelta(days=giorno.weekday())


def _sposta(giorno: date, occupati: set[date]) -> date:
    """Sposta al primo giorno feriale libero, se cade nel fine settimana."""
    while giorno.weekday() >= 5 or giorno in occupati:
        giorno += timedelta(days=1)
    return giorno


def festivi(anno: int) -> list[tuple[date, str]]:
    """I giorni festivi di Inghilterra e Galles per un anno."""
    domenica_pasqua = pasqua(anno)
    occupati: set[date] = set()
    elenco: list[tuple[date, str]] = []

    # Prima le feste mobili: cadono sempre in giorni feriali e non si spostano.
    for giorno, nome in (
        (domenica_pasqua - timedelta(days=2), "Venerdì Santo"),
        (domenica_pasqua + timedelta(days=1), "Lunedì dell'Angelo"),
        (primo_lunedi(anno, 5), "Early May Bank Holiday"),
        (ultimo_lunedi(anno, 5), "Spring Bank Holiday"),
        (ultimo_lunedi(anno, 8), "Summer Bank Holiday"),
    ):
        elenco.append((giorno, nome))
        occupati.add(giorno)

    # Poi quelle a data fissa, in due passaggi.
    #
    # Il primo mette al loro posto quelle che cadono già in un giorno feriale,
    # il secondo sposta le altre. L'ordine conta: nel 2011 il 25 dicembre era
    # domenica e il 26 lunedì, quindi Santo Stefano resta al 26 e il Natale
    # slitta al 27. Spostando in un passaggio solo, il Natale si sarebbe preso
    # il 26 e Santo Stefano il 27 — stesse date, nomi scambiati.
    fisse = (
        (date(anno, 1, 1), "Capodanno"),
        (date(anno, 12, 25), "Natale"),
        (date(anno, 12, 26), "Santo Stefano"),
    )

    for giorno, nome in fisse:
        if giorno.weekday() < 5:
            elenco.append((giorno, nome))
            occupati.add(giorno)

    for giorno, nome in fisse:
        if giorno.weekday() >= 5:
            spostato = _sposta(giorno, occupati)
            elenco.append((spostato, f"{nome} (recupero)"))
            occupati.add(spostato)

    for giorno, nome in STRAORDINARIE.items():
        if giorno.year == anno:
            elenco.append((giorno, nome))

    return sorted(elenco)


def main() -> int:
    lettore = argparse.ArgumentParser(description="Genera la seed dei festivi UK.")
    lettore.add_argument("dal", type=int)
    lettore.add_argument("al", type=int)
    opzioni = lettore.parse_args()

    righe = [
        (giorno.isoformat(), nome)
        for anno in range(opzioni.dal, opzioni.al + 1)
        for giorno, nome in festivi(anno)
    ]

    with SEED.open("w", encoding="utf-8", newline="") as file:
        scrittore = csv.writer(file, lineterminator="\n")
        scrittore.writerow(["data", "nome_festivo"])
        scrittore.writerows(righe)

    for data_iso, nome in righe:
        giorno = date.fromisoformat(data_iso)
        print(f"{data_iso}  {giorno.strftime('%a')}  {nome}")
    print(f"\nscritte {len(righe)} righe in {SEED}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
