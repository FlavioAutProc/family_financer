"""Dívidas: custo dos juros, prioridade de quitação e outras dívidas."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from typing import Optional, Union

from ..config import ATENCAO, OK, PERIGO
from ..modelos import Dados, somar_meses
from ..motor import parcelas_restantes, rotulo_parcela


def valor_presente(parcela: float, n: int, taxa: float) -> float:
    """Valor hoje de ``n`` parcelas iguais pagas ao fim de cada mês, com juros ``taxa`` ao mês."""
    if n <= 0:
        return 0.0
    if taxa == 0:
        return parcela * n
    return parcela * (1 - (1 + taxa) ** (-n)) / taxa


@dataclass
class DividaParcelada:
    indice: int                      # posição na lista de parcelados
    item: str
    rotulo: str
    parcela: float
    restantes: Optional[int]
    total_restante: Optional[float]
    taxa: Optional[float]
    saldo_devedor: Optional[float]
    juros_restantes: Optional[float]
    termina_em: Optional[date]
    prioridade: Optional[int] = None


@dataclass
class Prioridade:
    posicao: int
    divida: DividaParcelada
    verba_acumulada: float
    cabe_nos_extras: Optional[bool]


@dataclass
class OutraDividaAnalise:
    descricao: str
    saldo: float
    taxa: Optional[float]
    pagamento: Optional[float]
    juros_mes: Optional[float]
    meses_para_quitar: Union[int, str, None]
    juros_ate_quitar: Optional[float]
    situacao: str


@dataclass
class ResultadoDividas:
    parceladas: list[DividaParcelada]
    prioridade: list[Prioridade]
    outras: list[OutraDividaAnalise]
    total_restante: float
    com_taxa: int
    ativas: int
    juros_restantes: float
    saldo_devedor: float
    juros_mes_outras: float
    verba_extras: float

    @property
    def faltam_taxas(self) -> bool:
        return self.ativas > self.com_taxa


def analisar_outra(o) -> OutraDividaAnalise:
    if o.taxa is None or not o.saldo:
        return OutraDividaAnalise(o.descricao, o.saldo or 0, o.taxa, o.pagamento, None, None, None, "—")
    juros = o.saldo * o.taxa
    meses: Union[int, str, None] = None
    if o.pagamento is not None:
        if o.pagamento <= 0 or (o.taxa > 0 and o.pagamento <= juros):
            meses = "nunca quita"
        elif o.taxa == 0:
            meses = math.ceil(o.saldo / o.pagamento)
        else:
            meses = math.ceil(-math.log(1 - o.saldo * o.taxa / o.pagamento) / math.log(1 + o.taxa))
    total_juros = o.pagamento * meses - o.saldo if isinstance(meses, int) else None
    if meses is None:
        sit = "—"
    elif meses == "nunca quita":
        sit = PERIGO
    else:
        sit = ATENCAO if meses > 24 else OK
    return OutraDividaAnalise(o.descricao, o.saldo, o.taxa, o.pagamento, juros, meses, total_juros, sit)


def analisar_dividas(dados: Dados, mes: date) -> ResultadoDividas:
    manter = dados.cfg.manter_parcelados_sem_total
    lista: list[DividaParcelada] = []
    for i, p in enumerate(dados.parcelados):
        if not p.item:
            continue
        rest = parcelas_restantes(p, mes)
        parc = float(p.valor or 0)
        total = parc * rest if rest is not None else None
        if rest is None:
            saldo = juros = None
        elif rest == 0:
            saldo, juros = 0.0, 0.0
        elif p.taxa_juros is None:
            saldo = juros = None
        else:
            saldo = valor_presente(parc, rest, p.taxa_juros)
            juros = total - saldo
        rot = rotulo_parcela(p, mes) or ("encerrada" if rest == 0 else ("ainda não começou" if rest else "?"))
        lista.append(DividaParcelada(i, p.item, rot, parc, rest, total, p.taxa_juros, saldo, juros, p.ultima_parcela))

    ativas = [d for d in lista if d.restantes and d.restantes > 0]
    com_taxa = [d for d in ativas if d.taxa is not None]
    for pos, d in enumerate(sorted(com_taxa, key=lambda x: (-x.taxa, x.indice)), start=1):
        d.prioridade = pos

    verba = sum(e.valor * dados.cfg.destino_dividas for e in dados.extras
                if e.mes and e.mes >= mes and e.situacao != "Descartada" and e.valor)
    prioridade, acum = [], 0.0
    for d in sorted(com_taxa, key=lambda x: x.prioridade)[:5]:
        acum += d.saldo_devedor or 0.0
        prioridade.append(Prioridade(d.prioridade, d, acum, None if verba <= 0 else acum <= verba))

    outras = [analisar_outra(o) for o in dados.outras_dividas if o.descricao or o.saldo]
    return ResultadoDividas(
        lista, prioridade, outras,
        total_restante=sum(d.total_restante or 0 for d in lista),
        com_taxa=len(com_taxa), ativas=len(ativas),
        juros_restantes=sum(d.juros_restantes or 0 for d in lista),
        saldo_devedor=sum(d.saldo_devedor or 0 for d in lista),
        juros_mes_outras=sum(o.juros_mes or 0 for o in outras), verba_extras=verba)
