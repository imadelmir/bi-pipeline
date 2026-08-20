"""Le domande salvate e i tre cruscotti, definiti qui e non a clic (M7-T3…T7).

Ogni domanda è SQL che sta in questo file, quindi in git: si legge in una pull
request, si rifà su un'altra macchina con un comando, e il giorno che un numero
sembra sbagliato si va a vedere da dove viene invece di aprire venti finestre.

**Nessun calcolo di business qui dentro.** Gli indicatori sono già calcolati in
`marts.agg_indicatori_periodo`: queste query scelgono una riga e mostrano una
colonna. Le poche aggregazioni che restano — somme e ordinamenti per le
classifiche — sono somme di colonne additive, non definizioni di misure.

## I cinque indicatori mostrano anche la variazione

Il piano è esplicito: «un numero senza confronto non dice se è buono». Le cinque
schede in cima al primo cruscotto sono `smartscalar`, il tipo che mostra il
valore e sotto quanto è cambiato rispetto al periodo precedente. Per farlo la
query non restituisce una riga sola ma la serie degli anni fino a quello
scelto: Metabase confronta gli ultimi due.

## I filtri

`{{anno}}` e `{{paese}}` sono parametri obbligatori con un valore predefinito,
collegati ai filtri del cruscotto. Obbligatori di proposito: un filtro
facoltativo su una tabella che contiene più livelli di aggregazione lascerebbe
sommare fra loro righe che si sovrappongono, e il totale verrebbe doppio senza
che nulla lo segnali.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from metabase.formati import (
    BLU,
    GRAFITE,
    SALMONE,
    VERDE,
    VIOLA,
    intero,
    percentuale,
    sterline,
    unisci,
)

# L'ultimo anno quasi completo nei dati, che si fermano al 9 dicembre 2011.
ANNO_PREDEFINITO = 2011


def _tag_anno() -> dict[str, Any]:
    return {
        "id": "b1a1f1e1-0001-4000-8000-000000000001",
        "name": "anno",
        "display-name": "Anno",
        "type": "number",
        "required": True,
        "default": str(ANNO_PREDEFINITO),
    }


def _tag_paese() -> dict[str, Any]:
    return {
        "id": "b1a1f1e1-0002-4000-8000-000000000002",
        "name": "paese",
        "display-name": "Paese",
        "type": "text",
        "required": True,
        "default": "tutti",
    }


@dataclass
class Domanda:
    """Una domanda salvata: nome, SQL, e come si disegna."""

    chiave: str
    nome: str
    descrizione: str
    sql: str
    display: str
    impostazioni: dict[str, Any] = field(default_factory=dict)
    con_anno: bool = True
    con_paese: bool = False

    def tag(self) -> dict[str, Any]:
        tag: dict[str, Any] = {}
        if self.con_anno:
            tag["anno"] = _tag_anno()
        if self.con_paese:
            tag["paese"] = _tag_paese()
        return tag


# La riga giusta di `agg_indicatori_periodo`: quando il paese è «tutti» si
# guarda il livello per anno, altrimenti quello per anno e paese. Senza questa
# distinzione si sommerebbero righe che contengono già i totali.
CONDIZIONE_LIVELLO = """
    where livello = (case when {{paese}} = 'tutti' then 'anno' else 'anno_paese' end)
      and (({{paese}} = 'tutti' and nome_paese is null) or nome_paese = {{paese}})
"""


def _serie_indicatore(colonna: str, etichetta: str) -> str:
    """La serie annuale fino all'anno scelto: l'ultimo valore e il precedente.

    `make_date` perché `smartscalar` vuole una colonna temporale per sapere
    quale periodo confrontare con quale.
    """
    return (
        f'select make_date(anno, 1, 1) as periodo, {colonna} as "{etichetta}"\n'
        f"from marts.agg_indicatori_periodo\n"
        f"{CONDIZIONE_LIVELLO}"
        f"  and anno <= {{{{anno}}}}\n"
        f"order by periodo"
    )


def _indicatore(
    chiave: str,
    nome: str,
    colonna: str,
    descrizione: str,
    formato: dict[str, Any],
) -> Domanda:
    return Domanda(
        chiave=chiave,
        nome=nome,
        descrizione=descrizione,
        sql=_serie_indicatore(colonna, nome),
        display="smartscalar",
        impostazioni={
            "scalar.field": nome,
            "column_settings": formato,
            # Una freccia sola, con il confronto sull'anno precedente: due o
            # tre confronti sovrapposti in una scheda alta tre righe non si
            # leggono.
            "scalar.comparisons": [{"id": "precedente", "type": "previousValue"}],
            "scalar.switch_positive_negative": False,
        },
        con_paese=True,
    )


DOMANDE: list[Domanda] = [
    # --- i cinque indicatori (M7-T3) ---------------------------------------
    _indicatore(
        "fatturato_netto",
        "Fatturato netto",
        "valore_netto",
        "Somma del valore di tutte le righe, resi compresi come negativi. "
        "Calcolato in dbt: marts.agg_indicatori_periodo.",
        sterline("Fatturato netto", decimali=1, compatto=True),
    ),
    _indicatore(
        "ordini",
        "Ordini",
        "ordini",
        "Fatture distinte, resi esclusi. Una fattura con dodici prodotti "
        "resta un ordine solo.",
        intero("Ordini"),
    ),
    _indicatore(
        "scontrino_medio",
        "Scontrino medio",
        "scontrino_medio",
        "Fatturato netto diviso ordini. I resi stanno al numeratore e non al "
        "denominatore: è voluto, e abbassa il valore.",
        sterline("Scontrino medio", decimali=2),
    ),
    _indicatore(
        "tasso_reso",
        "Tasso di reso",
        "tasso_reso_percentuale",
        "Valore dei resi sul fatturato lordo. Sul valore e non sul conteggio: "
        "un reso da mille sterline non pesa quanto uno da due.",
        percentuale("Tasso di reso"),
    ),
    _indicatore(
        "clienti_attivi",
        "Clienti attivi",
        "clienti_attivi",
        "Clienti distinti, escluso il membro Sconosciuto: contarlo "
        "significherebbe contare come uno solo un quinto delle righe.",
        intero("Clienti attivi"),
    ),
    # --- cruscotto 1: andamento (M7-T4) ------------------------------------
    Domanda(
        chiave="fatturato_per_mese",
        nome="Fatturato netto per mese",
        descrizione="Il confronto è con lo stesso mese dell'anno precedente, "
        "non con il mese prima: la stagionalità di un grossista di articoli da "
        "regalo è fortissima, e novembre contro ottobre direbbe solo che si "
        "avvicina il Natale.",
        sql="""
-- `make_date` e non `to_date(mese, 'MM')`: quest'ultima costruisce una data
-- nell'anno 1 *avanti Cristo*, e il grafico esce con un asse che va dal 1944
-- al 2108 e nessuna linea sopra.
--
-- Le due serie usano la stessa data — quella dell'anno selezionato — così si
-- sovrappongono mese per mese invece di finire su due tratti lontani
-- dell'asse: il confronto si legge in verticale, che è il motivo per cui
-- esiste.
select
    make_date({{anno}}, mese, 1) as "Mese",
    sum(valore_netto) filter (where anno = {{anno}})     as "Anno selezionato",
    sum(valore_netto) filter (where anno = {{anno}} - 1) as "Anno precedente"
from marts.agg_indicatori_periodo
where livello = 'mese'
  and anno in ({{anno}}, {{anno}} - 1)
group by mese
order by mese
""",
        display="line",
        impostazioni={
            "graph.dimensions": ["Mese"],
            "graph.metrics": ["Anno selezionato", "Anno precedente"],
            "graph.x_axis.title_text": "",
            "graph.y_axis.title_text": "Fatturato netto",
            "graph.x_axis.axis_enabled": True,
            "graph.y_axis.auto_split": False,
            # Una serie blu e una viola: l'anno in corso è il protagonista,
            # quello prima è un riferimento. Due blu non si distinguono.
            "series_settings": {
                "Anno selezionato": {"color": BLU, "line.size": "L"},
                "Anno precedente": {"color": VIOLA, "line.style": "dashed"},
            },
            "column_settings": unisci(
                sterline("Anno selezionato", compatto=True),
                sterline("Anno precedente", compatto=True),
            ),
            "graph.show_trendline": False,
        },
    ),
    Domanda(
        chiave="ordini_per_mese",
        nome="Ordini per mese",
        descrizione="Fatture distinte per mese, resi esclusi.",
        sql="""
select make_date({{anno}}, mese, 1) as "Mese", ordini as "Ordini"
from marts.agg_indicatori_periodo
where livello = 'mese' and anno = {{anno}}
order by mese
""",
        display="bar",
        impostazioni={
            "graph.dimensions": ["Mese"],
            "graph.metrics": ["Ordini"],
            "graph.x_axis.title_text": "",
            "graph.y_axis.title_text": "Ordini",
            "series_settings": {"Ordini": {"color": BLU}},
            "column_settings": intero("Ordini"),
        },
    ),
    Domanda(
        chiave="lordo_resi_netto",
        nome="Lordo, resi, netto",
        descrizione="Le tre misure insieme di proposito: il netto da solo "
        "nasconde quanto rientra, e la differenza fra lordo e netto *è* "
        "l'indicatore dei resi.",
        sql="""
with valori as (
    select valore_lordo, valore_resi, valore_netto
    from marts.agg_indicatori_periodo
"""
        + CONDIZIONE_LIVELLO
        + """      and anno = {{anno}}
)
select 'Fatturato lordo' as "Voce", valore_lordo as "Importo", 1 as ordine
from valori
union all
select 'Resi', -valore_resi, 2 from valori
union all
select 'Fatturato netto', valore_netto, 3 from valori
order by ordine
""",
        display="table",
        impostazioni={
            "table.columns": [
                {"name": "Voce", "enabled": True},
                {"name": "Importo", "enabled": True},
                {"name": "ordine", "enabled": False},
            ],
            "column_settings": sterline("Importo", decimali=2),
        },
        con_paese=True,
    ),
    # --- cruscotto 2: prodotti e clienti (M7-T5) ---------------------------
    Domanda(
        chiave="primi_prodotti",
        nome="Primi venti prodotti per valore",
        descrizione="Barre orizzontali e non verticali: i nomi dei prodotti "
        "sono lunghi, e in verticale non si leggono.",
        sql="""
select
    initcap(p.descrizione) as "Prodotto",
    round(sum(a.valore_netto), 2) as "Fatturato netto"
from marts.agg_indicatori_giorno as a
join marts.dim_prodotto as p on a.prodotto_key = p.prodotto_key
join marts.dim_data as d on a.data_key = d.data_key
where d.anno = {{anno}}
group by p.descrizione
order by sum(a.valore_netto) desc
limit 20
""",
        display="row",
        impostazioni={
            "graph.dimensions": ["Prodotto"],
            "graph.metrics": ["Fatturato netto"],
            "graph.show_values": True,
            "series_settings": {"Fatturato netto": {"color": BLU}},
            "column_settings": sterline("Fatturato netto", compatto=True),
        },
    ),
    Domanda(
        chiave="distribuzione_scontrino",
        nome="Distribuzione dello scontrino",
        descrizione="Quante fatture per fascia di importo. La media da sola "
        "nasconde la forma e descrive un cliente che non esiste.",
        sql="""
with fatture as (
    select f.numero_fattura, sum(f.valore) as totale
    from marts.fct_vendite as f
    join marts.dim_data as d on f.data_key = d.data_key
    where not f.is_reso and d.anno = {{anno}}
    group by f.numero_fattura
    having sum(f.valore) > 0
)
select
    case
        when totale < 50 then 'fino a 50'
        when totale < 150 then '50 – 150'
        when totale < 300 then '150 – 300'
        when totale < 600 then '300 – 600'
        when totale < 1500 then '600 – 1.500'
        else 'oltre 1.500'
    end as "Importo della fattura",
    count(*) as "Fatture"
from fatture
group by 1
order by min(totale)
""",
        display="bar",
        impostazioni={
            "graph.dimensions": ["Importo della fattura"],
            "graph.metrics": ["Fatture"],
            "graph.x_axis.title_text": "",
            "graph.y_axis.title_text": "Fatture",
            "graph.show_values": True,
            "series_settings": {"Fatture": {"color": VERDE}},
            "column_settings": intero("Fatture"),
        },
    ),
    Domanda(
        chiave="primi_clienti",
        nome="Primi clienti per fatturato",
        descrizione="Tabella e non grafico: sono valori da leggere, non da "
        "confrontare a colpo d'occhio. Sono rivenditori, non consumatori — uno "
        "solo di questi fa il fatturato di centinaia di clienti piccoli.",
        sql="""
select
    c.etichetta as "Cliente",
    c.paese_principale as "Paese",
    round(sum(f.valore), 2) as "Fatturato netto",
    count(distinct f.numero_fattura) filter (where not f.is_reso) as "Ordini"
from marts.fct_vendite as f
join marts.dim_cliente as c on f.cliente_key = c.cliente_key
join marts.dim_data as d on f.data_key = d.data_key
where d.anno = {{anno}}
  and not c.is_sconosciuto
group by c.etichetta, c.paese_principale
order by sum(f.valore) desc
limit 15
""",
        display="table",
        impostazioni={
            "column_settings": unisci(
                sterline("Fatturato netto", decimali=0),
                intero("Ordini"),
            ),
        },
    ),
    Domanda(
        chiave="prodotti_piu_resi",
        nome="Prodotti con il tasso di reso più alto",
        descrizione="Il tasso è sul valore, non sul numero di pezzi. Solo "
        "prodotti con almeno cento righe di vendita: su tre vendite un reso fa "
        "il 33 % e non significa niente.",
        sql="""
with per_prodotto as (
    select
        p.descrizione,
        sum(a.valore_lordo) as lordo,
        sum(coalesce(a.valore_resi, 0)) as resi,
        sum(a.righe) as righe
    from marts.agg_indicatori_giorno as a
    join marts.dim_prodotto as p on a.prodotto_key = p.prodotto_key
    join marts.dim_data as d on a.data_key = d.data_key
    where d.anno = {{anno}}
    group by p.descrizione
)
select
    initcap(descrizione) as "Prodotto",
    round(resi / nullif(lordo, 0) * 100, 1) as "Tasso di reso"
from per_prodotto
where righe >= 100 and lordo > 0
order by resi / nullif(lordo, 0) desc
limit 12
""",
        display="row",
        impostazioni={
            "graph.dimensions": ["Prodotto"],
            "graph.metrics": ["Tasso di reso"],
            "graph.show_values": True,
            # Salmone: sono resi, cioè la parte che va storta. Il rosso pieno
            # su un cruscotto guardato tutto il giorno drammatizza.
            "series_settings": {"Tasso di reso": {"color": SALMONE}},
            "column_settings": percentuale("Tasso di reso", decimali=1),
        },
    ),
    # --- cruscotto 3: geografia (M7-T6) ------------------------------------
    Domanda(
        chiave="fatturato_per_paese",
        nome="Fatturato per paese, senza il Regno Unito",
        descrizione="Il Regno Unito è escluso ed è una scelta: vale l'84 % del "
        "fatturato, e con lui dentro tutte le altre barre diventano trattini "
        "indistinguibili. Il suo peso si legge nella scheda accanto, che è il "
        "posto giusto per una proporzione.",
        sql="""
select
    nome_paese as "Paese",
    round(valore_netto, 2) as "Fatturato netto"
from marts.agg_indicatori_periodo
where livello = 'anno_paese'
  and anno = {{anno}}
  and not is_regno_unito
  and valore_netto > 0
order by valore_netto desc
limit 12
""",
        display="row",
        impostazioni={
            "graph.dimensions": ["Paese"],
            "graph.metrics": ["Fatturato netto"],
            "graph.show_values": True,
            "series_settings": {"Fatturato netto": {"color": BLU}},
            "column_settings": sterline("Fatturato netto", compatto=True),
        },
    ),
    Domanda(
        chiave="interno_contro_estero",
        nome="Mercato interno contro estero",
        descrizione="Una barra impilata e non una torta: due fette così "
        "diverse in un cerchio si leggono peggio, e la torta non permette di "
        "confrontare due periodi affiancati.",
        sql="""
select
    'Fatturato' as "Anno",
    round(sum(valore_netto) filter (where is_regno_unito), 2) as "Regno Unito",
    round(sum(valore_netto) filter (where not is_regno_unito), 2) as "Estero"
from marts.agg_indicatori_periodo
where livello = 'anno_paese' and anno = {{anno}}
""",
        display="bar",
        impostazioni={
            "graph.dimensions": ["Anno"],
            "graph.metrics": ["Regno Unito", "Estero"],
            "stackable.stack_type": "normalized",
            "graph.x_axis.title_text": "",
            "graph.y_axis.title_text": "",
            "graph.show_values": True,
            "series_settings": {
                "Regno Unito": {"color": GRAFITE},
                "Estero": {"color": BLU},
            },
            "column_settings": unisci(
                sterline("Regno Unito", compatto=True),
                sterline("Estero", compatto=True),
            ),
        },
    ),
    Domanda(
        chiave="scheda_italia",
        nome="Scheda Italia",
        descrizione="Va letta sapendo quanto è piccolo il campione: accanto al "
        "fatturato c'è il numero di clienti che lo produce. Un numero costruito "
        "su dodici clienti non è una tendenza.",
        sql="""
select
    round(valore_netto, 2) as "Fatturato netto",
    ordini as "Ordini",
    clienti_attivi as "Clienti",
    righe as "Righe di vendita"
from marts.agg_indicatori_periodo
where livello = 'anno_paese'
  and anno = {{anno}}
  and nome_paese = 'Italia'
""",
        display="table",
        impostazioni={
            "column_settings": unisci(
                sterline("Fatturato netto", decimali=0),
                intero("Ordini"),
                intero("Clienti"),
                intero("Righe di vendita"),
            ),
        },
    ),
]

DOMANDE_PER_CHIAVE = {d.chiave: d for d in DOMANDE}


@dataclass
class Scheda:
    """Una scheda dentro un cruscotto: una domanda, oppure del testo.

    Il testo non è riempitivo. Una pagina di soli numeri costringe chi la
    guarda a indovinare cosa sta guardando: due righe di spiegazione accanto a
    un grafico valgono più di un grafico in più.
    """

    riga: int
    colonna: int
    larghezza: int
    altezza: int
    chiave: str | None = None
    testo: str | None = None
    titolo: bool = False


@dataclass
class Cruscotto:
    nome: str
    descrizione: str
    schede: list[Scheda]


# La griglia di Metabase è larga 24 colonne.
CRUSCOTTI: list[Cruscotto] = [
    Cruscotto(
        nome="1 — Andamento",
        descrizione="Come sta andando, rispetto a quando.",
        schede=[
            Scheda(0, 0, 24, 1, titolo=True, testo="Come sta andando"),
            Scheda(1, 0, 5, 3, chiave="fatturato_netto"),
            Scheda(1, 5, 4, 3, chiave="ordini"),
            Scheda(1, 9, 5, 3, chiave="scontrino_medio"),
            Scheda(1, 14, 5, 3, chiave="tasso_reso"),
            Scheda(1, 19, 5, 3, chiave="clienti_attivi"),
            Scheda(
                4,
                0,
                24,
                1,
                testo="Ogni indicatore mostra sotto la variazione rispetto "
                "all'anno precedente. Il tasso di reso è calcolato **sul "
                "valore** e non sul numero di pezzi.",
            ),
            Scheda(5, 0, 16, 7, chiave="fatturato_per_mese"),
            Scheda(5, 16, 8, 7, chiave="lordo_resi_netto"),
            Scheda(
                12,
                0,
                24,
                1,
                testo="Il picco di novembre non è un errore: è un grossista di "
                "articoli da regalo, e i rivenditori si riforniscono prima di "
                "Natale. Dicembre 2011 cala perché i dati si fermano al giorno 9.",
            ),
            Scheda(13, 0, 24, 6, chiave="ordini_per_mese"),
        ],
    ),
    Cruscotto(
        nome="2 — Prodotti e clienti",
        descrizione="Cosa si vende, a chi, e cosa torna indietro.",
        schede=[
            Scheda(0, 0, 24, 1, titolo=True, testo="Cosa si vende, e a chi"),
            Scheda(1, 0, 12, 9, chiave="primi_prodotti"),
            Scheda(1, 12, 12, 9, chiave="primi_clienti"),
            Scheda(
                10,
                0,
                24,
                1,
                testo="I clienti sono rivenditori, non consumatori: uno solo "
                "dei primi fa da solo il fatturato di centinaia di clienti "
                "piccoli.",
            ),
            Scheda(11, 0, 12, 8, chiave="distribuzione_scontrino"),
            Scheda(11, 12, 12, 8, chiave="prodotti_piu_resi"),
            Scheda(
                19,
                0,
                24,
                1,
                testo="Lo scontrino medio dice una cosa, la distribuzione ne "
                "dice un'altra: metà delle fatture sta sotto le 150 sterline. "
                "La media da sola descrive un cliente che non esiste.",
            ),
        ],
    ),
    Cruscotto(
        nome="3 — Geografia",
        descrizione="Dove sono i clienti, e perché la scala inganna.",
        schede=[
            Scheda(0, 0, 24, 1, titolo=True, testo="Dove sono i clienti"),
            Scheda(1, 0, 14, 9, chiave="fatturato_per_paese"),
            Scheda(1, 14, 10, 4, chiave="interno_contro_estero"),
            Scheda(5, 14, 10, 5, chiave="scheda_italia"),
            Scheda(
                10,
                0,
                24,
                2,
                testo="**Il Regno Unito non è nella classifica, ed è una "
                "scelta.** Vale l'84 % del fatturato: lasciandolo dentro, la "
                "sua barra arriva a fondo pagina e tutte le altre diventano "
                "trattini. Il suo peso si legge nella barra impilata a destra.\n\n"
                "La colonna del paese nella sorgente è testo libero e contiene "
                "voci che paesi non sono — `Unspecified`, `European Community`, "
                "`Channel Islands`, `EIRE` per l'Irlanda. La normalizzazione "
                "avviene in `dim_paese`, con una tabella di raccordo versionata.",
            ),
        ],
    ),
]
