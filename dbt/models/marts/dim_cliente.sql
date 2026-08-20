/*
    Anagrafica dei clienti, con il membro *Sconosciuto* (M4-T3).

    Il 22 % delle righe non ha un codice cliente. Non è un caso limite ed è la
    ragione per cui questa tabella ha una riga in più: se quelle vendite
    venissero buttate, il fatturato perderebbe un quinto abbondante di sé
    stesso; se puntassero a `NULL`, sparirebbero al primo join interno.

    Puntano invece a una riga vera, con chiave `-1`. Gli indicatori che
    contano i clienti la escludono per nome (M7-T3): includerla la conterebbe
    come un cliente solo, sbagliando in difetto.
*/

with vendite as (

    select
        codice_cliente,
        paese,
        numero_fattura,
        data_ora,
        valore,
        is_reso
    from {{ ref('stg_vendite') }}
    where codice_cliente is not null

),

per_cliente as (

    select
        codice_cliente,
        min(data_ora)::date as prima_fattura,
        max(data_ora)::date as ultima_fattura,
        count(distinct numero_fattura) filter (where not is_reso) as ordini,
        count(distinct numero_fattura) filter (where is_reso) as resi,
        round(sum(valore), 2) as valore_totale,
        -- Il paese di un cliente può cambiare fra una fattura e l'altra: si
        -- tiene quello più frequente, non l'ultimo, perché una singola
        -- spedizione a un indirizzo diverso non lo trasferisce all'estero.
        mode() within group (order by paese) as paese_principale
    from vendite
    group by codice_cliente

),

raccordo as (

    -- Il nome normalizzato arriva dalla seed e non da `dim_paese`: una
    -- dimensione che ne interroga un'altra è un legame che nessuno si aspetta,
    -- e nel grafo delle dipendenze si nota subito.
    --
    -- Senza questo passaggio il cruscotto dei clienti scriveva «Netherlands»
    -- mentre quello della geografia diceva «Paesi Bassi»: due nomi per lo
    -- stesso paese, nella stessa dashboard.
    select
        paese_sorgente,
        nome
    from {{ ref('paesi') }}

),

sconosciuto as (

    select
        -1 as cliente_key,
        null::bigint as codice_cliente,
        'Sconosciuto' as etichetta,
        true as is_sconosciuto,
        null::date as prima_fattura,
        null::date as ultima_fattura,
        0 as ordini,
        0 as resi,
        null::numeric as valore_totale,
        null::text as paese_principale

),

noti as (

    select
        row_number() over (order by c.codice_cliente) as cliente_key,
        c.codice_cliente,
        c.codice_cliente::text as etichetta,
        false as is_sconosciuto,
        c.prima_fattura,
        c.ultima_fattura,
        c.ordini,
        c.resi,
        c.valore_totale,
        coalesce(r.nome, c.paese_principale) as paese_principale
    from per_cliente as c
    left join raccordo as r on c.paese_principale = r.paese_sorgente

)

select
    cliente_key,
    codice_cliente,
    etichetta,
    is_sconosciuto,
    prima_fattura,
    ultima_fattura,
    ordini,
    resi,
    valore_totale,
    paese_principale
from sconosciuto

union all

select
    cliente_key,
    codice_cliente,
    etichetta,
    is_sconosciuto,
    prima_fattura,
    ultima_fattura,
    ordini,
    resi,
    valore_totale,
    paese_principale
from noti
