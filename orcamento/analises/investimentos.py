"""Carteira de investimentos, regra de liberação e simulador de aportes."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ..config import OBJETIVOS, TIPOS_INVESTIMENTO
from ..modelos import Dados
from ..motor import MesProj, mes_da_projecao
from .reserva import custo_essencial, saldo_real


@dataclass
class ResumoCarteira:
    aplicado: float
    atual: float
    resultado: float
    resultado_pct: float
    por_tipo: dict[str, float]
    por_objetivo: dict[str, float]
    aplicado_como_reserva: float
    saldo_reserva: float
    confere: bool


@dataclass
class Liberacao:
    reserva_real: float
    reserva_minima: float
    saldo_mes: float
    liberado: bool
    mensagem: str


def resumo_carteira(dados: Dados) -> ResumoCarteira:
    aplicado = sum(i.aplicado or 0 for i in dados.investimentos)
    atual = sum(i.atual or 0 for i in dados.investimentos)
    tipos = {t: sum(i.atual or 0 for i in dados.investimentos if i.tipo == t) for t in TIPOS_INVESTIMENTO}
    objs = {o: sum(i.atual or 0 for i in dados.investimentos if i.objetivo == o) for o in OBJETIVOS}
    reserva_apl = objs.get("Reserva de emergência", 0.0)
    saldo = saldo_real(dados)
    return ResumoCarteira(aplicado, atual, atual - aplicado, (atual / aplicado - 1) if aplicado else 0.0,
                          tipos, objs, reserva_apl, saldo, abs(reserva_apl - saldo) < 0.5)


def liberacao_para_investir(dados: Dados, proj: list[MesProj], mes: date) -> Liberacao:
    reserva = saldo_real(dados)
    minima = dados.cfg.reserva_minima_investir
    if minima is None:
        minima = custo_essencial(dados, proj).usado  # Etapa 2: 1 mês de contas essenciais
    saldo = mes_da_projecao(proj, mes).saldo
    ok = reserva >= minima and saldo >= 0
    msg = ("LIBERADO: reserva no nível mínimo e mês no azul. Pode começar aportes regulares." if ok else
           "AINDA NÃO: a prioridade é completar a reserva e fechar o mês no azul.")
    return Liberacao(reserva, minima, saldo, ok, msg)


def simular_aportes(aporte: float, taxa_anual: float, inicial: float, prazos=(12, 24, 36, 60)) -> list[tuple[int, float, float, float]]:
    """(meses, total aportado, valor estimado, rendimento). Rendimento líquido anual → taxa mensal equivalente."""
    saida = []
    for n in prazos:
        aportado = inicial + aporte * n
        if taxa_anual == 0:
            final = aportado
        else:
            i = (1 + taxa_anual) ** (1 / 12) - 1
            final = inicial * (1 + taxa_anual) ** (n / 12) + aporte * (((1 + taxa_anual) ** (n / 12) - 1) / i)
        saida.append((n, aportado, final, final - aportado))
    return saida
