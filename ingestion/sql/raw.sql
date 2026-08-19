-- Schema di atterraggio (M2-T4).
--
-- Regola dello strato: nessuna trasformazione. Tutte le colonne sono testo,
-- nessun vincolo, nessuna conversione. Se il dato è sporco entra sporco, e a
-- pulirlo ci pensa dbt in staging.
--
-- Perché testo e non i tipi giusti: un `numeric` rifiuterebbe la riga con il
-- prezzo scritto male, e il caricamento morirebbe a metà file su un dato che
-- volevamo proprio vedere. Un `timestamp` farebbe lo stesso con una data
-- ambigua. Qui dentro si entra sempre; la selezione avviene dopo, contata e
-- documentata.
--
-- Il file si può rieseguire quante volte si vuole: crea solo ciò che manca.

create schema if not exists raw;

create table if not exists raw.vendite (
    -- Le otto colonne della sorgente, con i nomi originali portati a
    -- snake_case. Restano in inglese: è lo strato che deve somigliare al
    -- file di partenza, e i nomi italiani nascono in staging.
    invoice       text,
    stock_code    text,
    description   text,
    quantity      text,
    invoice_date  text,
    price         text,
    customer_id   text,
    country       text,

    -- Le due colonne aggiunte dall'ingestione.
    -- `file_origine` è anche la chiave della cancellazione idempotente:
    -- ricaricare un file tocca solo le sue righe (M2-T8).
    caricato_il   timestamptz not null default now(),
    file_origine  text        not null
);

-- L'unico indice dello strato raw, e serve a una cosa sola: rendere veloce il
-- `delete from raw.vendite where file_origine = ...` che apre ogni
-- ricaricamento. Senza, ogni rilancio farebbe una scansione completa del
-- milione di righe.
create index if not exists ix_vendite_file_origine
    on raw.vendite (file_origine);

comment on table raw.vendite is
    'Righe di Online Retail II come arrivano dal CSV: tutto testo, nessun filtro.';


-- Registro dei caricamenti (M2-T7).
--
-- Risponde a una domanda che prima o poi arriva sempre: «questo numero da dove
-- viene?». File, checksum della sorgente, quando è iniziato, quando è finito,
-- quante righe, com'è andata.
create table if not exists raw.registro_caricamenti (
    id             bigserial primary key,
    file_origine   text        not null,
    checksum       text        not null,
    iniziato_il    timestamptz not null default now(),
    finito_il      timestamptz,
    righe_caricate bigint,
    -- 'in corso' | 'completato' | 'fallito'
    esito          text        not null,
    messaggio      text
);

comment on table raw.registro_caricamenti is
    'Un record per ogni tentativo di caricamento, riuscito o no.';
