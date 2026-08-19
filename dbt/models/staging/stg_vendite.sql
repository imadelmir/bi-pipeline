/*
    Le righe di vendita pulite (M3-T4 … M3-T9).

    È `stg_vendite_classificate` senza le righe escluse, più una descrizione
    sola per prodotto. Nessun join fra sorgenti diverse: è la regola dello
    strato, e i join veri cominciano in marts.

    I resi restano, marcati `is_reso`. Le righe senza cliente restano, con
    `codice_cliente` nullo: sono un quarto del dataset e sono vendite vere.
*/

with tenute as (

    select
        numero_fattura,
        codice_prodotto,
        descrizione_normalizzata,
        quantita,
        data_ora,
        prezzo_unitario,
        codice_cliente,
        paese,
        is_reso,
        caricato_il,
        file_origine
    from {{ ref('stg_vendite_classificate') }}
    where motivo_esclusione is null

),

descrizione_per_codice as (

    /*
        Lo stesso codice compare con descrizioni diverse: errori di battitura,
        abbreviazioni, maiuscole. Si tiene la più frequente (M3-T9).

        `mode()` sceglie il valore più ricorrente; a parità vince il primo in
        ordine alfabetico, che è arbitrario ma stabile — e la stabilità qui
        conta più della scelta: senza, la stessa esecuzione su due macchine
        potrebbe dare due anagrafiche diverse.
    */
    select
        codice_prodotto,
        mode() within group (order by descrizione_normalizzata)
            as descrizione
    from tenute
    where descrizione_normalizzata is not null
    group by codice_prodotto

)

select
    t.numero_fattura,
    t.codice_prodotto,
    -- Se un codice non ha mai avuto una descrizione, resta nullo: inventare
    -- un'etichetta qui vorrebbe dire nasconderlo.
    d.descrizione,
    t.quantita,
    t.data_ora,
    t.prezzo_unitario,
    -- Il valore della riga, che è quello che si somma per il fatturato.
    -- Negativo sui resi, di proposito.
    round(t.quantita * t.prezzo_unitario, 2) as valore,
    t.codice_cliente,
    t.paese,
    t.is_reso,
    t.caricato_il,
    t.file_origine

from tenute as t
left join descrizione_per_codice as d
    on t.codice_prodotto = d.codice_prodotto
