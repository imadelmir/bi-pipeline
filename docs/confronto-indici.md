# Gli indici sul fatto, misurati

Generato da `uv run python -m scripts.confronto_indici` il 20/08/2026 (M4-T8).

Quattro indici, uno per chiave esterna, creati da un `post_hook` di
`fct_vendite`. Su 1.021.137 righe pesano **28 MB**.

Ogni tempo è la mediana di 5 esecuzioni: la prima paga il
riempimento della cache, e una media la lascerebbe pesare su tutte le altre.

| Interrogazione | Senza indici | Con indici | Differenza |
| --- | ---: | ---: | ---: |
| Fatturato per mese, tutti i paesi | 0,197 s | 0,136 s | 1,4 volte |
| Fatturato per mese, solo l'Italia | 0,045 s | 0,003 s | 17,0 volte |

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
Finalize GroupAggregate  (cost=19641.29..19650.95 rows=36 width=40) (actual time=90.444..95.160 rows=21 loops=1)
  Group Key: d.anno, d.mese
  Buffers: shared hit=5797 read=6912
  ->  Gather Merge  (cost=19641.29..19649.69 rows=72 width=40) (actual time=90.418..95.094 rows=41 loops=1)
        Workers Planned: 2
        Workers Launched: 2
        Buffers: shared hit=5797 read=6912
        ->  Sort  (cost=18641.27..18641.36 rows=36 width=40) (actual time=85.573..85.582 rows=14 loops=3)
              Sort Key: d.anno, d.mese
              Sort Method: quicksort  Memory: 26kB
              Buffers: shared hit=5797 read=6912
              Worker 0:  Sort Method: quicksort  Memory: 26kB
              Worker 1:  Sort Method: quicksort  Memory: 26kB
              ->  Partial HashAggregate  (cost=18639.89..18640.34 rows=36 width=40) (actual time=85.507..85.525 rows=14 loops=3)
                  
```

Con gli indici:

```
Sort  (cost=6973.16..6973.25 rows=36 width=40) (actual time=1.811..1.815 rows=21 loops=1)
  Sort Key: d.anno, d.mese
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=55
  ->  HashAggregate  (cost=6971.69..6972.23 rows=36 width=40) (actual time=1.763..1.775 rows=21 loops=1)
        Group Key: d.anno, d.mese
        Batches: 1  Memory Usage: 24kB
        Buffers: shared hit=52
        ->  Hash Join  (cost=33.05..6895.11 rows=10211 width=14) (actual time=0.454..1.359 rows=1470 loops=1)
              Hash Cond: (f.data_key = d.data_key)
              Buffers: shared hit=52
              ->  Nested Loop  (cost=0.42..6722.08 rows=10211 width=10) (actual time=0.059..0.590 rows=1470 loops=1)
                    Buffers: shared hit=36
                    ->  Seq Scan on dim_paese p  (cost=0.00..16.00 rows=2 width=8) (actual time=0.018..0.022 rows=1 loops=1)
                          F
```
