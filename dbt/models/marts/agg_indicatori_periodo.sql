/*
    I cinque indicatori, già calcolati, a più livelli di aggregazione (M7-T3).

    Metabase legge questa tabella e mostra una colonna. Non divide, non conta
    distinti, non decide cosa escludere: tutte quelle scelte stanno qui, in un
    file versionato che si legge in una pull request.

    ## Perché più livelli in una tabella sola

    Due indicatori su cinque **non si possono sommare**:

    - i **clienti attivi** sono un conteggio di valori distinti. Lo stesso
      cliente compra a gennaio e a marzo: sommare i conteggi mensili lo
      conterebbe due volte;
    - lo **scontrino medio** e il **tasso di reso** sono rapporti. La media
      delle medie non è la media, e il rapporto delle somme non è la somma dei
      rapporti.

    Se questa tabella avesse solo la grana mensile, un cruscotto che mostra
    «clienti attivi nel 2011» sommerebbe dodici numeri e ne otterrebbe uno
    più grande del vero. Con `grouping sets` il database calcola ogni livello
    guardando i dati veri, in una passata sola.

    La colonna `livello` dice a che aggregazione appartiene una riga, e ogni
    domanda salvata filtra quella che le serve. **Chi sbaglia livello somma
    tutto due volte**, quindi il filtro non è facoltativo: c'è un test che
    pretende una riga sola per il livello «tutto».
*/

with vendite as (

    select
        f.data_key,
        d.anno,
        d.mese,
        d.anno_mese,
        f.paese_key,
        p.nome as nome_paese,
        p.is_regno_unito,
        f.numero_fattura,
        f.cliente_key,
        f.quantita,
        f.valore,
        f.is_reso
    from {{ ref('fct_vendite') }} as f
    join {{ ref('dim_data') }} as d on f.data_key = d.data_key
    join {{ ref('dim_paese') }} as p on f.paese_key = p.paese_key

),

aggregate as (

    select
        grouping(anno) as g_anno,
        grouping(mese) as g_mese,
        grouping(paese_key) as g_paese,

        anno,
        mese,
        max(anno_mese) as anno_mese,
        paese_key,
        max(nome_paese) as nome_paese,
        bool_or(is_regno_unito) as is_regno_unito,

        /*
            `coalesce` a zero e non `null`: nel dicembre 2009 il Giappone e la
            Nigeria hanno soltanto resi e nessuna vendita, e `sum() filter`
            restituisce `null`. Ma il fatturato lordo di chi non ha venduto
            niente è **zero**, non «sconosciuto» — e un null si propaga: in
            Metabase la somma di una colonna con dei null resta un numero, ma
            un rapporto che ci finisce sopra diventa vuoto senza spiegazione.
        */
        round(coalesce(sum(valore) filter (where not is_reso), 0), 2)
            as valore_lordo,
        round(coalesce(-sum(valore) filter (where is_reso), 0), 2) as valore_resi,
        round(coalesce(sum(valore), 0), 2) as valore_netto,

        count(distinct numero_fattura) filter (where not is_reso) as ordini,

        -- Il membro *Sconosciuto* è escluso dai clienti attivi: contarlo
        -- significherebbe contare come un cliente solo le 226.979 righe che
        -- non hanno un codice, sbagliando in difetto.
        count(distinct cliente_key) filter (where cliente_key <> -1)
            as clienti_attivi,

        coalesce(sum(quantita) filter (where not is_reso), 0) as pezzi_venduti,
        count(*) as righe

    from vendite
    group by grouping sets (
        (),                    -- tutto
        (anno),                -- per anno
        (anno, mese),          -- per mese
        (paese_key),           -- per paese
        (anno, paese_key)      -- per anno e paese
    )

)

select
    case
        when g_anno = 1 and g_paese = 1 then 'tutto'
        when g_anno = 0 and g_mese = 0 and g_paese = 1 then 'mese'
        when g_anno = 0 and g_paese = 1 then 'anno'
        when g_anno = 1 and g_paese = 0 then 'paese'
        else 'anno_paese'
    end as livello,

    anno,
    mese,
    anno_mese,

    /*
        Le colonne che il livello non raggruppa devono essere **nulle**, non
        riempite con un valore qualunque.

        `max(nome_paese)` dentro l'aggregazione restituisce un nome anche
        quando i paesi sono tutti insieme — il massimo alfabetico, che è
        semplicemente falso: quella riga non parla degli Stati Uniti, parla di
        tutti. Una domanda che cerca «la riga senza paese» non la trovava, e i
        cinque indicatori del cruscotto uscivano vuoti.
    */
    case when g_paese = 0 then paese_key end as paese_key,
    case when g_paese = 0 then nome_paese end as nome_paese,
    case when g_paese = 0 then is_regno_unito end as is_regno_unito,

    valore_lordo,
    valore_resi,
    valore_netto,
    ordini,
    clienti_attivi,
    pezzi_venduti,
    righe,

    -- Scontrino medio: fatturato netto diviso ordini. I resi stanno al
    -- numeratore e non al denominatore — è voluto, ed è il motivo per cui
    -- questo numero è più basso del prezzo medio di una fattura.
    case
        when ordini > 0 then round(valore_netto / ordini, 2)
    end as scontrino_medio,

    -- Tasso di reso **sul valore**, non sul conteggio: un reso da mille
    -- sterline non pesa quanto uno da due, e contarli uguali nasconde il
    -- problema vero.
    case
        when valore_lordo > 0 then round(valore_resi / valore_lordo * 100, 2)
    end as tasso_reso_percentuale

from aggregate
