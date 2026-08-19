"""Scaricamento e conversione della sorgente Online Retail II (M2-T1, M2-T2).

Fa tre cose, in quest'ordine:

1. scarica l'archivio da UCI, se non c'è già;
2. ne estrae l'Excel e verifica lo SHA-256 contro il valore atteso;
3. converte i due fogli in due CSV, una volta sola.

Il punto 2 è il motivo per cui questo modulo esiste. Un file scaricato può
arrivare troncato, o la sorgente può cambiare senza dirlo: in entrambi i casi
la pipeline continuerebbe a girare producendo numeri diversi, e nessuno se ne
accorgerebbe. Il checksum trasforma quel silenzio in un errore.

Il punto 3 esiste perché leggere 43,5 MB di Excel a ogni esecuzione costa
minuti: openpyxl deve interpretare XML compresso cella per cella. I CSV si
producono una volta e da lì in poi si legge quelli.

Uso:

    uv run python -m ingestion.sources.online_retail
    uv run python -m ingestion.sources.online_retail --forza
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

from ingestion.formato import numero
from ingestion.percorsi import CARTELLA_CSV, CARTELLA_GREZZI, prepara_cartelle

# La pagina della scheda è https://archive.ics.uci.edu/dataset/502/online+retail+ii
# Questo è il collegamento diretto all'archivio, l'unico che non richiede
# di passare dal browser.
URL_ARCHIVIO = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"

NOME_ARCHIVIO = "online+retail+ii.zip"
NOME_EXCEL = "online_retail_II.xlsx"

# SHA-256 dell'Excel, misurato al primo scaricamento del 19/08/2026 e da allora
# atteso identico. UCI non pubblica un checksum ufficiale: questo valore dice
# «il file è lo stesso di quando il progetto è stato scritto», non «il file è
# quello che UCI ha voluto pubblicare». La differenza è dichiarata in
# docs/decisioni.md, D6.
SHA256_EXCEL = "bcbe73b35f5b7babf197fb0cb983a11f5d9ff929078d4aa53d171b1f2df2e980"

# Quanto si legge per volta durante lo scaricamento e il calcolo del checksum.
# Un megabyte: abbastanza da non fare miliardi di chiamate, poco da non tenere
# in memoria un file da 43 MB.
BLOCCO = 1024 * 1024


class ChecksumNonCorrispondente(RuntimeError):
    """Il file scaricato non è quello atteso."""


def calcola_sha256(percorso: Path) -> str:
    """Legge il file a blocchi e ne restituisce lo SHA-256 in esadecimale."""
    digest = hashlib.sha256()
    with percorso.open("rb") as file:
        while blocco := file.read(BLOCCO):
            digest.update(blocco)
    return digest.hexdigest()


def scarica_archivio(destinazione: Path, forza: bool = False) -> Path:
    """Scarica l'archivio da UCI. Se c'è già e non si forza, non fa niente."""
    archivio = destinazione / NOME_ARCHIVIO

    if archivio.exists() and not forza:
        print(f"archivio già presente: {archivio.name}")
        return archivio

    print(f"scarico {URL_ARCHIVIO}")

    # Si scrive prima in un file temporaneo e si rinomina alla fine: se lo
    # scaricamento si interrompe a metà, resta un .parziale invece di un
    # archivio incompleto che al giro dopo sembrerebbe valido.
    parziale = archivio.with_suffix(archivio.suffix + ".parziale")
    with urllib.request.urlopen(URL_ARCHIVIO) as risposta, parziale.open("wb") as file:
        shutil.copyfileobj(risposta, file, BLOCCO)
    parziale.replace(archivio)

    megabyte = archivio.stat().st_size / 1024 / 1024
    print(f"scaricato: {archivio.name}, {megabyte:.1f} MB")
    return archivio


def estrai_excel(archivio: Path, destinazione: Path) -> Path:
    """Estrae l'unico .xlsx contenuto nell'archivio."""
    with zipfile.ZipFile(archivio) as zip_file:
        nomi = [n for n in zip_file.namelist() if n.endswith(".xlsx")]
        if len(nomi) != 1:
            raise RuntimeError(
                f"nell'archivio ci sono {len(nomi)} file .xlsx invece di uno: {nomi}"
            )
        zip_file.extract(nomi[0], destinazione)

    estratto = destinazione / nomi[0]
    atteso = destinazione / NOME_EXCEL
    if estratto != atteso:
        estratto.replace(atteso)
    return atteso


def verifica_checksum(excel: Path) -> str:
    """Confronta lo SHA-256 con quello atteso e alza un errore se differisce."""
    calcolato = calcola_sha256(excel)

    if calcolato != SHA256_EXCEL:
        raise ChecksumNonCorrispondente(
            f"\n  Il file scaricato non è quello atteso.\n"
            f"  file:      {excel}\n"
            f"  atteso:    {SHA256_EXCEL}\n"
            f"  calcolato: {calcolato}\n\n"
            f"  Può voler dire due cose: lo scaricamento si è rotto a metà — e\n"
            f"  allora basta rilanciare con --forza — oppure la sorgente è\n"
            f"  cambiata. Nel secondo caso non si aggiorna il valore atteso e\n"
            f"  basta: si guarda cosa è cambiato, perché tutti i numeri del\n"
            f"  progetto sono stati misurati sul file precedente."
        )

    print(f"checksum verificato: {calcolato}")
    return calcolato


def _nome_csv(nome_foglio: str) -> str:
    """Da «Year 2009-2010» a «vendite_2009_2010.csv»."""
    anni = re.findall(r"\d{4}", nome_foglio)
    if len(anni) == 2:
        return f"vendite_{anni[0]}_{anni[1]}.csv"

    # Il foglio non ha il nome atteso: si tiene il suo, ripulito. Meglio un
    # nome brutto che una conversione che si ferma.
    ripulito = re.sub(r"[^a-z0-9]+", "_", nome_foglio.lower()).strip("_")
    return f"vendite_{ripulito}.csv"


def converti_in_csv(excel: Path, destinazione: Path, forza: bool = False) -> list[Path]:
    """Scrive un CSV per ogni foglio dell'Excel e restituisce i percorsi.

    Non è una trasformazione: è un cambio di formato. Nessuna colonna viene
    tolta, rinominata o filtrata — quello che c'è nell'Excel finisce nel CSV.
    """
    prodotti: list[Path] = []

    with pd.ExcelFile(excel) as libro:
        fogli = list(libro.sheet_names)
        print(f"fogli trovati: {fogli}")

        for foglio in fogli:
            csv = destinazione / _nome_csv(str(foglio))

            if csv.exists() and not forza:
                print(f"  {csv.name}: già presente")
                prodotti.append(csv)
                continue

            print(f"  {foglio}: lettura in corso…")
            dati = libro.parse(foglio)
            dati.to_csv(csv, index=False)
            print(f"  {csv.name}: {numero(len(dati))} righe")
            prodotti.append(csv)

    return prodotti


def main(argomenti: list[str] | None = None) -> int:
    lettore = argparse.ArgumentParser(
        description="Scarica Online Retail II da UCI, ne verifica il checksum "
        "e converte i fogli in CSV."
    )
    lettore.add_argument(
        "--forza",
        action="store_true",
        help="riscarica e riconverte anche se i file ci sono già",
    )
    opzioni = lettore.parse_args(argomenti)

    prepara_cartelle()

    archivio = scarica_archivio(CARTELLA_GREZZI, forza=opzioni.forza)
    excel = estrai_excel(archivio, CARTELLA_GREZZI)
    verifica_checksum(excel)

    csv = converti_in_csv(excel, CARTELLA_CSV, forza=opzioni.forza)
    print(f"pronti {len(csv)} CSV in {CARTELLA_CSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
