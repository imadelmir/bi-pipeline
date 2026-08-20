/*
    Nessuna riga di vendita con prezzo minore o uguale a zero (M5-T5).

    Cosa impedisce: che le rettifiche contabili rientrino di nascosto fra le
    vendite. Sono 6.168 righe, e a prezzo zero non spostano il fatturato di una
    sterlina — ma gonfiano il conteggio degli ordini, il numero di prodotti
    venduti e lo scontrino medio, che si calcola dividendo per gli ordini.

    Il filtro è in `stg_vendite_classificate`. Questo test verifica che ci sia
    davvero: una modifica al modello che lo tolga per sbaglio si presenta come
    test rosso invece che come indicatore leggermente diverso.

    Un test dbt passa quando non restituisce righe.
*/

select
    numero_fattura,
    codice_prodotto,
    prezzo_unitario,
    data_ora
from {{ ref('stg_vendite') }}
where prezzo_unitario <= 0
