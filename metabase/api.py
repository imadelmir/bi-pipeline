"""Un cliente minimo per l'API di Metabase.

Perché non `requests`: sarebbe una dipendenza in più per fare quattro chiamate
HTTP che la libreria standard sa già fare. Perché non a mano dall'interfaccia:
un cruscotto costruito a clic non è versionato, non si rifà su un'altra
macchina e non si legge in una pull request — cioè esattamente le tre cose che
questo progetto pretende dal resto della pipeline.

La sessione si tiene in memoria per la durata dello script.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

INDIRIZZO = f"http://localhost:{os.environ.get('METABASE_PORT', '3000')}"

# Metabase risponde «ok» all'health check prima di essere davvero pronto a
# ricevere configurazioni: si aspetta, ma non all'infinito.
ATTESA_MASSIMA = 300
INTERVALLO = 5


class ErroreMetabase(RuntimeError):
    """L'API ha risposto con un errore."""


class Metabase:
    def __init__(self, indirizzo: str = INDIRIZZO) -> None:
        self.indirizzo = indirizzo.rstrip("/")
        self.sessione: str | None = None

    # --- comunicazione -------------------------------------------------

    def chiama(
        self,
        metodo: str,
        percorso: str,
        corpo: dict[str, Any] | None = None,
    ) -> Any:
        richiesta = urllib.request.Request(
            f"{self.indirizzo}{percorso}",
            method=metodo,
            data=json.dumps(corpo).encode("utf-8") if corpo is not None else None,
            headers={"Content-Type": "application/json"},
        )
        if self.sessione:
            richiesta.add_header("X-Metabase-Session", self.sessione)

        try:
            with urllib.request.urlopen(richiesta) as risposta:
                testo = risposta.read().decode("utf-8")
        except urllib.error.HTTPError as errore:
            dettaglio = errore.read().decode("utf-8", errors="replace")
            raise ErroreMetabase(
                f"{metodo} {percorso} → {errore.code}\n{dettaglio[:800]}"
            ) from errore

        return json.loads(testo) if testo else None

    def get(self, percorso: str) -> Any:
        return self.chiama("GET", percorso)

    def post(self, percorso: str, corpo: dict[str, Any]) -> Any:
        return self.chiama("POST", percorso, corpo)

    def put(self, percorso: str, corpo: dict[str, Any]) -> Any:
        return self.chiama("PUT", percorso, corpo)

    # --- avvio ---------------------------------------------------------

    def aspetta(self) -> None:
        """Aspetta che l'istanza risponda, invece di fallire al primo tentativo."""
        scadenza = time.time() + ATTESA_MASSIMA
        while time.time() < scadenza:
            try:
                stato = self.get("/api/health")
            except Exception:
                # Qualsiasi errore qui significa «non è ancora pronto»:
                # connessione rifiutata, 503, risposta a metà.
                stato = None
            if isinstance(stato, dict) and stato.get("status") == "ok":
                return
            time.sleep(INTERVALLO)
        raise ErroreMetabase(f"Metabase non risponde dopo {ATTESA_MASSIMA} secondi")

    def proprieta(self) -> dict[str, Any]:
        risposta = self.get("/api/session/properties")
        return dict(risposta) if isinstance(risposta, dict) else {}

    def prepara_amministratore(self, email: str, password: str) -> bool:
        """Crea l'amministratore al primo avvio. Restituisce True se l'ha creato.

        Le credenziali arrivano da `.env`: non stanno nel codice e non
        finiscono in git.
        """
        proprieta = self.proprieta()

        if proprieta.get("has-user-setup"):
            return False

        token = proprieta.get("setup-token")
        if not token:
            raise ErroreMetabase(
                "l'istanza non è configurata ma non fornisce un token di setup"
            )

        risposta = self.post(
            "/api/setup",
            {
                "token": token,
                "user": {
                    "first_name": "Imad",
                    "last_name": "El Mir",
                    "email": email,
                    "password": password,
                    "site_name": "BI Pipeline",
                },
                "prefs": {
                    "site_name": "BI Pipeline",
                    "site_locale": "it",
                    # Nessuna telemetria: è un progetto locale.
                    "allow_tracking": False,
                },
            },
        )
        self.sessione = risposta.get("id") if isinstance(risposta, dict) else None
        return True

    def entra(self, email: str, password: str) -> None:
        risposta = self.post("/api/session", {"username": email, "password": password})
        if not isinstance(risposta, dict) or "id" not in risposta:
            raise ErroreMetabase("l'accesso non ha restituito una sessione")
        self.sessione = str(risposta["id"])
