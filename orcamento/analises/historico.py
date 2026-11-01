"""Histórico: planejado × realizado e taxa de poupança."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from ..config import ATENCAO, OK, PERIGO
from ..modelos import Dados, somar_meses
from ..motor import MesProj, mes_corrente


@dataclass
class MesHistorico:
    mes: date
    situacao_mes: str                  # Fechado | Em andamento | Futuro
    receita: float
    teto: float
    variaveis: Optional[float]
    desvio: Optional[float]
    desvio_pct: Optional[float]
    saldo: Optional[float]
    planejado_poupar: float
    poupado: Optional[float]
    taxa_real: Optional[float]
    taxa_planejada: Optional[float]
    resultado: str


@dataclass
class ResumoHistorico:
    meses_com_dados: int
    meses_no_teto: int
    desvio_acumulado: float
    taxa_realizada: Optional[float]


def poupado_no_mes(dados: Dados, mes: date) -> float:
    fim = somar_meses(mes, 1)
    dep = sum(m.valor or 0 for m in dados.mov_reserva if m.tipo == "Depósito" and m.data and mes <= m.data < fim)
    ret = sum(m.valor or 0 for m in dados.mov_reserva if m.tipo == "Retirada" and m.data and mes <= m.data < fim)
    return dep - ret


def analisar_historico(dados: Dados, proj: list[MesProj], hoje: Optional[date] = None) -> tuple[list[MesHistorico], ResumoHistorico]:
    atual = mes_corrente(hoje)
    linhas: list[MesHistorico] = []
    for p in proj:
        lancado = p.fonte == "Lançado"
        situacao = "Fechado" if p.mes < atual else ("Em andamento" if (p.mes == atual or lancado) else "Futuro")
        var = p.variaveis if (situacao != "Futuro" and lancado) else None
        desvio = None if var is None else var - p.teto
        desvio_pct = None if var is None or p.teto <= 0 else desvio / p.teto
        saldo = None if var is None else p.saldo
        poupado = None if situacao == "Futuro" else _poupado(dados, p.mes)
        planejado = p.aporte_total
        if var is None:
            resultado = "SEM DADOS" if situacao == "Fechado" else "—"
        else:
            resultado = OK if desvio <= 0 else (ATENCAO if (desvio_pct or 0) <= 0.1 else PERIGO)
        linhas.append(MesHistorico(p.mes, situacao, p.receita, p.teto, var, desvio, desvio_pct, saldo, planejado, poupado,
                                   (poupado / p.receita) if (poupado is not None and p.receita) else None,
                                   planejado / p.receita if p.receita else None, resultado))
    com_poup = [l for l in linhas if l.poupado is not None]
    denom = sum(l.receita for l in com_poup)
    resumo = ResumoHistorico(
        sum(1 for l in linhas if l.variaveis is not None), sum(1 for l in linhas if l.resultado == OK),
        sum(l.desvio or 0 for l in linhas), (sum(l.poupado for l in com_poup) / denom) if denom else None)
    return linhas, resumo


def _poupado(dados: Dados, mes: date) -> float:
    return poupado_no_mes(dados, mes)
