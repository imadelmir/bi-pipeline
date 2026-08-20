/*
    La quadratura dei totali (M5-T7) — il test che quasi nessuno scrive.

        righe in raw = righe in fct_vendite + esclusioni dichiarate

    È l'unico controllo che si accorge se delle righe spariscono lungo la
    strada. Tutti gli altri test verificano che ciò che è arrivato sia sano;
    questo verifica che sia arrivato tutto. Un join sbagliato, un filtro di
    troppo, una dimensione incompleta: il fatturato cala e nessuno se ne
    accorge, perché un numero più piccolo non ha l'aria di un errore.

    Il confronto è in due parti, e la seconda vale solo su `prod`:

    1. **le righe tenute in staging finiscono tutte nel fatto.** Vale su
       entrambi i target: se un join di `fct_vendite` perdesse righe, la
       differenza salterebbe fuori qui;
    2. **la somma di `stg_esclusioni` corrisponde alle righe di `raw`.**
       Su `dev` non può valere: il target taglia il periodo a tre mesi mentre
       `raw` contiene tutto, e pretenderlo renderebbe il test rosso per
       costruzione — cioè inutile.
*/

with conteggi as (

    select
        (select count(*) from {{ ref('fct_vendite') }}) as righe_fatto,
        (select righe from {{ ref('stg_esclusioni') }} where e_tenuta) as righe_tenute,
        (select sum(righe) from {{ ref('stg_esclusioni') }}) as righe_classificate,
        (select count(*) from {{ source('raw', 'vendite') }}) as righe_raw

),

verifiche as (

    select
        'il fatto perde righe rispetto a staging' as controllo,
        righe_tenute as atteso,
        righe_fatto as trovato
    from conteggi
    where righe_fatto <> righe_tenute

    {% if target.name == 'prod' %}
    union all

    select
        'la somma delle esclusioni non torna con raw' as controllo,
        righe_raw as atteso,
        righe_classificate as trovato
    from conteggi
    where righe_classificate <> righe_raw
    {% endif %}

)

select
    controllo,
    atteso,
    trovato,
    atteso - trovato as differenza
from verifiche
