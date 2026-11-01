"""Reserva de emergência: saldo real, custo essencial e metas por etapa."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Union

from ..modelos import Dados
from ..motor import MesProj, mes_da_projecao


@dataclass
class Etapa:
    nome: str
    meta: float
    ja_tenho: float
    falta: float
    pct: float
    previsao: Union[date, str]   # data prevista, "Concluída" ou "além de 36 meses"


@dataclass
class CustoEssencial:
    fixas: float
    variaveis: float
    parcelas: float
    calculado: float
    usado: float


@dataclass
class SituacaoReserva:
    saldo_real: float
    planejado_no_mes: float
    diferenca: float
    custo: CustoEssencial
    meses_cobertura: float
    proxima_meta: float
    etapas: list[Etapa]


def saldo_real(dados: Dados) -> float:
    """Saldo inicial + depósitos − retiradas registrados."""
    dep = sum(m.valor or 0 for m in dados.mov_reserva if m.tipo == "Depósito")
    ret = sum(m.valor or 0 for m in dados.mov_reserva if m.tipo == "Retirada")
    return dados.cfg.saldo_inicial_reserva + dep - ret


def custo_essencial(dados: Dados, proj: list[MesProj]) -> CustoEssencial:
    """Custo mensal essencial no 1º mês: fixas essenciais + variáveis essenciais lançados (+ parcelas)."""
    primeiro = proj[0].mes
    fixas = sum(f.valor_no_mes(primeiro) for f in dados.fixas if f.classificacao == "Essencial")
    var = sum(l.valor or 0 for l in dados.lancamentos if l.mes == primeiro and l.bloco == "Variável" and l.classificacao == "Essencial")
    parc = proj[0].parcelas if dados.cfg.incluir_parcelas_custo_essencial else 0.0
    calc = fixas + var + parc
    manual = dados.cfg.custo_essencial_manual
    return CustoEssencial(fixas, var, parc, calc, manual if manual is not None else calc)


def previsao_etapa(proj: list[MesProj], meta: float, saldo: float) -> Union[date, str]:
    if saldo >= meta:
        return "Concluída"
    for p in proj:
        if p.reserva_saldo >= meta:
            return p.mes
    return "além de 36 meses"


def situacao_reserva(dados: Dados, proj: list[MesProj], mes: date) -> SituacaoReserva:
    saldo = saldo_real(dados)
    custo = custo_essencial(dados, proj)
    nomes = [("Etapa 1 — Primeiro colchão", dados.cfg.meta_reserva),
             ("Etapa 2 — 1 mês de contas essenciais", custo.usado * 1),
             ("Etapa 3 — 3 meses de contas essenciais", custo.usado * 3),
             ("Etapa 4 — 6 meses (reserva completa)", custo.usado * 6)]
    etapas = [Etapa(n, m, saldo, max(0.0, m - saldo), min(1.0, max(0.0, saldo / m)) if m else 0.0, previsao_etapa(proj, m, saldo)) for n, m in nomes]
    proxima = next((e.meta for e in etapas if saldo < e.meta), etapas[-1].meta)
    planejado = mes_da_projecao(proj, mes).reserva_saldo
    return SituacaoReserva(saldo, planejado, saldo - planejado, custo, saldo / custo.usado if custo.usado else 0.0, proxima, etapas)
