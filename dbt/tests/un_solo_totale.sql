/*
    Il livello «tutto» ha una riga sola (M7-T3).

    `agg_indicatori_periodo` contiene cinque livelli di aggregazione nella
    stessa tabella. È comodo — un modello invece di cinque — ma diventa una
    trappola se un livello smette di essere unico: una domanda che filtra
    `livello = 'tutto'` e trova due righe mostrerebbe metà del fatturato, o il
    doppio, a seconda di come le somma.

    Il rischio non è teorico: basta aggiungere una colonna ai `grouping sets`
    e dimenticare di aggiornare il `case` che assegna il livello.
*/

select livello, count(*) as righe
from {{ ref('agg_indicatori_periodo') }}
where livello = 'tutto'
group by livello
having count(*) <> 1
