/*
    Anagrafica dei paesi (M4-T4).

    La colonna `Country` della sorgente è testo libero e contiene voci che
    paesi non sono: `Unspecified`, `European Community`, `Channel Islands`,
    `EIRE` per l'Irlanda, `RSA` per il Sudafrica. La normalizzazione avviene
    qui, con una tabella di raccordo versionata (`seeds/paesi.csv`) — non con
    una serie di `CASE WHEN` nascosti dentro un grafico.

    Il join con la seed è esterno di proposito: se domani nei dati comparisse
    un paese non ancora mappato, comparirebbe comunque nella dimensione, con
    il nome della sorgente e macro-area «Non attribuito». Un join interno lo
    farebbe sparire dal fatto insieme alle sue vendite — che è il modo più
    silenzioso di perdere fatturato. Un test dedicato lo segnala (M5).
*/

with presenti as (

    select distinct paese as paese_sorgente
    from {{ ref('stg_vendite') }}

),

raccordo as (

    select
        paese_sorgente,
        nome,
        macro_area,
        nota
    from {{ ref('paesi') }}

)

select
    row_number() over (order by p.paese_sorgente) as paese_key,
    p.paese_sorgente,
    coalesce(r.nome, p.paese_sorgente) as nome,
    coalesce(r.macro_area, 'Non attribuito') as macro_area,
    r.nome is null as da_mappare,
    -- Solo il Regno Unito, non le Isole del Canale: sono dipendenze della
    -- Corona e non fanno parte del Regno Unito. La distinzione conta perché
    -- il cruscotto della geografia contrappone mercato interno ed estero.
    coalesce(r.macro_area = 'Regno Unito', false) as is_regno_unito,
    -- Le voci che un paese non sono restano nei dati, ma dichiarate: chi
    -- costruisce un grafico sa che non può metterle su una mappa.
    coalesce(r.macro_area = 'Non attribuito', true) as is_non_attribuito,
    r.nota
from presenti as p
left join raccordo as r
    on p.paese_sorgente = r.paese_sorgente
