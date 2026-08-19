# Profilazione della sorgente

Generato da `uv run python -m ingestion.profilazione` il 20/08/2026 (M2-T3).

Non si scrive una sola trasformazione prima di aver contato cosa c'è
dentro. Le ipotesi del piano — la tabella «Lo sporco che ci
aspettiamo» — sono verificate qui sotto una per una.

## Righe per file

| File | Righe |
| --- | --- |
| `vendite_2009_2010.csv` | 525.461 |
| `vendite_2010_2011.csv` | 541.910 |
| **Totale** | **1.067.371** |

Periodo coperto: dal 01/12/2009 07:45 al 09/12/2011 12:50.

## Le colonne

| Colonna | Nulli | % nulli | Distinti | Minimo | Massimo |
| --- | --- | --- | --- | --- | --- |
| `Invoice` | 0 | 0,00 % | 53.628 | 489434 | C581569 |
| `StockCode` | 0 | 0,00 % | 5.305 | 10002 | m |
| `Description` | 4.382 | 0,41 % | 5.698 |   DOORMAT UNION JACK GUNS AND ROSES | wrongly sold sets |
| `Quantity` | 0 | 0,00 % | 1.057 | -80995 | 80995 |
| `InvoiceDate` | 0 | 0,00 % | 47.635 | 2009-12-01 07:45:00 | 2011-12-09 12:50:00 |
| `Price` | 0 | 0,00 % | 2.807 | -53594.36 | 38970.0 |
| `Customer ID` | 243.007 | 22,77 % | 5.942 | 12346.0 | 18287.0 |
| `Country` | 0 | 0,00 % | 43 | Australia | West Indies |

## Lo sporco atteso, verificato

| Ipotesi del piano | Misurato | Quota | Verdetto |
| --- | --- | --- | --- |
| Fatture che iniziano per `C` (resi) | 19.494 | 1,83 % | confermata |
| `Customer ID` mancante «in circa un quarto delle righe» | 243.007 | 22,77 % | confermata |
| Codici di servizio nominati nel piano | 5.134 | 0,48 % | confermata |
| Codici fuori dalla forma «5 cifre + lettere» | 6.094 | 0,57 % | da guardare a mano, elenco sotto |
| Prezzo pari a zero | 6.202 | 0,58 % | confermata |
| Prezzo negativo | 5 | 0,00 % | confermata |
| Righe duplicate esatte (fattura, prodotto, quantità, istante) | 34.604 | 3,24 % | confermata |
| Descrizione mancante | 4.382 | 0,41 % | confermata |
| Codici con più di una descrizione | 1.232 | — | confermata |
| Descrizioni con spazi iniziali o finali | 213.035 | 19,96 % | confermata |
| Descrizioni non in maiuscolo | 5.967 | 0,56 % | confermata |
| Quantità negativa | 22.950 | 2,15 % | confermata |
| Reso (`C`) con quantità positiva | 1 | 0,00 % | controllo di coerenza (M5-T6) |
| Non reso con quantità negativa | 3.457 | 0,32 % | controllo di coerenza (M5-T6) |

## Quando il segno e la fattura non vanno d'accordo

Righe con quantità negativa su una fattura che **non** inizia per `C`: **3.457**.

Di queste, con prezzo pari a zero: **3.457**. Senza `Customer ID`: **3.457**.

Le descrizioni più frequenti dicono cosa sono:

| Descrizione | Righe |
| --- | --- |
| *(nulla)* | 2.689 |
| check | 123 |
| damages | 84 |
| ? | 83 |
| damaged | 78 |
| missing | 27 |
| sold as set on dotcom | 20 |
| Damaged | 17 |
| smashed | 9 |
| thrown away | 9 |

Non sono vendite né resi: sono rettifiche di magazzino — merce rotta,
smarrita, buttata, o un controllo di inventario. Hanno tutte prezzo zero,
quindi **l'esclusione dei prezzi non positivi (M3-T7) le toglie già tutte**.

All'opposto, righe con quantità positiva su una fattura che inizia per `C`: **1**.

| Fattura | Codice | Descrizione | Quantità | Prezzo |
| --- | --- | --- | --- | --- |
| `C496350` | `M` | Manual | 1 | 373.57 |

Il codice è `M`, cioè *Manual*: un codice di servizio, non un prodotto.
**L'esclusione dei codici di servizio (M3-T6) toglie anche questa.**

> Da ricordare in M5: i due test di coerenza dei resi passano *perché*
> due esclusioni a monte tolgono di mezzo i casi storti. Chi un giorno
> allentasse la regola sui prezzi si troverebbe a rompere un test che
> sta in un altro file e parla di un'altra cosa.

## I codici che non sono prodotti

Un codice prodotto vero è cinque cifre, a volte seguite da una o due
lettere. Tutto il resto è qui sotto: da qui nasce la seed
`codici_di_servizio.csv` di M3-T6.

| Codice | Righe | Descrizione più frequente |
| --- | --- | --- |
| `POST` | 2.122 | POSTAGE |
| `DOT` | 1.446 | DOTCOM POSTAGE |
| `M` | 1.421 | Manual |
| `C2` | 282 | CARRIAGE |
| `D` | 177 | Discount |
| `S` | 104 | SAMPLES |
| `BANK CHARGES` | 102 | Bank Charges |
| `ADJUST` | 67 | Adjustment by john on 26/01/2010 16 |
| `AMAZONFEE` | 43 | AMAZON FEE |
| `DCGS0058` | 31 | MISO PRETTY  GUM |
| `gift_0001_20` | 29 | Dotcomgiftshop Gift Voucher £20.00 |
| `gift_0001_30` | 29 | Dotcomgiftshop Gift Voucher £30.00 |
| `DCGSSGIRL` | 25 | GIRLS PARTY BAG |
| `DCGSSBOY` | 23 | BOYS PARTY BAG |
| `PADS` | 19 | PADS TO MATCH ALL CUSHIONS |
| `gift_0001_10` | 16 | Dotcomgiftshop Gift Voucher £10.00 |
| `CRUK` | 16 | CRUK Commission |
| `DCGS0076` | 15 | SUNJAR LED NIGHT NIGHT LIGHT |
| `TEST001` | 15 | This is a test product. |
| `DCGS0003` | 14 | BOXED GLASS ASHTRAY |
| `gift_0001_50` | 8 | Dotcomgiftshop Gift Voucher £50.00 |
| `gift_0001_40` | 7 | Dotcomgiftshop Gift Voucher £40.00 |
| `DCGS0069` | 6 | OOH LA LA DOGS COLLAR |
| `B` | 6 | Adjust bad debt |
| `DCGS0004` | 5 | HAYNES CAMPER SHOULDER BAG |
| `m` | 5 | Manual |
| `gift_0001_80` | 4 | Dotcomgiftshop Gift Voucher £80.00 |
| `DCGS0072` | 4 | CAT CAMOUFLAGUE COLLAR |
| `DCGS0066N` | 4 | NAVY CUDDLES DOG HOODIE |
| `DCGS0068` | 3 | DOGS NIGHT COLLAR |
| …e altri 33 codici |  |  |

## I paesi

La colonna è testo libero e contiene voci che paesi non sono.
La normalizzazione avviene in `dim_paese` (M4-T4), con una tabella di
raccordo versionata.

| Paese | Righe | % righe | Clienti distinti |
| --- | --- | --- | --- |
| United Kingdom | 981.330 | 91,94 % | 5.410 |
| EIRE | 17.866 | 1,67 % | 5 |
| Germany | 17.624 | 1,65 % | 107 |
| France | 14.330 | 1,34 % | 95 |
| Netherlands | 5.140 | 0,48 % | 23 |
| Spain | 3.811 | 0,36 % | 41 |
| Switzerland | 3.189 | 0,30 % | 22 |
| Belgium | 3.123 | 0,29 % | 29 |
| Portugal | 2.620 | 0,25 % | 24 |
| Australia | 1.913 | 0,18 % | 15 |
| Channel Islands | 1.664 | 0,16 % | 14 |
| Italy | 1.534 | 0,14 % | 17 |
| Norway | 1.455 | 0,14 % | 13 |
| Sweden | 1.364 | 0,13 % | 19 |
| Cyprus | 1.176 | 0,11 % | 11 |
| Finland | 1.049 | 0,10 % | 15 |
| Austria | 938 | 0,09 % | 13 |
| Denmark | 817 | 0,08 % | 12 |
| Unspecified | 756 | 0,07 % | 7 |
| Greece | 663 | 0,06 % | 5 |
| Japan | 582 | 0,05 % | 10 |
| USA | 535 | 0,05 % | 9 |
| Poland | 535 | 0,05 % | 6 |
| United Arab Emirates | 500 | 0,05 % | 4 |
| Israel | 371 | 0,03 % | 4 |
| Hong Kong | 364 | 0,03 % | 0 |
| Singapore | 346 | 0,03 % | 1 |
| Malta | 299 | 0,03 % | 2 |
| Iceland | 253 | 0,02 % | 1 |
| Canada | 228 | 0,02 % | 5 |
| Lithuania | 189 | 0,02 % | 1 |
| RSA | 169 | 0,02 % | 2 |
| Bahrain | 126 | 0,01 % | 2 |
| Brazil | 94 | 0,01 % | 2 |
| Thailand | 76 | 0,01 % | 1 |
| Korea | 63 | 0,01 % | 2 |
| European Community | 61 | 0,01 % | 1 |
| Lebanon | 58 | 0,01 % | 1 |
| West Indies | 54 | 0,01 % | 1 |
| Bermuda | 34 | 0,00 % | 0 |
| Nigeria | 32 | 0,00 % | 1 |
| Czech Republic | 30 | 0,00 % | 1 |
| Saudi Arabia | 10 | 0,00 % | 1 |
