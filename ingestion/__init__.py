"""Ingestione: scaricamento, verifica del checksum e caricamento in raw."""

import io
import sys

# Su Windows, quando l'uscita finisce in una pipe o in un file, Python usa la
# codifica di sistema (cp1252) invece di UTF-8: le accentate diventano punti
# interrogativi proprio nei messaggi d'errore, che sono quelli che si finisce
# per incollare da qualche parte. Tre righe qui evitano di doverci pensare in
# ogni modulo.
for _flusso in (sys.stdout, sys.stderr):
    if isinstance(_flusso, io.TextIOWrapper) and _flusso.encoding.lower() != "utf-8":
        _flusso.reconfigure(encoding="utf-8", errors="replace")
