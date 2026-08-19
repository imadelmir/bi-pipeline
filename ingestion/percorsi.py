"""Percorsi dei dati sul disco.

Un posto solo dove sono scritti: `load.py` e `registry.py` leggono gli stessi
valori di `sources/online_retail.py`, e il giorno che una cartella cambia nome
non resta un percorso dimenticato in un modulo.

Tutta `data/` è in `.gitignore`: qui dentro finiscono 43,5 MB di sorgente e i
CSV che ne derivano, che non devono entrare nel repository.
"""

from pathlib import Path

# La radice del progetto: due livelli sopra questo file (ingestion/percorsi.py).
RADICE = Path(__file__).resolve().parent.parent

CARTELLA_DATI = RADICE / "data"

# Il file come arriva da UCI: l'archivio e l'Excel che ne esce.
CARTELLA_GREZZI = CARTELLA_DATI / "grezzi"

# I CSV prodotti dalla conversione, quelli che poi entrano in raw con COPY.
CARTELLA_CSV = CARTELLA_DATI / "csv"


def prepara_cartelle() -> None:
    """Crea le cartelle dei dati se non esistono. Chiamarla non fa danni."""
    for cartella in (CARTELLA_DATI, CARTELLA_GREZZI, CARTELLA_CSV):
        cartella.mkdir(parents=True, exist_ok=True)
