/*
    Gli indicatori aggregati per giorno, paese e prodotto (M7-T3).

    Esiste perché la regola del progetto è che i cinque indicatori si
    calcolano **in dbt**. Una formula scritta dentro un grafico non è
    versionata, non è testata e non la ritrova nessuno: qui invece la
    definizione sta in un file, e Metabase si limita a sommare colonne.

    ## Cosa è additivo e cosa no

    Questa è la parte che si sbaglia sempre, quindi vale la pena scriverla.

    **Additive** — si possono sommare su qualsiasi combinazione di righe:
    `valore_lordo`, `valore_resi`, `valore_netto`, `pezzi`, `righe`.

    **Additiva solo perché la grana lo permette**: `ordini`. Una fattura
    appartiene a un solo istante e quindi a un solo giorno, e a un solo paese:
    sommare i conteggi di giorni diversi non conta due volte la stessa
    fattura. Se un domani la grana cambiasse, questa colonna diventerebbe
    sbagliata **in silenzio**.

    **Non additivi**: i clienti distinti, che non compaiono qui apposta — lo
    stesso cliente compra in giorni diversi, e sommare i conteggi giornalieri
    lo conterebbe una volta per giorno. Stanno in `agg_indicatori_periodo`,
    calcolati a ogni livello che serve.

    Gli indicatori che sono **rapporti** — scontrino medio e tasso di reso —
    non stanno qui per lo stesso motivo: la media delle medie non è la media.
    Si ottengono dividendo due somme, e quel calcolo vive in
    `agg_indicatori_periodo`.
*/

with vendite as (

    select
        data_key,
        paese_key,
        prodotto_key,
        numero_fattura,
        quantita,
        valore,
        is_reso
    from {{ ref('fct_vendite') }}

)

select
    data_key,
    paese_key,
    prodotto_key,

    -- Il lordo esclude i resi; il netto li comprende come negativi. La
    -- differenza fra i due *è* il valore dei resi, e sono tre colonne perché
    -- il cruscotto le mostra tutte e tre insieme: il netto da solo nasconde
    -- quanto rientra.
    round(sum(valore) filter (where not is_reso), 2) as valore_lordo,
    round(-sum(valore) filter (where is_reso), 2) as valore_resi,
    round(sum(valore), 2) as valore_netto,

    sum(quantita) filter (where not is_reso) as pezzi_venduti,
    -sum(quantita) filter (where is_reso) as pezzi_resi,

    -- Gli ordini contano le fatture, non le righe: una fattura con dodici
    -- prodotti resta un ordine solo. I resi non sono ordini.
    count(distinct numero_fattura) filter (where not is_reso) as ordini,
    count(distinct numero_fattura) filter (where is_reso) as fatture_di_reso,

    count(*) as righe

from vendite
group by data_key, paese_key, prodotto_key
