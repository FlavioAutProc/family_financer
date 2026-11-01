"""Formatação de valores no padrão brasileiro."""
from __future__ import annotations

from datetime import date, datetime

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
         "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]


def moeda(valor: float | None, vazio: str = "—") -> str:
    """1234.5 -> 'R$ 1.234,50' (negativos: '-R$ 39,04')."""
    if valor is None:
        return vazio
    texto = f"{abs(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"-R$ {texto}" if valor < -0.004 else f"R$ {texto}"


def pct(valor: float | None, casas: int = 1, vazio: str = "—") -> str:
    if valor is None:
        return vazio
    return f"{valor * 100:.{casas}f}%".replace(".", ",")


def mes_extenso(d: date | None) -> str:
    return "—" if d is None else f"{MESES[d.month - 1]} de {d.year}"


def mes_abrev(d: date | None) -> str:
    return "—" if d is None else f"{MESES[d.month - 1][:3]}/{str(d.year)[2:]}"


def data_br(d: date | datetime | None) -> str:
    return "—" if d is None else d.strftime("%d/%m/%Y")


def numero(valor: float | None, casas: int = 0) -> str:
    if valor is None:
        return "—"
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
