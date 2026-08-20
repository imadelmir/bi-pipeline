/*
    Anagrafica dei prodotti (M4-T2).

    Una riga per codice prodotto, con la descrizione già scelta in staging e
    quattro colonne che nascono dalle vendite: prima e ultima volta che è stato
    venduto, quante righe, prezzo medio.

    La chiave è surrogata: il fatto non punta a `85123A` ma a un intero. Costa
    un passaggio in più e restituisce join più veloci e indipendenza dai codici
    della sorgente — il giorno che il fornitore rinumera il catalogo, cambia
    una colonna di questa tabella e non un milione di righe del fatto.
*/

with vendite as (

    select
        codice_prodotto,
        descrizione,
        data_ora,
        quantita,
        prezzo_unitario,
        is_reso
    from {{ ref('stg_vendite') }}

),

per_prodotto as (

    select
        codice_prodotto,
        max(descrizione) as descrizione,
        min(data_ora)::date as prima_vendita,
        max(data_ora)::date as ultima_vendita,
        count(*) as righe_vendita,
        -- I resi non entrano nel prezzo medio: hanno lo stesso prezzo della
        -- vendita ma quantità negativa, e mescolarli abbasserebbe la media
        -- senza che nessun prezzo sia mai cambiato.
        round(avg(prezzo_unitario) filter (where not is_reso), 2) as prezzo_medio,
        min(prezzo_unitario) as prezzo_minimo,
        max(prezzo_unitario) as prezzo_massimo,
        sum(quantita) filter (where not is_reso) as pezzi_venduti,
        sum(quantita) filter (where is_reso) as pezzi_resi
    from vendite
    group by codice_prodotto

)

select
    -- La chiave nasce dall'ordine alfabetico del codice: è arbitrario ma
    -- ripetibile. Una ricostruzione della dimensione assegna le stesse chiavi,
    -- e il fatto incrementale continua a puntare dove puntava.
    row_number() over (order by codice_prodotto) as prodotto_key,
    codice_prodotto,
    descrizione,
    prima_vendita,
    ultima_vendita,
    righe_vendita,
    prezzo_medio,
    prezzo_minimo,
    prezzo_massimo,
    pezzi_venduti,
    coalesce(pezzi_resi, 0) as pezzi_resi
from per_prodotto
