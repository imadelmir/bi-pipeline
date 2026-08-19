"""Formattazione dei numeri per i messaggi a schermo.

In questo progetto si contano righe a sei e sette cifre: `1067371` e `1.067.371`
sono lo stesso numero, ma il primo va riletto due volte per capire quanto vale.
Il separatore delle migliaia in italiano è il punto.

Non si usa `locale`: dipenderebbe dalle impostazioni della macchina, e lo stesso
comando darebbe uscite diverse su due computer.
"""


def numero(valore: int) -> str:
    """1067371 → «1.067.371»."""
    return f"{valore:,}".replace(",", ".")


def secondi(valore: float) -> str:
    """Durata leggibile: sotto il minuto in secondi, sopra in minuti e secondi."""
    if valore < 60:
        return f"{valore:.1f} s"
    minuti, resto = divmod(int(valore), 60)
    return f"{minuti} min {resto} s"
