"""Gastos futuros incertos: projeção em três cenários (confirmado, esperado, pior caso)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ..config import ATENCAO, OK, PERIGO
from ..modelos import Dados, GastoFuturo
from ..motor import MesProj
from .reserva import saldo_real

INATIVAS = ("Descartada", "Já lançado")


def peso(dados: Dados, g: GastoFuturo) -> float:
    """Probabilidade usada: 0 (descartada/já lançado), 1 (confirmada) ou a da chance."""
    if g.situacao in INATIVAS:
        return 0.0
    if g.situacao == "Confirmada":
        return 1.0
    return dados.cfg.peso_chance(g.chance)


@dataclass
class MesFuturo:
    mes: date
    receita: float
    despesas: float
    saldo_confirmado: float
    esperado: float
    saldo_esperado: float
    pior_caso: float
    saldo_pior: float
    situacao: str


@dataclass
class ResumoFuturos:
    pior_caso: float
    esperado: float
    reserva: float
    reserva_cobre: str
    meses_negativos: int
    itens_sem_mes: int


def projecao_futuros(dados: Dados, proj: list[MesProj], mes: date, n: int = 12) -> list[MesFuturo]:
    inicio = next((i for i, p in enumerate(proj) if p.mes == mes), 0)
    linhas = []
    for p in proj[inicio:inicio + n]:
        doMes = [g for g in dados.gastos_futuros if g.mes == p.mes and g.valor]
        esperado = sum(g.valor * peso(dados, g) for g in doMes)
        pior = sum(g.valor for g in doMes if g.situacao not in INATIVAS)
        s_conf = p.receita - p.total
        s_esp, s_pior = s_conf - esperado, s_conf - pior
        sit = OK if s_pior >= 0 else (ATENCAO if s_esp >= 0 else PERIGO)
        linhas.append(MesFuturo(p.mes, p.receita, p.total, s_conf, esperado, s_esp, pior, s_pior, sit))
    return linhas


def resumo_futuros(dados: Dados, proj: list[MesProj], mes: date) -> ResumoFuturos:
    ativos = [g for g in dados.gastos_futuros if g.valor and g.situacao not in INATIVAS]
    pior = sum(g.valor for g in ativos)
    esperado = sum(g.valor * peso(dados, g) for g in ativos)
    reserva = saldo_real(dados)
    if pior == 0:
        texto = "Nenhum gasto possível registrado."
    elif reserva >= pior:
        texto = "Sim: a reserva cobre até o pior caso."
    elif reserva >= esperado:
        texto = "Em parte: cobre o valor esperado, mas não o pior caso."
    else:
        texto = "Não: a reserva ainda não cobre nem o valor esperado. Risco de recorrer a cartão ou empréstimo."
    linhas = projecao_futuros(dados, proj, mes)
    return ResumoFuturos(pior, esperado, reserva, texto, sum(1 for l in linhas if l.saldo_pior < 0),
                         sum(1 for g in dados.gastos_futuros if g.descricao and g.mes is None))
