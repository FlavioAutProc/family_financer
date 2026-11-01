"""Extras (13º, férias...) e provisões anuais (cofrinho)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Union

from ..config import OK, PERIGO
from ..modelos import Dados, somar_meses
from ..motor import MesProj, provisao_mensal
from .reserva import custo_essencial, saldo_real, previsao_etapa


def partes_extra(dados: Dados, valor: float) -> dict[str, float]:
    c = dados.cfg
    return {"reserva": valor * c.destino_reserva, "dividas": valor * c.destino_dividas,
            "investir": valor * c.destino_investir, "livre": valor * c.destino_livre}


def soma_percentuais(dados: Dados) -> float:
    c = dados.cfg
    return c.destino_reserva + c.destino_dividas + c.destino_investir + c.destino_livre


@dataclass
class MesExtras:
    mes: date
    extras: float
    reserva: float
    dividas: float
    investir: float
    livre: float
    provisao_guardada: float
    provisoes_a_pagar: float
    cofrinho: float
    situacao_cofrinho: str
    reserva_com_extras: float
    necessidade_por_mes: float


@dataclass
class EtapaComExtras:
    nome: str
    meta: float
    pelo_plano: Union[date, str]
    com_extras: Union[date, str]
    antecipa_meses: Union[int, None]


@dataclass
class ResultadoExtras:
    linha: list[MesExtras]
    provisao_sugerida: float
    provisao_usada: float
    primeiro_mes_no_vermelho: Union[date, None]
    guardar_para_nunca_faltar: float
    etapas: list[EtapaComExtras]


def vencimento_no_mes(dados: Dados, mes: date) -> float:
    """Provisões que vencem no mês (a conta se repete todo ano, a partir do 1º vencimento)."""
    return sum(p.valor or 0 for p in dados.provisoes
               if p.situacao != "Pausada" and p.mes and p.valor and mes >= p.mes and mes.month == p.mes.month)


def analisar_extras(dados: Dados, proj: list[MesProj]) -> ResultadoExtras:
    prov = provisao_mensal(dados)
    sugerida = sum(p.valor or 0 for p in dados.provisoes if p.situacao != "Pausada" and p.descricao) / 12.0
    linha, cofre, acum_reserva, acum_vencido, max_nec = [], dados.cfg.provisao_guardado_inicial, 0.0, 0.0, 0.0
    primeiro_vermelho = None
    for i, p in enumerate(proj, start=1):
        do_mes = [e for e in dados.extras if e.mes == p.mes and e.situacao != "Descartada" and e.valor]
        total = sum(e.valor for e in do_mes)
        partes = {k: sum(partes_extra(dados, e.valor)[k] for e in do_mes) for k in ("reserva", "dividas", "investir", "livre")}
        vence = vencimento_no_mes(dados, p.mes)
        cofre += prov - vence
        acum_vencido += vence
        acum_reserva += partes["reserva"]
        nec = max(0.0, (acum_vencido - dados.cfg.provisao_guardado_inicial) / i)
        max_nec = max(max_nec, nec)
        if cofre < -0.005 and primeiro_vermelho is None:
            primeiro_vermelho = p.mes
        linha.append(MesExtras(p.mes, total, partes["reserva"], partes["dividas"], partes["investir"], partes["livre"],
                               prov, vence, cofre, PERIGO if cofre < -0.005 else OK, p.reserva_saldo + acum_reserva, nec))

    saldo = saldo_real(dados)
    custo = custo_essencial(dados, proj)
    metas = [("Etapa 1 — Primeiro colchão", dados.cfg.meta_reserva), ("Etapa 2 — 1 mês de contas essenciais", custo.usado),
             ("Etapa 3 — 3 meses de contas essenciais", custo.usado * 3), ("Etapa 4 — 6 meses (reserva completa)", custo.usado * 6)]
    etapas = []
    for nome, meta in metas:
        plano = previsao_etapa(proj, meta, saldo)
        com = "Concluída" if saldo >= meta else next((l.mes for l in linha if l.reserva_com_extras >= meta), "além de 36 meses")
        ant = None
        if isinstance(plano, date) and isinstance(com, date):
            ant = (plano.year - com.year) * 12 + plano.month - com.month
        etapas.append(EtapaComExtras(nome, meta, plano, com, ant))
    return ResultadoExtras(linha, sugerida, prov, primeiro_vermelho, max_nec, etapas)
