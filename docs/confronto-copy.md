# COPY contro `pandas.to_sql`

Generato da `uv run python -m ingestion.confronto_copy` il 20/08/2026 (M2-T6).

Stesse **100.000 righe**, stesso database, stesso momento. La lettura
del CSV è fuori dal cronometro: si misura la scrittura verso PostgreSQL.

| Metodo | Secondi | Righe al secondo |
| --- | --- | --- |
| `COPY` (psycopg) | **0.17** | 588.756 |
| `pandas.to_sql` (SQLAlchemy) | **2.99** | 33.467 |

**`COPY` è 17.6 volte più veloce.**

Proiettato sul milione di righe del dataset: circa
2 secondi contro
32.

## Perché

`to_sql` traduce ogni riga in un'istruzione `INSERT`: il server la riceve, la
analizza, la pianifica e la esegue, una per una. `COPY` apre un flusso e ci
scrive dentro il blocco di righe: nessuna istruzione da analizzare, nessun
piano da costruire, e il server scrive direttamente nelle pagine della tabella.

La differenza non è di configurazione: sono due protocolli diversi. Ed è il
motivo per cui l'ingestione di questo progetto usa `COPY` (M2-T5) e non la
scorciatoia di una riga di pandas.
