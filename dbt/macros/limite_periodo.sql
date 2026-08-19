{#
    Taglio del periodo per il target `dev` (M3-T3).

    Stessi modelli in sviluppo e in produzione: cambia solo quanti dati
    attraversano. Copiare i modelli per averne una versione «piccola»
    significherebbe due file da tenere allineati, e il giorno che divergono la
    prova in sviluppo non dice più niente su cosa succederà in produzione.

    In `dev` tiene gli ultimi N mesi (variabile `mesi_in_dev`), contati dalla
    data più recente presente nei dati — non da `today()`: la sorgente si ferma
    al 09/12/2011, e un filtro sulla data odierna lascerebbe zero righe.

    In `prod` restituisce `true`, cioè nessun filtro.

    Uso, dentro un modello:

        where {{ limite_periodo('data_ora', 'nome_della_cte') }}
#}

{% macro limite_periodo(colonna, sorgente) %}
    {%- if target.name == 'dev' -%}
        {{ colonna }} >= (
            select max({{ colonna }}) - interval '{{ var("mesi_in_dev") }} months'
            from {{ sorgente }}
        )
    {%- else -%}
        true
    {%- endif -%}
{% endmacro %}
