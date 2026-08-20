{{
    config(
        materialized='incremental',
        unique_key='data_key',
        incremental_strategy='delete+insert',
        post_hook=[
            "create index if not exists ix_fct_vendite_data on {{ this }} (data_key)",
            "create index if not exists ix_fct_vendite_prodotto on {{ this }} (prodotto_key)",
            "create index if not exists ix_fct_vendite_cliente on {{ this }} (cliente_key)",
            "create index if not exists ix_fct_vendite_paese on {{ this }} (paese_key)",
        ]
    )
}}

/*
    Il fatto: una riga per riga di fattura (M4-T5, M4-T6, M4-T7).

    Grana: un prodotto, su una fattura, in un istante. È la più fine
    disponibile, e da lì si aggrega verso l'alto senza dover mai tornare alla
    sorgente.

    **Incrementale, per giorno.** `is_incremental()` limita la lettura ai
    giorni dall'ultimo caricato in poi; `delete+insert` su `data_key` cancella
    quei giorni prima di riscriverli. Rilanciare non duplica, e il totale resta
    identico a una ricostruzione completa — verificato in M4-T6.

    Non è una scelta di eleganza: senza, ogni esecuzione riscriverebbe un
    milione di righe per aggiungerne poche. Con dati fermi al 2011 la
    differenza si vede poco; con una sorgente che cresce ogni notte è la
    differenza fra due secondi e dieci minuti.

    **I resi restano**, con quantità e valore negativi. Toglierli
    significherebbe buttare via uno dei cinque indicatori.
*/

-- Dipendenza dichiarata a mano perché il fatto **non legge** `dim_data`: la
-- chiave del giorno la calcola (`to_char(data_ora, 'YYYYMMDD')`), che evita un
-- join da un milione di righe per ottenere un numero che si ricava dalla data.
-- Senza questa riga dbt non saprebbe che le due tabelle sono legate: il grafo
-- mostrerebbe una stella con un braccio staccato, e potrebbe costruire il fatto
-- prima del calendario a cui il test `relationships` lo confronta.
-- depends_on: {{ ref('dim_data') }}

with vendite as (

    select
        numero_fattura,
        codice_prodotto,
        codice_cliente,
        paese,
        data_ora,
        quantita,
        prezzo_unitario,
        valore,
        is_reso
    from {{ ref('stg_vendite') }}

    {% if is_incremental() %}
    -- Si riparte dall'ultimo giorno già presente, non dal successivo: quel
    -- giorno potrebbe essere stato caricato a metà, e `delete+insert` lo
    -- riscrive per intero.
    where data_ora >= (
        select coalesce(max(data_key)::text::date, '1900-01-01'::date) from {{ this }}
    )
    {% endif %}

)

select
    to_char(v.data_ora, 'YYYYMMDD')::integer as data_key,
    p.prodotto_key,
    -- Le vendite senza cliente puntano al membro Sconosciuto, chiave -1:
    -- sono vendite vere e devono restare nel fatturato.
    coalesce(c.cliente_key, -1) as cliente_key,
    n.paese_key,

    -- Dimensione degenere: il numero di fattura sta nel fatto e non ha una
    -- tabella propria. Una `dim_fattura` conterrebbe solo la chiave e
    -- nient'altro — un join in più per zero informazione.
    v.numero_fattura,

    v.quantita,
    v.prezzo_unitario,
    v.valore,
    v.is_reso,

    -- L'istante resta nel fatto accanto alla chiave del giorno: serve a
    -- ordinare le righe di una fattura e a rispondere sulle fasce orarie,
    -- cose che `dim_data` non sa fare.
    v.data_ora

from vendite as v
inner join {{ ref('dim_prodotto') }} as p
    on v.codice_prodotto = p.codice_prodotto
inner join {{ ref('dim_paese') }} as n
    on v.paese = n.paese_sorgente
left join {{ ref('dim_cliente') }} as c
    on v.codice_cliente = c.codice_cliente
