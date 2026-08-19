/*
    Tipizzazione e classificazione delle righe grezze (M3-T4 … M3-T8).

    Questo modello non toglie niente: **tutte** le righe di `raw` arrivano
    fino in fondo, e ognuna esce con un `motivo_esclusione` che è nullo
    quando la riga è buona.

    Esiste per una ragione sola: `stg_vendite` (le righe tenute) e
    `stg_esclusioni` (il conteggio di quelle scartate) devono nascere dallo
    stesso identico giudizio. Se ciascuno rifacesse i propri filtri, prima o
    poi divergerebbero di qualche riga — ed è esattamente lo scarto che il
    test di quadratura di M5-T7 cerca.

    I motivi sono in ordine di priorità: una riga esclusa per più di un motivo
    viene contata una volta sola, sul primo che la coglie. Senza questa
    regola la somma delle esclusioni supererebbe le righe escluse.
*/

with grezze as (

    select
        -- `trim` sui codici: alcuni arrivano con spazi in coda («47503J »),
        -- e senza pulirli sarebbero due prodotti diversi.
        trim(invoice) as numero_fattura,
        trim(stock_code) as codice_prodotto,
        description as descrizione_grezza,
        quantity::integer as quantita,
        invoice_date::timestamp as data_ora,
        price::numeric(10, 2) as prezzo_unitario,
        -- Il CSV scrive i codici cliente come numeri con la virgola
        -- («13085.0»): il doppio cast toglie la parte decimale senza
        -- passare da manipolazioni di stringhe.
        customer_id::numeric::bigint as codice_cliente,
        trim(country) as paese,
        caricato_il,
        file_origine
    from {{ source('raw', 'vendite') }}

),

nel_periodo as (

    select
        numero_fattura,
        codice_prodotto,
        descrizione_grezza,
        quantita,
        data_ora,
        prezzo_unitario,
        codice_cliente,
        paese,
        caricato_il,
        file_origine
    from grezze
    where {{ limite_periodo('data_ora', 'grezze') }}

),

numerate as (

    select
        numero_fattura,
        codice_prodotto,
        descrizione_grezza,
        quantita,
        data_ora,
        prezzo_unitario,
        codice_cliente,
        paese,
        caricato_il,
        file_origine,

        -- Un reso è una fattura che inizia per C. I resi **restano**: il
        -- tasso di reso è uno dei cinque indicatori (M3-T5).
        numero_fattura like 'C%' as is_reso,

        /*
            Righe identiche su fattura, prodotto, quantità e istante: la
            seconda in poi è un duplicato esatto (M3-T8).

            L'ordinamento non è un dettaglio estetico. La chiave del piano non
            comprende il prezzo, quindi dentro un gruppo possono finire righe
            con prezzi diversi — tipicamente una a prezzo pieno e una a zero.
            Con un ordinamento arbitrario, a volte sopravviveva quella a zero:
            veniva scartata dal filtro sui prezzi, e la sua gemella valida
            spariva come duplicato. Due esecuzioni della stessa vista davano
            conteggi diversi, di tre righe.

            Ordinando per prezzo decrescente si tiene sempre la riga che vale,
            e le colonne successive rendono l'ordine ripetibile anche quando i
            prezzi coincidono: senza un criterio totale, il risultato dipende
            da come il database ha deciso di leggere le pagine.
        */
        row_number() over (
            partition by numero_fattura, codice_prodotto, quantita, data_ora
            order by
                prezzo_unitario desc,
                coalesce(descrizione_grezza, ''),
                coalesce(codice_cliente, -1),
                file_origine
        ) as ordinale

    from nel_periodo

),

servizio as (

    select
        upper(codice) as codice,
        motivo
    from {{ ref('codici_di_servizio') }}

)

select
    n.numero_fattura,
    n.codice_prodotto,
    n.descrizione_grezza,
    n.quantita,
    n.data_ora,
    n.prezzo_unitario,
    n.codice_cliente,
    n.paese,
    n.is_reso,
    n.caricato_il,
    n.file_origine,

    -- Descrizione normalizzata: spazi ripuliti e maiuscolo. La scelta della
    -- descrizione più frequente per codice avviene in `stg_vendite`, dove si
    -- guardano solo le righe tenute (M3-T9).
    nullif(upper(regexp_replace(trim(n.descrizione_grezza), '\s+', ' ', 'g')), '')
        as descrizione_normalizzata,

    case
        when s.codice is not null then 'codice di servizio'
        when n.prezzo_unitario <= 0 then 'prezzo non positivo'
        when n.ordinale > 1 then 'duplicato esatto'
    end as motivo_esclusione

from numerate as n
left join servizio as s
    on upper(n.codice_prodotto) = s.codice
