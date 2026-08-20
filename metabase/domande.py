"""Le domande salvate e i tre cruscotti, definiti qui e non a clic (M7-T3…T7).

Ogni domanda è SQL che sta in questo file, quindi in git: si legge in una pull
request, si rifà su un'altra macchina con un comando, e il giorno che un numero
sembra sbagliato si va a vedere da dove viene invece di aprire venti finestre.

**Nessun calcolo di business qui dentro.** Gli indicatori sono già calcolati in
`marts.agg_indicatori_periodo`: queste query scelgono una riga e mostrano una
colonna. Le poche aggregazioni che restano — somme e ordinamenti per le
classifiche — sono somme di colonne additive, non definizioni di misure.

## I filtri

`{{anno}}` e `{{paese}}` sono parametri obbligatori con un valore
predefinito, collegati ai filtri del cruscotto. Obbligatori di proposito: un
filtro facoltativo su una tabella che contiene più livelli di aggregazione
lascerebbe sommare fra loro righe che si sovrappongono, e il totale verrebbe
doppio senza che nulla lo segnali.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# L'ultimo anno completo nei dati. I dati si fermano al 9 dicembre 2011,
# quindi il 2011 è quasi completo e il 2009 ha un mese solo.
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
SCELTA_RIGA = """
    where livello = (case when {{paese}} = 'tutti' then 'anno' else 'anno_paese' end)
      and anno = {{anno}}
      and (({{paese}} = 'tutti' and nome_paese is null) or nome_paese = {{paese}})
"""


def _indicatore(
    chiave: str, nome: str, colonna: str, descrizione: str, prefisso: str = ""
) -> Domanda:
    return Domanda(
        chiave=chiave,
        nome=nome,
        descrizione=descrizione,
        sql=(
            f"select {colonna} as {chiave}\n"
            f"from marts.agg_indicatori_periodo\n{SCELTA_RIGA}"
        ),
        display="scalar",
        impostazioni={
            "scalar.field": chiave,
            **({"column_settings": {}} if not prefisso else {}),
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
    ),
    _indicatore(
        "ordini",
        "Ordini",
        "ordini",
        "Fatture distinte, resi esclusi. Una fattura con dodici prodotti "
        "resta un ordine solo.",
    ),
    _indicatore(
        "scontrino_medio",
        "Scontrino medio",
        "scontrino_medio",
        "Fatturato netto diviso ordini. I resi stanno al numeratore e non al "
        "denominatore: è voluto, e abbassa il valore.",
    ),
    _indicatore(
        "tasso_reso",
        "Tasso di reso",
        "tasso_reso_percentuale",
        "Valore dei resi sul fatturato lordo, in percentuale. Sul valore e non "
        "sul conteggio: un reso da mille sterline non pesa quanto uno da due.",
    ),
    _indicatore(
        "clienti_attivi",
        "Clienti attivi",
        "clienti_attivi",
        "Clienti distinti, escluso il membro Sconosciuto: contarlo "
        "significherebbe contare come uno solo un quinto delle righe.",
    ),
    # --- cruscotto 1: andamento (M7-T4) ------------------------------------
    Domanda(
        chiave="fatturato_per_mese",
        nome="Fatturato netto per mese",
        descrizione="Serie mensile del fatturato netto, con l'anno precedente "
        "a confronto. Il paragone è con lo stesso mese dell'anno prima, non con "
        "il mese precedente: la stagionalità qui è fortissima.",
        sql="""
select
    mese,
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
            "graph.dimensions": ["mese"],
            "graph.metrics": ["Anno selezionato", "Anno precedente"],
            "graph.x_axis.title_text": "Mese",
            "graph.y_axis.title_text": "Fatturato netto (£)",
        },
    ),
    Domanda(
        chiave="ordini_per_mese",
        nome="Ordini per mese",
        descrizione="Fatture distinte per mese, resi esclusi.",
        sql="""
select mese, ordini as "Ordini"
from marts.agg_indicatori_periodo
where livello = 'mese' and anno = {{anno}}
order by mese
""",
        display="bar",
        impostazioni={
            "graph.dimensions": ["mese"],
            "graph.metrics": ["Ordini"],
            "graph.x_axis.title_text": "Mese",
            "graph.y_axis.title_text": "Ordini",
        },
    ),
    Domanda(
        chiave="lordo_resi_netto",
        nome="Lordo, resi, netto",
        descrizione="Le tre misure insieme di proposito: il netto da solo "
        "nasconde quanto rientra, e il tasso di reso è uno dei cinque "
        "indicatori.",
        sql="""
select
    'Fatturato lordo' as voce, valore_lordo as importo, 1 as ordine
from marts.agg_indicatori_periodo
"""
        + SCELTA_RIGA
        + """
union all
select
    'Resi', -valore_resi, 2
from marts.agg_indicatori_periodo
"""
        + SCELTA_RIGA
        + """
union all
select
    'Fatturato netto', valore_netto, 3
from marts.agg_indicatori_periodo
"""
        + SCELTA_RIGA
        + """
order by ordine
""",
        display="table",
        impostazioni={"table.columns": []},
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
    p.descrizione as "Prodotto",
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
        },
    ),
    Domanda(
        chiave="distribuzione_scontrino",
        nome="Distribuzione dello scontrino",
        descrizione="Quante fatture per fascia di importo. La media da sola "
        "nasconde la forma e descrive un cliente che non esiste.",
        sql="""
with fatture as (
    select
        f.numero_fattura,
        sum(f.valore) as totale
    from marts.fct_vendite as f
    join marts.dim_data as d on f.data_key = d.data_key
    where not f.is_reso and d.anno = {{anno}}
    group by f.numero_fattura
    having sum(f.valore) > 0
)
select
    case
        when totale < 50 then '1. sotto 50'
        when totale < 150 then '2. da 50 a 150'
        when totale < 300 then '3. da 150 a 300'
        when totale < 600 then '4. da 300 a 600'
        when totale < 1500 then '5. da 600 a 1.500'
        else '6. oltre 1.500'
    end as "Fascia (£)",
    count(*) as "Fatture"
from fatture
group by 1
order by 1
""",
        display="bar",
        impostazioni={
            "graph.dimensions": ["Fascia (£)"],
            "graph.metrics": ["Fatture"],
            "graph.x_axis.title_text": "Importo della fattura",
            "graph.y_axis.title_text": "Numero di fatture",
        },
    ),
    Domanda(
        chiave="primi_clienti",
        nome="Primi clienti per fatturato",
        descrizione="Tabella e non grafico: sono valori da leggere, non da "
        "confrontare a colpo d'occhio. Sono rivenditori, non consumatori.",
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
    ),
    Domanda(
        chiave="prodotti_piu_resi",
        nome="Prodotti con il tasso di reso più alto",
        descrizione="Il tasso è sul valore, non sul numero di pezzi. Solo "
        "prodotti con almeno cento righe di vendita: su tre vendite un reso "
        "fa il 33 % e non significa niente.",
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
    descrizione as "Prodotto",
    round(resi / nullif(lordo, 0) * 100, 2) as "Tasso di reso (%)",
    round(lordo, 2) as "Fatturato lordo"
from per_prodotto
where righe >= 100 and lordo > 0
order by resi / nullif(lordo, 0) desc
limit 15
""",
        display="row",
        impostazioni={
            "graph.dimensions": ["Prodotto"],
            "graph.metrics": ["Tasso di reso (%)"],
        },
    ),
    # --- cruscotto 3: geografia (M7-T6) ------------------------------------
    Domanda(
        chiave="fatturato_per_paese",
        nome="Fatturato per paese, senza il Regno Unito",
        descrizione="Il Regno Unito è escluso ed è una scelta: vale il 91,9 % "
        "del fatturato, e con lui dentro tutte le altre barre diventano "
        "trattini indistinguibili. Il suo peso si legge nella barra impilata "
        "accanto, che è il posto giusto per una proporzione.",
        sql="""
select
    nome_paese as "Paese",
    round(valore_netto, 2) as "Fatturato netto"
from marts.agg_indicatori_periodo
where livello = 'anno_paese'
  and anno = {{anno}}
  and not is_regno_unito
order by valore_netto desc
limit 15
""",
        display="row",
        impostazioni={
            "graph.dimensions": ["Paese"],
            "graph.metrics": ["Fatturato netto"],
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
    case when is_regno_unito then 'Regno Unito' else 'Estero' end as "Mercato",
    round(sum(valore_netto), 2) as "Fatturato netto",
    round(sum(valore_netto) * 100.0 / sum(sum(valore_netto)) over (), 1) as "Quota (%)"
from marts.agg_indicatori_periodo
where livello = 'anno_paese' and anno = {{anno}}
group by is_regno_unito
order by sum(valore_netto) desc
""",
        display="table",
    ),
    Domanda(
        chiave="scheda_italia",
        nome="Scheda Italia",
        descrizione="Va letta sapendo quanto è piccolo il campione: la riga "
        "dice anche quanti clienti ci sono dietro. Un numero su quindici "
        "clienti non è una tendenza.",
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
    ),
]

DOMANDE_PER_CHIAVE = {d.chiave: d for d in DOMANDE}


@dataclass
class Scheda:
    """Una domanda dentro un cruscotto, con la sua posizione."""

    chiave: str
    riga: int
    colonna: int
    larghezza: int
    altezza: int


@dataclass
class Cruscotto:
    nome: str
    descrizione: str
    schede: list[Scheda]


# La griglia di Metabase è larga 24 colonne.
CRUSCOTTI: list[Cruscotto] = [
    Cruscotto(
        nome="1 — Andamento",
        descrizione="Come sta andando, rispetto a quando. I cinque indicatori "
        "in alto, la serie mensile sotto. Il confronto è con lo stesso mese "
        "dell'anno precedente: la stagionalità di un grossista di articoli da "
        "regalo è fortissima.",
        schede=[
            Scheda("fatturato_netto", 0, 0, 5, 3),
            Scheda("ordini", 0, 5, 4, 3),
            Scheda("scontrino_medio", 0, 9, 5, 3),
            Scheda("tasso_reso", 0, 14, 5, 3),
            Scheda("clienti_attivi", 0, 19, 5, 3),
            Scheda("fatturato_per_mese", 3, 0, 16, 7),
            Scheda("lordo_resi_netto", 3, 16, 8, 7),
            Scheda("ordini_per_mese", 10, 0, 24, 6),
        ],
    ),
    Cruscotto(
        nome="2 — Prodotti e clienti",
        descrizione="Cosa si vende, a chi, e cosa torna indietro.",
        schede=[
            Scheda("primi_prodotti", 0, 0, 12, 9),
            Scheda("primi_clienti", 0, 12, 12, 9),
            Scheda("distribuzione_scontrino", 9, 0, 12, 8),
            Scheda("prodotti_piu_resi", 9, 12, 12, 8),
        ],
    ),
    Cruscotto(
        nome="3 — Geografia",
        descrizione="Dove sono i clienti, e perché la scala inganna. Il Regno "
        "Unito è fuori dalla classifica di proposito.",
        schede=[
            Scheda("fatturato_per_paese", 0, 0, 14, 9),
            Scheda("interno_contro_estero", 0, 14, 10, 4),
            Scheda("scheda_italia", 4, 14, 10, 5),
        ],
    ),
]
