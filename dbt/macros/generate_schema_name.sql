{#
    Nomi degli schemi, senza il prefisso che dbt mette di suo.

    Il comportamento predefinito di dbt concatena lo schema del profilo a
    quello del modello: con profilo `staging` e modello in `+schema: staging`
    nasce `staging_staging`. Serve a far convivere più sviluppatori nello
    stesso database, ognuno con il proprio prefisso.

    Qui il database è locale e gli schemi sono quelli dichiarati nel piano —
    `raw`, `staging`, `marts` — e devono chiamarsi così anche in Metabase e
    nelle interrogazioni scritte a mano.

    Ma i due target devono restare separati: con un nome solo, un
    `dbt build --target dev` riscriverebbe le viste che Metabase sta leggendo,
    e per giunta con un trimestre di dati invece di due anni. Il cruscotto
    mostrerebbe numeri sbagliati senza che nessuno abbia toccato niente.

    Quindi: `prod` scrive in `staging` e `marts`, `dev` negli stessi nomi con
    il suffisso `_dev`.
#}

{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- set schema = custom_schema_name if custom_schema_name is not none
                     else target.schema -%}
    {%- if target.name == 'prod' -%}
        {{ schema | trim }}
    {%- else -%}
        {{ schema | trim }}_{{ target.name | trim }}
    {%- endif -%}
{%- endmacro %}
