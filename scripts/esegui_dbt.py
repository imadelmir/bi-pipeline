"""Avvia dbt senza passare dall'eseguibile generato nella venv.

Su questa macchina Windows il criterio di controllo delle applicazioni blocca
gli `.exe` che pip e uv generano dentro `.venv/Scripts/`: `dbt` risponde
«os error 4551» e non parte. Il pacchetto però è installato e funziona: basta
chiamarne la funzione di ingresso invece dello shim.

`python -m dbt.cli.main` funzionerebbe, ma stampa un avviso di runpy a ogni
esecuzione. Importare `cli` e chiamarla è la stessa cosa, in silenzio.

Il file non può chiamarsi `dbt.py`: la cartella dello script finisce in testa
a `sys.path`, e `import dbt` troverebbe questo file invece del pacchetto.

Uso — identico a dbt, con gli stessi argomenti:

    uv run python scripts/esegui_dbt.py debug
    uv run python scripts/esegui_dbt.py build --target prod
"""

from __future__ import annotations

from dbt.cli.main import cli

if __name__ == "__main__":
    cli()
