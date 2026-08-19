/*
    Quante righe sono state escluse, e perché (M3-T10).

    È la contabilità delle esclusioni: un motivo per riga, con il conteggio.
    Da qui nasce il test di quadratura di M5-T7, che verifica

        righe in raw = righe in stg_vendite + somma delle esclusioni

    Se quel conto non torna, delle righe sono sparite senza che nessuno le
    abbia dichiarate — ed è l'unico modo per accorgersene prima che il
    cruscotto mostri un fatturato sbagliato.

    La riga «tenute» c'è di proposito: così la somma della colonna `righe`
    di questo modello dà esattamente le righe della sorgente, e la verifica
    si fa a occhio oltre che con un test.
*/

with classificate as (

    select
        motivo_esclusione,
        quantita,
        prezzo_unitario
    from {{ ref('stg_vendite_classificate') }}

)

select
    coalesce(motivo_esclusione, 'tenute') as motivo,
    motivo_esclusione is null as e_tenuta,
    count(*) as righe,
    -- Il valore che se ne va con le righe escluse. Serve a rispondere alla
    -- domanda che segue sempre l'esclusione: «quanto fatturato ho tolto?».
    round(sum(quantita * prezzo_unitario), 2) as valore
from classificate
group by 1, 2
