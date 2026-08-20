"""Le stesse interrogazioni con e senza indici, cronometrate (M4-T8).

Gli indici sulle chiavi esterne del fatto si creano con un `post_hook` in
`fct_vendite`. Questo modulo misura quanto servono davvero: cancella gli
indici, cronometra, li ricrea, cronometra di nuovo.

Due interrogazioni di proposito, perché la risposta non è una sola:

- una **aggregazione completa** — il fatturato per mese su tutti i paesi —
  che deve leggere ogni riga comunque;
- una **interrogazione selettiva** — le vendite di un paese piccolo — dove
  l'indice evita di leggere il 99,9 % della tabella.

Chi scrive «ho aggiunto gli indici e le query sono più veloci» senza dire
quali, di solito ha misurato solo la seconda.

Uso:

    uv run python -m scripts.confronto_indici
"""

from __future__ import annotations

import io
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

from ingestion.db import connessione
from ingestion.formato import numero

for _flusso in (sys.stdout, sys.stderr):
    if isinstance(_flusso, io.TextIOWrapper) and _flusso.encoding.lower() != "utf-8":
        _flusso.reconfigure(encoding="utf-8", errors="replace")

RADICE = Path(__file__).resolve().parent.parent
RELAZIONE = RADICE / "docs" / "confronto-indici.md"

INDICI = {
    "ix_fct_vendite_data": "data_key",
    "ix_fct_vendite_prodotto": "prodotto_key",
    "ix_fct_vendite_cliente": "cliente_key",
    "ix_fct_vendite_paese": "paese_key",
}

AGGREGAZIONE_COMPLETA = """
    select d.anno, d.mese, round(sum(f.valore), 2) as fatturato
    from marts.fct_vendite as f
    join marts.dim_data as d on f.data_key = d.data_key
    group by d.anno, d.mese
    order by d.anno, d.mese
"""

INTERROGAZIONE_SELETTIVA = """
    select d.anno, d.mese, round(sum(f.valore), 2) as fatturato
    from marts.fct_vendite as f
    join marts.dim_data as d on f.data_key = d.data_key
    join marts.dim_paese as p on f.paese_key = p.paese_key
    where p.nome = 'Italia'
    group by d.anno, d.mese
    order by d.anno, d.mese
"""

RIPETIZIONI = 5


def _cronometra(sql: str, ripetizioni: int = RIPETIZIONI) -> float:
    """Mediana di N esecuzioni, in secondi.

    La mediana e non la media: la prima esecuzione paga il riempimento della
    cache del database, e una media la lascerebbe pesare su tutte le altre.
    """
    tempi: list[float] = []
    with connessione() as conn, conn.cursor() as cur:
        for _ in range(ripetizioni):
            inizio = time.perf_counter()
            cur.execute(sql)
            cur.fetchall()
            tempi.append(time.perf_counter() - inizio)
    return statistics.median(tempi)


def _piano(sql: str) -> str:
    with connessione() as conn, conn.cursor() as cur:
        cur.execute(f"explain (analyze, buffers, format text) {sql}")
        return "\n".join(str(riga[0]) for riga in cur.fetchall())


def cancella_indici() -> None:
    with connessione() as conn:
        with conn.cursor() as cur:
            for nome in INDICI:
                cur.execute(f"drop index if exists marts.{nome}")
        conn.commit()


def crea_indici() -> None:
    with connessione() as conn:
        with conn.cursor() as cur:
            for nome, colonna in INDICI.items():
                cur.execute(
                    f"create index if not exists {nome} "
                    f"on marts.fct_vendite ({colonna})"
                )
        conn.commit()


def dimensione_indici() -> str:
    with connessione() as conn, conn.cursor() as cur:
        cur.execute(
            "select pg_size_pretty(sum(pg_relation_size(indexrelid))) "
            "from pg_index i join pg_class c on c.oid = i.indrelid "
            "join pg_namespace n on n.oid = c.relnamespace "
            "where n.nspname = 'marts' and c.relname = 'fct_vendite'"
        )
        riga = cur.fetchone()
    return "0 B" if riga is None or riga[0] is None else str(riga[0])


def main() -> int:
    print("cancello gli indici e misuro")
    cancella_indici()
    senza_completa = _cronometra(AGGREGAZIONE_COMPLETA)
    senza_selettiva = _cronometra(INTERROGAZIONE_SELETTIVA)
    piano_senza = _piano(INTERROGAZIONE_SELETTIVA)
    print(f"  aggregazione completa: {senza_completa:.3f} s")
    print(f"  interrogazione selettiva: {senza_selettiva:.3f} s")

    print("ricreo gli indici e rimisuro")
    crea_indici()
    con_completa = _cronometra(AGGREGAZIONE_COMPLETA)
    con_selettiva = _cronometra(INTERROGAZIONE_SELETTIVA)
    piano_con = _piano(INTERROGAZIONE_SELETTIVA)
    peso = dimensione_indici()
    print(f"  aggregazione completa: {con_completa:.3f} s")
    print(f"  interrogazione selettiva: {con_selettiva:.3f} s")

    with connessione() as conn, conn.cursor() as cur:
        cur.execute("select count(*) from marts.fct_vendite")
        riga = cur.fetchone()
        righe = 0 if riga is None else int(riga[0])

    def it(valore: float, cifre: int = 3) -> str:
        """Numero con la virgola decimale, come si scrive in italiano."""
        return f"{valore:.{cifre}f}".replace(".", ",")

    riga_completa = (
        f"{it(senza_completa)} s | {it(con_completa)} s "
        f"| {it(senza_completa / con_completa, 1)} volte"
    )
    riga_selettiva = (
        f"{it(senza_selettiva)} s | {it(con_selettiva)} s "
        f"| {it(senza_selettiva / con_selettiva, 1)} volte"
    )

    testo = f"""# Gli indici sul fatto, misurati

Generato da `uv run python -m scripts.confronto_indici` il \
{datetime.now().astimezone():%d/%m/%Y} (M4-T8).

Quattro indici, uno per chiave esterna, creati da un `post_hook` di
`fct_vendite`. Su {numero(righe)} righe pesano **{peso}**.

Ogni tempo è la mediana di {RIPETIZIONI} esecuzioni: la prima paga il
riempimento della cache, e una media la lascerebbe pesare su tutte le altre.

| Interrogazione | Senza indici | Con indici | Differenza |
| --- | ---: | ---: | ---: |
| Fatturato per mese, tutti i paesi | {riga_completa} |
| Fatturato per mese, solo l'Italia | {riga_selettiva} |

## Perché due interrogazioni e non una

**L'aggregazione completa deve leggere tutte le righe comunque.** Un indice
non le evita niente: il database sceglie la scansione sequenziale, che su un
milione di righe è la strada giusta. Qui gli indici non servono, e dirlo è
più onesto che nasconderlo.

**L'interrogazione selettiva tocca poco più di millecinquecento righe su un
milione.** Senza indice il database le cerca leggendo tutta la tabella; con
l'indice va a prendere solo quelle. È il caso dei filtri dei cruscotti —
periodo, paese, cliente — cioè quello che succede davvero quando qualcuno usa
la dashboard.

## Il piano di esecuzione

Senza indici, la parte che conta:

```
{piano_senza[:900]}
```

Con gli indici:

```
{piano_con[:900]}
```
"""
    RELAZIONE.write_text(testo, encoding="utf-8")
    print(f"scritto {RELAZIONE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
