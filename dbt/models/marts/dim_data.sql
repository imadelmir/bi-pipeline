/*
    Il calendario, generato e non letto (M4-T1).

    I giorni di chiusura non compaiono nelle vendite: se questa dimensione
    nascesse dai dati, un grafico giornaliero salterebbe le domeniche e nessuno
    se ne accorgerebbe — la linea sembrerebbe continua. Si genera l'intero
    periodo, e i giorni senza vendite restano visibili come zeri.

    La chiave è la data in forma numerica (20091201). È leggibile a occhio in
    una tabella dei fatti, si ordina da sola, e non ha bisogno di un join per
    capire di che giorno si parla.
*/

with periodo as (

    select
        min(data_ora)::date as primo_giorno,
        max(data_ora)::date as ultimo_giorno
    from {{ ref('stg_vendite') }}

),

giorni as (

    select generate_series(primo_giorno, ultimo_giorno, interval '1 day')::date as data
    from periodo

),

festivi as (

    select
        data::date as data,
        nome_festivo
    from {{ ref('festivi_regno_unito') }}

)

select
    to_char(g.data, 'YYYYMMDD')::integer as data_key,
    g.data,

    extract(year from g.data)::integer as anno,
    extract(quarter from g.data)::integer as trimestre,
    extract(month from g.data)::integer as mese,
    -- I nomi in italiano non arrivano da `to_char`, che segue la lingua del
    -- database: una macchina configurata in inglese darebbe «December» e i
    -- grafici cambierebbero etichetta a seconda di dove girano.
    (array[
        'gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno',
        'luglio', 'agosto', 'settembre', 'ottobre', 'novembre', 'dicembre'
    ])[extract(month from g.data)] as nome_mese,
    to_char(g.data, 'YYYY-MM') as anno_mese,

    extract(week from g.data)::integer as settimana,
    -- `isodow`: lunedì = 1, domenica = 7. Con `dow` la domenica sarebbe 0 e
    -- ogni ordinamento comincerebbe dalla domenica.
    extract(isodow from g.data)::integer as giorno_settimana,
    (array[
        'lunedì', 'martedì', 'mercoledì', 'giovedì',
        'venerdì', 'sabato', 'domenica'
    ])[extract(isodow from g.data)] as nome_giorno,
    extract(day from g.data)::integer as giorno_del_mese,

    extract(isodow from g.data) >= 6 as is_weekend,
    f.data is not null as is_festivo,
    f.nome_festivo,
    -- Giorno lavorativo: né weekend né festivo. È la colonna che serve per
    -- rispondere a «quanto si vende nei giorni di apertura».
    (extract(isodow from g.data) < 6 and f.data is null) as is_lavorativo

from giorni as g
left join festivi as f
    on g.data = f.data
