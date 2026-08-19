"""Rispecchia `docs/backlog.md` su GitHub: etichette, milestone, issue, progetto.

La fonte di verità resta il file nel repository. Questo script non contiene
nessun elenco di task: legge il markdown, e da lì crea ciò che manca su GitHub.
Rilanciarlo non duplica niente — è pensato per essere eseguito ogni volta che il
backlog cambia o che una milestone si chiude.

Serve `gh` autenticato, con lo scope `project` per i Projects v2:

    gh auth status
    gh auth refresh -h github.com -s project

Uso:

    uv run python scripts/backlog_su_github.py --completate M1,M2
    uv run python scripts/backlog_su_github.py --completate M1,M2 --prova
"""

from __future__ import annotations

import argparse
import io
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Su Windows, quando l'uscita finisce in un file o in una pipe, Python usa
# cp1252: una freccia «→» in un messaggio di stato fa morire lo script dopo
# che ha già creato settantotto issue. Stessa protezione che sta in
# ingestion/__init__.py, ripetuta qui perché questo script non importa quel
# pacchetto.
for _flusso in (sys.stdout, sys.stderr):
    if isinstance(_flusso, io.TextIOWrapper) and _flusso.encoding.lower() != "utf-8":
        _flusso.reconfigure(encoding="utf-8", errors="replace")

RADICE = Path(__file__).resolve().parent.parent
BACKLOG = RADICE / "docs" / "backlog.md"

# Stesso schema di nome dei progetti già esistenti dell'autore
# ("Portfolio Roadmap", "Football Analytics - Roadmap").
TITOLO_PROGETTO = "BI Pipeline - Roadmap"

# Le etichette del backlog, con un colore che le rende distinguibili a colpo
# d'occhio nella lista delle issue.
ETICHETTE: dict[str, tuple[str, str]] = {
    "M1": ("0e8a16", "Milestone 1 — Fondamenta"),
    "M2": ("0e8a16", "Milestone 2 — Ingestione"),
    "M3": ("0e8a16", "Milestone 3 — Staging"),
    "M4": ("0e8a16", "Milestone 4 — Schema a stella"),
    "M5": ("0e8a16", "Milestone 5 — Qualità"),
    "M6": ("0e8a16", "Milestone 6 — Orchestrazione"),
    "M7": ("0e8a16", "Milestone 7 — Cruscotti"),
    "M8": ("0e8a16", "Milestone 8 — Pubblicazione"),
    "ingestione": ("1d76db", "Tutto ciò che tocca lo strato raw"),
    "dbt": ("ff694b", "Modelli, test, documentazione dbt"),
    "modellazione": ("5319e7", "Decisioni sullo schema a stella"),
    "qualità": ("fbca04", "Test e controlli"),
    "infra": ("c5def5", "Docker, CI, Makefile"),
    "dashboard": ("509ee3", "Metabase"),
    "documentazione": ("d4c5f9", "Relazioni di milestone, README"),
    "bloccante": ("b60205", "Impedisce di procedere"),
}

RIGA_MILESTONE = re.compile(r"^## (M\d) — (.+)$")
RIGA_TASK = re.compile(r"^### (M\d-T\d+) · (.+)$")
RIGA_ETICHETTE = re.compile(r"^Etichette: (.+)$")
RIGA_OBIETTIVO = re.compile(r"^Obiettivo: (.+)$")


@dataclass
class Task:
    codice: str
    titolo: str
    corpo: list[str] = field(default_factory=list)
    etichette: list[str] = field(default_factory=list)

    @property
    def milestone(self) -> str:
        return self.codice.split("-")[0]

    @property
    def titolo_issue(self) -> str:
        return f"{self.codice} · {self.titolo}"

    def descrizione(self, repo: str) -> str:
        testo = "\n".join(self.corpo).strip()
        collegamento = f"https://github.com/{repo}/blob/main/docs/backlog.md"
        return (
            f"{testo}\n\n---\n\nTask `{self.codice}` del backlog di progetto: "
            f"[`docs/backlog.md`]({collegamento}).\n"
        )


@dataclass
class Milestone:
    codice: str
    nome: str
    obiettivo: str = ""

    @property
    def titolo(self) -> str:
        return f"{self.codice} — {self.nome}"


def leggi_backlog(percorso: Path) -> tuple[list[Milestone], list[Task]]:
    """Estrae milestone e task dal markdown. Nessun elenco scritto a mano."""
    milestone: list[Milestone] = []
    task: list[Task] = []
    corrente: Task | None = None

    for riga in percorso.read_text(encoding="utf-8").splitlines():
        se_milestone = RIGA_MILESTONE.match(riga)
        if se_milestone:
            corrente = None
            milestone.append(Milestone(se_milestone[1], se_milestone[2].strip()))
            continue

        se_obiettivo = RIGA_OBIETTIVO.match(riga)
        if se_obiettivo and milestone and not milestone[-1].obiettivo:
            milestone[-1].obiettivo = se_obiettivo[1].strip()
            continue

        se_task = RIGA_TASK.match(riga)
        if se_task:
            corrente = Task(se_task[1], se_task[2].strip())
            task.append(corrente)
            continue

        if corrente is None:
            continue

        se_etichette = RIGA_ETICHETTE.match(riga)
        if se_etichette:
            corrente.etichette = re.findall(r"`([^`]+)`", se_etichette[1])
            continue

        if riga.startswith("## ") or riga.strip() == "---":
            corrente = None
            continue

        corrente.corpo.append(riga)

    return milestone, task


# Segni di un errore di rete, non di un comando sbagliato. Su questi vale la
# pena riprovare: l'API di GitHub ogni tanto chiude una connessione, e non c'è
# motivo di buttare via un'esecuzione che ha già creato settantotto issue.
ERRORI_DI_RETE = (
    "wsarecv",
    "timeout",
    "connection",
    "eof",
    "reset by peer",
    "502",
    "503",
    "secondary rate limit",
)

TENTATIVI = 3


def gh(*argomenti: str, silenzioso: bool = False) -> str:
    """Esegue `gh` e restituisce l'uscita.

    Ritenta solo gli errori di rete, e solo quelli: un comando sbagliato
    fallisce subito, perché riprovarlo darebbe lo stesso errore tre volte più
    tardi.
    """
    ultimo_errore = ""

    for tentativo in range(1, TENTATIVI + 1):
        esito = subprocess.run(
            ["gh", *argomenti],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        if esito.returncode == 0:
            return esito.stdout.strip()

        ultimo_errore = esito.stderr.strip()
        di_rete = any(s in ultimo_errore.lower() for s in ERRORI_DI_RETE)
        if not di_rete or tentativo == TENTATIVI:
            break

        attesa = 2 * tentativo
        print(f"    rete instabile, riprovo fra {attesa} s ({tentativo}/{TENTATIVI})")
        time.sleep(attesa)

    if silenzioso:
        return ""
    raise RuntimeError(f"gh {' '.join(argomenti)} è fallito:\n{ultimo_errore}")


def gh_json(*argomenti: str) -> Any:
    return json.loads(gh(*argomenti))


def repository() -> str:
    return str(gh_json("repo", "view", "--json", "nameWithOwner")["nameWithOwner"])


def sincronizza_etichette(prova: bool) -> None:
    print("etichette")
    for nome, (colore, descrizione) in ETICHETTE.items():
        if prova:
            print(f"  [prova] {nome}")
            continue
        # --force aggiorna colore e descrizione se l'etichetta esiste già.
        gh(
            "label",
            "create",
            nome,
            "--color",
            colore,
            "--description",
            descrizione,
            "--force",
        )
        print(f"  {nome}")


def sincronizza_milestone(milestone: list[Milestone], repo: str, prova: bool) -> None:
    print("milestone")
    esistenti = {
        str(m["title"]): m
        for m in gh_json("api", f"repos/{repo}/milestones?state=all&per_page=100")
    }

    for m in milestone:
        if m.titolo in esistenti:
            print(f"  {m.titolo}: c'è già")
            continue
        if prova:
            print(f"  [prova] {m.titolo}")
            continue
        gh(
            "api",
            f"repos/{repo}/milestones",
            "-f",
            f"title={m.titolo}",
            "-f",
            f"description={m.obiettivo}",
            silenzioso=True,
        )
        print(f"  {m.titolo}: creata")


def issue_esistenti() -> dict[str, dict[str, Any]]:
    """Le issue del repository, indicizzate per codice del task (M1-T1)."""
    elenco = gh_json(
        "issue",
        "list",
        "--state",
        "all",
        "--limit",
        "500",
        "--json",
        "number,title,state,url",
    )
    per_codice: dict[str, dict[str, Any]] = {}
    for issue in elenco:
        primo = str(issue["title"]).split(" ")[0]
        if re.fullmatch(r"M\d-T\d+", primo):
            per_codice[primo] = issue
    return per_codice


def sincronizza_issue(
    task: list[Task],
    milestone: list[Milestone],
    completate: set[str],
    repo: str,
    prova: bool,
) -> dict[str, dict[str, Any]]:
    print("issue")
    titolo_milestone = {m.codice: m.titolo for m in milestone}
    esistenti = issue_esistenti()

    for t in task:
        issue = esistenti.get(t.codice)

        if issue is None:
            if prova:
                print(f"  [prova] creo {t.titolo_issue}")
                continue
            etichette = [t.milestone, *t.etichette]
            url = gh(
                "issue",
                "create",
                "--title",
                t.titolo_issue,
                "--body",
                t.descrizione(repo),
                "--milestone",
                titolo_milestone[t.milestone],
                *[argomento for e in etichette for argomento in ("--label", e)],
            )
            print(f"  creata {t.codice}: {url}")

            # Lo stato si applica subito: se la milestone è già chiusa, questa
            # issue nasce e viene chiusa nello stesso giro. Rimandarlo alla
            # prossima esecuzione significherebbe che una sola esecuzione non
            # basta a mettere GitHub d'accordo con il backlog.
            if t.milestone in completate:
                numero_issue = url.rstrip("/").split("/")[-1]
                gh(
                    "issue",
                    "close",
                    numero_issue,
                    "--reason",
                    "completed",
                    "--comment",
                    f"Completato in {t.milestone}. La relazione della milestone "
                    f"è in `docs/milestones/`.",
                )
                print(f"  chiusa {t.codice}")
            continue

        # L'issue c'è: si controlla solo che lo stato sia quello giusto.
        deve_essere_chiusa = t.milestone in completate
        aperta = str(issue["state"]).upper() == "OPEN"

        if deve_essere_chiusa and aperta:
            if prova:
                print(f"  [prova] chiudo {t.codice}")
            else:
                gh(
                    "issue",
                    "close",
                    str(issue["number"]),
                    "--reason",
                    "completed",
                    "--comment",
                    f"Completato in {t.milestone}. La relazione della milestone "
                    f"è in `docs/milestones/`.",
                )
                print(f"  chiusa {t.codice}")
        elif not deve_essere_chiusa and not aperta:
            if prova:
                print(f"  [prova] riapro {t.codice}")
            else:
                gh("issue", "reopen", str(issue["number"]))
                print(f"  riaperta {t.codice}")
        else:
            print(f"  {t.codice}: già a posto")

    return issue_esistenti()


def _progetto(owner: str, prova: bool) -> dict[str, Any] | None:
    """Trova il progetto per titolo, o lo crea."""
    elenco = gh_json("project", "list", "--owner", owner, "--format", "json")
    for progetto in elenco.get("projects", []):
        if str(progetto["title"]) == TITOLO_PROGETTO:
            return dict(progetto)

    if prova:
        print(f"  [prova] creo il progetto «{TITOLO_PROGETTO}»")
        return None

    creato = gh_json(
        "project",
        "create",
        "--owner",
        owner,
        "--title",
        TITOLO_PROGETTO,
        "--format",
        "json",
    )
    print(f"  creato il progetto: {creato['url']}")
    return dict(creato)


def sincronizza_progetto(
    task: list[Task],
    issue: dict[str, dict[str, Any]],
    completate: set[str],
    owner: str,
    prova: bool,
) -> None:
    """Mette ogni issue nel progetto e le dà lo stato giusto.

    Lo stato non si deduce dal progetto ma dalle milestone completate: la
    fonte resta il repository, il progetto è solo la vista.
    """
    print("progetto")
    progetto = _progetto(owner, prova)
    if progetto is None:
        return

    numero = str(progetto["number"])
    id_progetto = str(progetto["id"])

    voci = gh_json(
        "project",
        "item-list",
        numero,
        "--owner",
        owner,
        "--format",
        "json",
        "--limit",
        "500",
    )["items"]
    per_url = {
        str(v["content"]["url"]): v for v in voci if isinstance(v.get("content"), dict)
    }

    campi = gh_json(
        "project", "field-list", numero, "--owner", owner, "--format", "json"
    )["fields"]
    stato = next((c for c in campi if str(c["name"]) == "Status"), None)
    if stato is None:
        raise RuntimeError("il progetto non ha un campo Status")
    opzioni = {str(o["name"]): str(o["id"]) for o in stato["options"]}

    for t in task:
        dati_issue = issue.get(t.codice)
        if dati_issue is None:
            continue
        url = str(dati_issue["url"])

        voce = per_url.get(url)
        if voce is None:
            if prova:
                print(f"  [prova] aggiungo {t.codice}")
                continue
            voce = gh_json(
                "project",
                "item-add",
                numero,
                "--owner",
                owner,
                "--url",
                url,
                "--format",
                "json",
            )

        atteso = "Done" if t.milestone in completate else "Todo"
        attuale = str(voce.get("status") or "")
        if attuale == atteso:
            continue

        if prova:
            print(f"  [prova] {t.codice} → {atteso}")
            continue

        gh(
            "project",
            "item-edit",
            "--id",
            str(voce["id"]),
            "--project-id",
            id_progetto,
            "--field-id",
            str(stato["id"]),
            "--single-select-option-id",
            opzioni[atteso],
        )
        print(f"  {t.codice} → {atteso}")


def chiudi_milestone(
    milestone: list[Milestone], completate: set[str], repo: str, prova: bool
) -> None:
    print("stato delle milestone")
    esistenti = {
        str(m["title"]): m
        for m in gh_json("api", f"repos/{repo}/milestones?state=all&per_page=100")
    }

    for m in milestone:
        remota = esistenti.get(m.titolo)
        if remota is None:
            continue
        stato_atteso = "closed" if m.codice in completate else "open"
        if str(remota["state"]) == stato_atteso:
            continue
        if prova:
            print(f"  [prova] {m.titolo} → {stato_atteso}")
            continue
        gh(
            "api",
            "--method",
            "PATCH",
            f"repos/{repo}/milestones/{remota['number']}",
            "-f",
            f"state={stato_atteso}",
            silenzioso=True,
        )
        print(f"  {m.titolo} → {stato_atteso}")


def main() -> int:
    lettore = argparse.ArgumentParser(
        description="Rispecchia docs/backlog.md su GitHub: etichette, milestone, issue."
    )
    lettore.add_argument(
        "--completate",
        default="",
        help="milestone già chiuse, separate da virgola (es. M1,M2): "
        "le loro issue vengono chiuse",
    )
    lettore.add_argument(
        "--prova",
        action="store_true",
        help="dice cosa farebbe senza toccare niente",
    )
    opzioni = lettore.parse_args()

    completate = {c.strip() for c in opzioni.completate.split(",") if c.strip()}

    milestone, task = leggi_backlog(BACKLOG)
    print(f"letti {len(milestone)} milestone e {len(task)} task da {BACKLOG.name}")
    if completate:
        print(f"considerate completate: {', '.join(sorted(completate))}")
    print()

    repo = repository()
    print(f"repository: {repo}\n")

    sincronizza_etichette(opzioni.prova)
    print()
    sincronizza_milestone(milestone, repo, opzioni.prova)
    print()
    issue = sincronizza_issue(task, milestone, completate, repo, opzioni.prova)
    print()
    chiudi_milestone(milestone, completate, repo, opzioni.prova)
    print()
    sincronizza_progetto(task, issue, completate, repo.split("/")[0], opzioni.prova)

    return 0


if __name__ == "__main__":
    sys.exit(main())
