/*
    Il segno della quantità deve concordare con il marchio di reso (M5-T6).

    Un reso ha quantità negativa, una vendita positiva. Una riga marcata reso
    con quantità positiva sommerebbe al fatturato invece di sottrarre, e il
    tasso di reso — uno dei cinque indicatori — direbbe il falso in entrambe
    le direzioni.

    **Questo test passa grazie a due esclusioni scritte altrove**, e vale la
    pena saperlo prima di toccarle:

    - nella sorgente ci sono 3.457 righe con quantità negativa su fatture che
      non iniziano per `C`. Sono rettifiche di magazzino — «damages», «check»,
      «missing» — e hanno **tutte** prezzo zero: le toglie il filtro sui prezzi
      non positivi (M3-T7);
    - c'è una fattura di reso con quantità positiva, `C496350`, il cui codice
      prodotto è `M`, cioè *Manual*: la toglie l'esclusione dei codici di
      servizio (M3-T6).

    Chi un giorno allentasse una di quelle due regole si troverebbe questo test
    rosso, e senza questa nota non capirebbe perché.
*/

select
    numero_fattura,
    quantita,
    is_reso,
    data_ora
from {{ ref('fct_vendite') }}
where (is_reso and quantita > 0)
   or (not is_reso and quantita < 0)
