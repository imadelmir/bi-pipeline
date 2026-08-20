# I cruscotti

Tre pagine, quindici schede, due filtri comuni. Ogni domanda è definita in
[`metabase/domande.py`](domande.py) e si ricostruisce con un comando:

```bash
uv run python -m metabase.prepara      # database, utente di lettura, sincronizzazione
uv run python -m metabase.configura    # domande e cruscotti
```

Nessuna scheda è stata costruita a clic. Un cruscotto disegnato
nell'interfaccia vive su una macchina sola: quando quella macchina si perde,
si perde anche il lavoro, e nessuno può leggere in una pull request cosa è
cambiato.

## L'aspetto

**Il font e i colori dell'interfaccia non si possono cambiare** nell'edizione
open source di Metabase: sono dietro la funzionalità `whitelabel`, e un
`PUT /api/setting/application-font` risponde 500 dicendolo. Le impostazioni
sono comunque scritte in [`metabase/aspetto.py`](aspetto.py), che le prova e
riporta l'esito: il giorno che l'istanza cambiasse edizione, non c'è niente da
riscrivere.

Quello che si può fare — e che conta di più — si imposta **per colonna e per
scheda**, in [`metabase/formati.py`](formati.py) e accanto a ogni domanda:

| Cosa | Come |
| --- | --- |
| Importi | Sterline con il simbolo e il separatore delle migliaia; forma compatta (£ 9,0 Mln) sui numeri singoli, cifre intere nelle tabelle |
| Percentuali | Due decimali e il simbolo, senza moltiplicare due volte |
| Colori delle serie | Blu per la serie principale, viola tratteggiato per l'anno precedente, salmone per i resi, verde per le distribuzioni |
| Variazioni | I cinque indicatori mostrano sotto quanto sono cambiati rispetto all'anno prima |
| Assi | Titolo solo dove serve: «Fatturato netto» sull'asse dei valori, niente sull'asse dei mesi, che si capisce da solo |

Le tre pagine hanno anche **titoli di sezione e note di lettura**: una pagina di
soli numeri costringe chi la guarda a indovinare cosa sta guardando, e due righe
accanto a un grafico valgono più di un grafico in più.

## La regola che vale su tutte le pagine

**I calcoli stanno in dbt.** Le domande leggono
`marts.agg_indicatori_periodo` e `marts.agg_indicatori_giorno`, che
contengono gli indicatori già calcolati, e si limitano a scegliere una riga o
a sommare colonne additive. Dentro Metabase non c'è nessuna formula: se serve
un numero nuovo, nasce in un modello.

## I filtri comuni

| Filtro | Valori | Predefinito |
| --- | --- | --- |
| Anno | 2009, 2010, 2011 | 2011 |
| Paese | `tutti` oppure il nome normalizzato | `tutti` |

Sono **obbligatori**, e non è pigrizia. `agg_indicatori_periodo` contiene
cinque livelli di aggregazione nella stessa tabella: senza un filtro che ne
scelga uno, una somma prenderebbe insieme il totale e i suoi addendi,
restituendo il doppio del fatturato senza che nulla lo segnali.

Il filtro **«con o senza resi» del piano non è stato realizzato come
interruttore**. Le tre misure — lordo, resi, netto — si vedono insieme nella
scheda «Lordo, resi, netto» del primo cruscotto. Un interruttore avrebbe un
difetto: chi guarda lo schermo non sa in quale delle due posizioni si trova,
e un fatturato senza resi somiglia moltissimo a un fatturato con pochi resi.
Tre numeri affiancati dicono sempre quale si sta guardando.

## Cruscotto 1 — Andamento

Come sta andando, rispetto a quando.

| Scheda | Tipo | Cosa mostra |
| --- | --- | --- |
| Fatturato netto | numero | `SUM(valore)`, resi compresi come negativi |
| Ordini | numero | Fatture distinte, resi esclusi |
| Scontrino medio | numero | Netto diviso ordini |
| Tasso di reso | numero | Valore dei resi sul lordo, in percentuale |
| Clienti attivi | numero | Clienti distinti, *Sconosciuto* escluso |
| Fatturato netto per mese | linea | Due serie: anno scelto e anno precedente |
| Lordo, resi, netto | tabella | Le tre misure insieme |
| Ordini per mese | barre | Fatture per mese |

Il confronto è con **lo stesso mese dell'anno precedente**, non con il mese
prima: la stagionalità di un grossista di articoli da regalo è fortissima, e
novembre confrontato con ottobre direbbe solo che si avvicina il Natale.

## Cruscotto 2 — Prodotti e clienti

Cosa si vende, a chi, e cosa torna indietro.

| Scheda | Tipo | Nota |
| --- | --- | --- |
| Primi dodici prodotti per valore | barre orizzontali | I nomi sono lunghi: in verticale non si leggono |
| Primi clienti per fatturato | tabella | Valori da leggere, non da confrontare |
| Distribuzione dello scontrino | istogramma | La media da sola descrive un cliente che non esiste |
| Prodotti con il tasso di reso più alto | barre orizzontali | Solo prodotti con almeno cento righe |

La soglia delle cento righe non è estetica: su tre vendite, un reso fa il
33 % e non significa niente.

**Dodici prodotti e non venti**, come sarebbe naturale in una classifica:
Metabase raggruppa da sé le barre che non entrano nell'altezza della scheda in
una voce «Altro», e con venti prodotti quella voce diventava la seconda barra
più lunga del grafico senza dire niente. Le impostazioni per disattivarlo
vengono salvate ma ignorate: l'unica strada che non dipende dalla dimensione
della finestra di chi guarda è chiedere meno righe.

## Cruscotto 3 — Geografia

Dove sono i clienti, e perché la scala inganna.

| Scheda | Tipo | Nota |
| --- | --- | --- |
| Fatturato per paese, senza il Regno Unito | barre orizzontali | Il Regno Unito è escluso di proposito |
| Mercato interno contro estero | tabella con quote | Provata anche come barra impilata: con l'84 % da una parte, la fetta piccola diventa una riga sottile |
| Scheda Italia | tabella | Con il numero di clienti accanto |

**Il Regno Unito è fuori dalla classifica.** Vale il 91,9 % delle righe e
l'84 % del fatturato del 2011: lasciandolo dentro, la sua barra arriva a fondo
pagina e tutte le altre diventano trattini indistinguibili. Il suo peso si
legge nella scheda accanto, che è il posto giusto per una proporzione.

**La scheda Italia mostra anche quanti clienti ci sono dietro**, ed è il
motivo per cui esiste in questa forma: nel 2011 sono dodici clienti e
trentatré ordini. Un numero costruito su dodici clienti non è una tendenza, e
il cruscotto lo dice invece di far finta di niente.

## Cosa non c'è, e perché

- **Niente torte.** Confrontare due fette simili in un cerchio è impossibile,
  e affiancare due periodi lo è ancora di più.
- **Niente mappe di calore.** Su quarantatré paesi è decorazione: le stesse
  informazioni si leggono meglio in una classifica ordinata.
- **Nessun indicatore di margine.** Serve il costo d'acquisto, che questi dati
  non contengono. Inventarlo renderebbe finto tutto il resto.
