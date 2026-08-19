"""Profilazione della sorgente (M2-T3).

Si guarda il dato *prima* di scrivere qualsiasi trasformazione. Il piano
contiene una tabella intitolata «Lo sporco che ci aspettiamo»: è un'ipotesi,
non un dato acquisito, e questo modulo la verifica riga per riga sostituendo a
ogni «circa» un numero misurato.

Produce `docs/profilazione.md`, che è il materiale grezzo della relazione di
milestone. Il file si rigenera con un comando: se domani la sorgente cambia,
i numeri si aggiornano invece di restare veri per sempre in un documento.

Uso:

    uv run python -m ingestion.profilazione
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from ingestion.formato import numero
from ingestion.percorsi import CARTELLA_CSV, RADICE

# I codici di servizio nominati nel piano. Non sono prodotti: sono spese di
# spedizione, commissioni bancarie, rettifiche manuali. Qui si contano soltanto;
# l'esclusione vera avviene in staging (M3-T6), con una seed.
CODICI_DI_SERVIZIO = ["POST", "DOT", "M", "BANK CHARGES", "AMAZONFEE", "CARRIAGE"]

# Un codice prodotto vero è cinque cifre, a volte seguite da una o due lettere
# (85123A). Tutto ciò che non ha questa forma va guardato a mano.
FORMA_CODICE_PRODOTTO = r"^\d{5}[A-Za-z]{0,2}$"

RELAZIONE = RADICE / "docs" / "profilazione.md"


def carica(cartella: Path) -> pd.DataFrame:
    """Legge i CSV prodotti dalla conversione e li unisce in una tabella sola.

    I tipi sono dichiarati invece che indovinati: `Invoice` e `StockCode` sono
    testo anche quando sembrano numeri, e lasciarli interpretare a pandas
    trasformerebbe `537434` in un intero e `C536379` in una stringa — due tipi
    diversi nella stessa colonna, che è il modo più rapido per contare male.
    """
    file_csv = sorted(cartella.glob("vendite_*.csv"))
    if not file_csv:
        raise FileNotFoundError(
            f"nessun CSV in {cartella}: esegui prima "
            "`uv run python -m ingestion.sources.online_retail`"
        )

    pezzi: list[pd.DataFrame] = []
    for percorso in file_csv:
        pezzo = pd.read_csv(
            percorso,
            dtype={
                "Invoice": "string",
                "StockCode": "string",
                "Description": "string",
                "Quantity": "int64",
                "Price": "float64",
                "Customer ID": "float64",
                "Country": "string",
            },
            parse_dates=["InvoiceDate"],
        )
        pezzo["file_origine"] = percorso.name
        pezzi.append(pezzo)
        print(f"letto {percorso.name}: {numero(len(pezzo))} righe")

    return pd.concat(pezzi, ignore_index=True)


def _riga_tabella(valori: list[str]) -> str:
    return "| " + " | ".join(valori) + " |"


def _percentuale(parte: int, totale: int) -> str:
    return f"{parte / totale * 100:.2f} %".replace(".", ",")


def colonne(dati: pd.DataFrame) -> list[str]:
    """Per ogni colonna: nulli, valori distinti, minimo e massimo."""
    righe = [
        _riga_tabella(["Colonna", "Nulli", "% nulli", "Distinti", "Minimo", "Massimo"]),
        _riga_tabella(["---"] * 6),
    ]

    totale = len(dati)
    for nome in dati.columns:
        if nome == "file_origine":
            continue
        colonna = dati[nome]
        nulli = int(colonna.isna().sum())
        distinti = int(colonna.nunique(dropna=True))

        senza_nulli = colonna.dropna()
        if senza_nulli.empty:
            minimo = massimo = "—"
        else:
            minimo = str(senza_nulli.min())
            massimo = str(senza_nulli.max())

        righe.append(
            _riga_tabella(
                [
                    f"`{nome}`",
                    numero(nulli),
                    _percentuale(nulli, totale),
                    numero(distinti),
                    minimo,
                    massimo,
                ]
            )
        )

    return righe


def sporco_atteso(dati: pd.DataFrame) -> tuple[list[str], dict[str, int]]:
    """Verifica una per una le ipotesi della tabella «Lo sporco che ci aspettiamo»."""
    totale = len(dati)
    conteggi: dict[str, int] = {}

    resi = dati["Invoice"].str.startswith("C", na=False)
    conteggi["resi"] = int(resi.sum())

    conteggi["cliente_mancante"] = int(dati["Customer ID"].isna().sum())

    e_servizio = dati["StockCode"].isin(CODICI_DI_SERVIZIO)
    conteggi["codici_di_servizio"] = int(e_servizio.sum())

    fuori_forma = ~dati["StockCode"].str.match(FORMA_CODICE_PRODOTTO, na=False)
    conteggi["codici_fuori_forma"] = int(fuori_forma.sum())

    conteggi["prezzo_zero"] = int((dati["Price"] == 0).sum())
    conteggi["prezzo_negativo"] = int((dati["Price"] < 0).sum())

    chiave = ["Invoice", "StockCode", "Quantity", "InvoiceDate"]
    conteggi["duplicati"] = int(dati.duplicated(subset=chiave).sum())

    conteggi["descrizione_mancante"] = int(dati["Description"].isna().sum())

    descrizioni_per_codice = dati.groupby("StockCode", observed=True)[
        "Description"
    ].nunique()
    conteggi["codici_con_piu_descrizioni"] = int((descrizioni_per_codice > 1).sum())

    descrizioni = dati["Description"].dropna()
    conteggi["descrizioni_con_spazi"] = int(
        (descrizioni != descrizioni.str.strip()).sum()
    )
    conteggi["descrizioni_non_maiuscole"] = int(
        (descrizioni != descrizioni.str.upper()).sum()
    )

    conteggi["quantita_negativa"] = int((dati["Quantity"] < 0).sum())
    conteggi["reso_con_quantita_positiva"] = int((resi & (dati["Quantity"] > 0)).sum())
    conteggi["non_reso_con_quantita_negativa"] = int(
        (~resi & (dati["Quantity"] < 0)).sum()
    )

    righe = [
        _riga_tabella(["Ipotesi del piano", "Misurato", "Quota", "Verdetto"]),
        _riga_tabella(["---"] * 4),
        _riga_tabella(
            [
                "Fatture che iniziano per `C` (resi)",
                numero(conteggi["resi"]),
                _percentuale(conteggi["resi"], totale),
                "confermata",
            ]
        ),
        _riga_tabella(
            [
                "`Customer ID` mancante «in circa un quarto delle righe»",
                numero(conteggi["cliente_mancante"]),
                _percentuale(conteggi["cliente_mancante"], totale),
                "confermata",
            ]
        ),
        _riga_tabella(
            [
                "Codici di servizio nominati nel piano",
                numero(conteggi["codici_di_servizio"]),
                _percentuale(conteggi["codici_di_servizio"], totale),
                "confermata",
            ]
        ),
        _riga_tabella(
            [
                "Codici fuori dalla forma «5 cifre + lettere»",
                numero(conteggi["codici_fuori_forma"]),
                _percentuale(conteggi["codici_fuori_forma"], totale),
                "da guardare a mano, elenco sotto",
            ]
        ),
        _riga_tabella(
            [
                "Prezzo pari a zero",
                numero(conteggi["prezzo_zero"]),
                _percentuale(conteggi["prezzo_zero"], totale),
                "confermata",
            ]
        ),
        _riga_tabella(
            [
                "Prezzo negativo",
                numero(conteggi["prezzo_negativo"]),
                _percentuale(conteggi["prezzo_negativo"], totale),
                "confermata",
            ]
        ),
        _riga_tabella(
            [
                "Righe duplicate esatte (fattura, prodotto, quantità, istante)",
                numero(conteggi["duplicati"]),
                _percentuale(conteggi["duplicati"], totale),
                "confermata",
            ]
        ),
        _riga_tabella(
            [
                "Descrizione mancante",
                numero(conteggi["descrizione_mancante"]),
                _percentuale(conteggi["descrizione_mancante"], totale),
                "confermata",
            ]
        ),
        _riga_tabella(
            [
                "Codici con più di una descrizione",
                numero(conteggi["codici_con_piu_descrizioni"]),
                "—",
                "confermata",
            ]
        ),
        _riga_tabella(
            [
                "Descrizioni con spazi iniziali o finali",
                numero(conteggi["descrizioni_con_spazi"]),
                _percentuale(conteggi["descrizioni_con_spazi"], totale),
                "confermata",
            ]
        ),
        _riga_tabella(
            [
                "Descrizioni non in maiuscolo",
                numero(conteggi["descrizioni_non_maiuscole"]),
                _percentuale(conteggi["descrizioni_non_maiuscole"], totale),
                "confermata",
            ]
        ),
        _riga_tabella(
            [
                "Quantità negativa",
                numero(conteggi["quantita_negativa"]),
                _percentuale(conteggi["quantita_negativa"], totale),
                "confermata",
            ]
        ),
        _riga_tabella(
            [
                "Reso (`C`) con quantità positiva",
                numero(conteggi["reso_con_quantita_positiva"]),
                _percentuale(conteggi["reso_con_quantita_positiva"], totale),
                "controllo di coerenza (M5-T6)",
            ]
        ),
        _riga_tabella(
            [
                "Non reso con quantità negativa",
                numero(conteggi["non_reso_con_quantita_negativa"]),
                _percentuale(conteggi["non_reso_con_quantita_negativa"], totale),
                "controllo di coerenza (M5-T6)",
            ]
        ),
    ]

    return righe, conteggi


def anomalie_dei_segni(dati: pd.DataFrame, quante: int = 10) -> list[str]:
    """Le righe dove segno della quantità e prefisso della fattura non tornano.

    È la scoperta che vale di più di tutta la profilazione: se queste righe
    arrivassero nel fatto, il test di coerenza dei resi (M5-T6) fallirebbe.
    Qui si guarda cosa sono davvero, prima di decidere come trattarle.
    """
    resi = dati["Invoice"].str.startswith("C", na=False)

    negative = dati[~resi & (dati["Quantity"] < 0)]
    reso_positivo = dati[resi & (dati["Quantity"] > 0)]

    a_prezzo_zero = int((negative["Price"] == 0).sum())
    senza_cliente = int(negative["Customer ID"].isna().sum())

    righe = [
        "Righe con quantità negativa su una fattura che **non** inizia per `C`: "
        f"**{numero(len(negative))}**.",
        "",
        f"Di queste, con prezzo pari a zero: **{numero(a_prezzo_zero)}**. "
        f"Senza `Customer ID`: **{numero(senza_cliente)}**.",
        "",
        "Le descrizioni più frequenti dicono cosa sono:",
        "",
        _riga_tabella(["Descrizione", "Righe"]),
        _riga_tabella(["---"] * 2),
    ]

    frequenti = negative["Description"].fillna("*(nulla)*").value_counts()
    for descrizione, quantita in frequenti.head(quante).items():
        righe.append(_riga_tabella([str(descrizione), numero(int(quantita))]))

    righe += [
        "",
        "Non sono vendite né resi: sono rettifiche di magazzino — merce rotta,",
        "smarrita, buttata, o un controllo di inventario. Hanno tutte prezzo zero,",
        "quindi **l'esclusione dei prezzi non positivi (M3-T7) le toglie già tutte**.",
        "",
        "All'opposto, righe con quantità positiva su una fattura che inizia per "
        f"`C`: **{numero(len(reso_positivo))}**.",
        "",
    ]

    if not reso_positivo.empty:
        righe += [
            _riga_tabella(["Fattura", "Codice", "Descrizione", "Quantità", "Prezzo"]),
            _riga_tabella(["---"] * 5),
        ]
        for _, riga in reso_positivo.iterrows():
            righe.append(
                _riga_tabella(
                    [
                        f"`{riga['Invoice']}`",
                        f"`{riga['StockCode']}`",
                        str(riga["Description"]),
                        str(riga["Quantity"]),
                        str(riga["Price"]),
                    ]
                )
            )
        righe += [
            "",
            "Il codice è `M`, cioè *Manual*: un codice di servizio, non un prodotto.",
            "**L'esclusione dei codici di servizio (M3-T6) toglie anche questa.**",
            "",
            "> Da ricordare in M5: i due test di coerenza dei resi passano *perché*",
            "> due esclusioni a monte tolgono di mezzo i casi storti. Chi un giorno",
            "> allentasse la regola sui prezzi si troverebbe a rompere un test che",
            "> sta in un altro file e parla di un'altra cosa.",
        ]

    return righe


def codici_non_standard(dati: pd.DataFrame, quanti: int = 30) -> list[str]:
    """I codici che non hanno la forma di un codice prodotto, con quante righe."""
    fuori_forma = ~dati["StockCode"].str.match(FORMA_CODICE_PRODOTTO, na=False)
    conteggio = dati.loc[fuori_forma, "StockCode"].value_counts()

    righe = [
        _riga_tabella(["Codice", "Righe", "Descrizione più frequente"]),
        _riga_tabella(["---"] * 3),
    ]
    for codice, quante in conteggio.head(quanti).items():
        descrizioni = dati.loc[dati["StockCode"] == codice, "Description"].dropna()
        frequente = descrizioni.mode()
        etichetta = str(frequente.iloc[0]) if not frequente.empty else "—"
        righe.append(_riga_tabella([f"`{codice}`", numero(int(quante)), etichetta]))

    if len(conteggio) > quanti:
        righe.append(
            _riga_tabella(
                [f"…e altri {numero(len(conteggio) - quanti)} codici", "", ""]
            )
        )

    return righe


def paesi(dati: pd.DataFrame) -> list[str]:
    """Tutti i valori della colonna Country, con righe e clienti distinti."""
    conteggio = dati["Country"].value_counts()
    clienti = dati.groupby("Country", observed=True)["Customer ID"].nunique()

    righe = [
        _riga_tabella(["Paese", "Righe", "% righe", "Clienti distinti"]),
        _riga_tabella(["---"] * 4),
    ]
    totale = len(dati)
    for paese, quante in conteggio.items():
        righe.append(
            _riga_tabella(
                [
                    str(paese),
                    numero(int(quante)),
                    _percentuale(int(quante), totale),
                    numero(int(clienti.get(paese, 0))),
                ]
            )
        )
    return righe


def scrivi_relazione(dati: pd.DataFrame, destinazione: Path) -> Path:
    totale = len(dati)
    primo = dati["InvoiceDate"].min()
    ultimo = dati["InvoiceDate"].max()

    per_file = dati["file_origine"].value_counts().sort_index()
    righe_per_file = [
        _riga_tabella(["File", "Righe"]),
        _riga_tabella(["---"] * 2),
    ]
    for nome, quante in per_file.items():
        righe_per_file.append(_riga_tabella([f"`{nome}`", numero(int(quante))]))
    righe_per_file.append(_riga_tabella(["**Totale**", f"**{numero(totale)}**"]))

    tabella_sporco, _ = sporco_atteso(dati)

    testo = "\n".join(
        [
            "# Profilazione della sorgente",
            "",
            "Generato da `uv run python -m ingestion.profilazione` il "
            f"{datetime.now().astimezone():%d/%m/%Y} (M2-T3).",
            "",
            "Non si scrive una sola trasformazione prima di aver contato cosa c'è",
            "dentro. Le ipotesi del piano — la tabella «Lo sporco che ci",
            "aspettiamo» — sono verificate qui sotto una per una.",
            "",
            "## Righe per file",
            "",
            *righe_per_file,
            "",
            f"Periodo coperto: dal {primo:%d/%m/%Y %H:%M} al {ultimo:%d/%m/%Y %H:%M}.",
            "",
            "## Le colonne",
            "",
            *colonne(dati),
            "",
            "## Lo sporco atteso, verificato",
            "",
            *tabella_sporco,
            "",
            "## Quando il segno e la fattura non vanno d'accordo",
            "",
            *anomalie_dei_segni(dati),
            "",
            "## I codici che non sono prodotti",
            "",
            "Un codice prodotto vero è cinque cifre, a volte seguite da una o due",
            "lettere. Tutto il resto è qui sotto: da qui nasce la seed",
            "`codici_di_servizio.csv` di M3-T6.",
            "",
            *codici_non_standard(dati),
            "",
            "## I paesi",
            "",
            "La colonna è testo libero e contiene voci che paesi non sono.",
            "La normalizzazione avviene in `dim_paese` (M4-T4), con una tabella di",
            "raccordo versionata.",
            "",
            *paesi(dati),
            "",
        ]
    )

    destinazione.write_text(testo, encoding="utf-8")
    return destinazione


def main() -> int:
    dati = carica(CARTELLA_CSV)
    print(f"totale: {numero(len(dati))} righe")

    percorso = scrivi_relazione(dati, RELAZIONE)
    print(f"scritto {percorso}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
