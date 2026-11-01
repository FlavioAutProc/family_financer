"""Sugestões de corte de despesas."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from ..config import DICA_FATURA, DICA_FIXA, DICA_PADRAO, DICAS_CATEGORIA
from ..formatacao import moeda
from ..modelos import Dados, somar_meses
from ..motor import MesProj, mes_da_projecao


@dataclass
class ItemCorte:
    descricao: str
    categoria: str
    valor: float
    pct_corte: float
    economia: float
    dica: str


@dataclass
class ParcelaEncerrando:
    item: str
    ultima: date
    valor: float
    libera_a_partir_de: date


@dataclass
class Cortes:
    saldo: float
    deveria_sobrar: float
    falta_cortar: float
    economia_sugerida: float
    situacao: str
    nao_essenciais: list[ItemCorte] = field(default_factory=list)
    fixas: list[ItemCorte] = field(default_factory=list)
    parcelas_encerrando: list[ParcelaEncerrando] = field(default_factory=list)


def analisar_cortes(dados: Dados, proj: list[MesProj], mes: date, dicas: Optional[dict[str, str]] = None) -> Cortes:
    dicas = {**DICAS_CATEGORIA, **(dicas or {})}
    cfg, mp = dados.cfg, mes_da_projecao(proj, mes)
    falta = max(0.0, mp.aporte_total - mp.saldo)

    cand = sorted((l for l in dados.lancamentos if l.mes == mes and l.bloco == "Variável" and l.classificacao == "Não Essencial"),
                  key=lambda l: -(l.valor or 0))[:10]
    nao_ess = []
    for l in cand:
        fatura = "cart" in (l.descricao or "").lower()
        pct = 0.0 if fatura else cfg.corte_nao_essencial
        nao_ess.append(ItemCorte(l.descricao, l.categoria, l.valor or 0, pct, (l.valor or 0) * pct,
                                 DICA_FATURA if fatura else dicas.get(l.categoria, DICA_PADRAO)))

    fixas_mes = [(f, f.valor_no_mes(mes)) for f in dados.fixas]
    fixas_mes = sorted([(f, v) for f, v in fixas_mes if v > 0], key=lambda x: -x[1])[:6]
    fixas = [ItemCorte(f.item, f.classificacao, v, cfg.corte_fixas, v * cfg.corte_fixas, f.obs or DICA_FIXA) for f, v in fixas_mes]

    enc = sorted((p for p in dados.parcelados if p.item and p.ultima_parcela and p.ultima_parcela >= mes), key=lambda p: p.ultima_parcela)[:6]
    parcelas = [ParcelaEncerrando(p.item, p.ultima_parcela, p.valor or 0, somar_meses(p.ultima_parcela, 1)) for p in enc]

    economia = sum(i.economia for i in nao_ess) + sum(i.economia for i in fixas)
    if falta == 0:
        sit = "Nada a cortar: o mês já fecha e ainda sobra para a reserva."
    elif economia >= falta:
        sit = "As sugestões cobrem o que falta. Escolha quais aplicar."
    else:
        sit = f"As sugestões cobrem só parte: ainda faltam {moeda(falta - economia)}. Veja também renda extra ou renegociar parcelas."
    return Cortes(mp.saldo, mp.aporte_total, falta, economia, sit, nao_ess, fixas, parcelas)
