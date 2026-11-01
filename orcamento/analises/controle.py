"""Painel de controle do mês: semáforo de verificações, maiores gastos e envelopes."""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from typing import Optional

from ..config import ATENCAO, OK, PERIGO, ESTOUROU, DEFINIR_ENVELOPE
from ..formatacao import moeda, pct
from ..modelos import Dados
from ..motor import LinhaEnvelope, MesProj, envelopes_do_mes, mes_corrente, mes_da_projecao
from .reserva import situacao_reserva


@dataclass
class Verificacao:
    nome: str
    resultado: Optional[float]
    limite: Optional[float]
    situacao: str
    orientacao: str
    formato: str = "moeda"       # moeda | pct | inteiro


@dataclass
class GastoGrande:
    posicao: int
    descricao: str
    categoria: str
    valor: float
    pct_variaveis: float
    classificacao: str
    envelope: str


@dataclass
class Controle:
    mes: date
    mp: MesProj
    gasto_variaveis: float
    verificacoes: list[Verificacao]
    maiores: list[GastoGrande]
    envelopes: list[LinhaEnvelope]

    @property
    def ok_count(self) -> int:
        return sum(1 for v in self.verificacoes if v.situacao == OK)

    @property
    def resumo(self) -> str:
        n = len(self.verificacoes)
        if self.ok_count == n:
            return "Mês sob controle."
        if self.ok_count >= 5:
            return "Quase lá: resolva os itens amarelos e vermelhos."
        return "Atenção: vários pontos fora do controle. Comece pela aba Cortes."


def _dias(mes: date, hoje: date) -> tuple[int, int]:
    """(dias do mês, dias já decorridos) — 0 decorridos para meses futuros."""
    dias_mes = calendar.monthrange(mes.year, mes.month)[1]
    atual = mes_corrente(hoje)
    if mes > atual:
        return dias_mes, 0
    if mes < atual:
        return dias_mes, dias_mes
    return dias_mes, hoje.day


def analisar_controle(dados: Dados, proj: list[MesProj], mes: date, hoje: Optional[date] = None) -> Controle:
    hoje = hoje or date.today()
    mp = mes_da_projecao(proj, mes)
    gasto = sum(l.valor or 0 for l in dados.lancamentos if l.mes == mes and l.bloco == "Variável")
    env = envelopes_do_mes(dados, proj, mes)
    res = situacao_reserva(dados, proj, mes)
    v: list[Verificacao] = []

    # 1) Saldo do mês × quanto deveria sobrar (reserva + provisões)
    meta_saldo = mp.aporte_total
    sit = PERIGO if mp.saldo < 0 else (ATENCAO if mp.saldo < meta_saldo else OK)
    txt = {PERIGO: "Gasta mais do que ganha: corte o que não é essencial (aba Cortes).",
           ATENCAO: "Fecha no azul, mas não sobra para a reserva e as provisões: reduza gastos não essenciais.",
           OK: "Sobra o suficiente para a reserva: faça o depósito na aba Reserva."}[sit]
    v.append(Verificacao("Saldo do mês (receita − despesas)", mp.saldo, meta_saldo, sit, txt))

    # 2) Variáveis × teto
    if mp.teto <= 0:
        sit = PERIGO if gasto > 0 else OK
    else:
        uso = gasto / mp.teto
        sit = PERIGO if uso > 1 else (ATENCAO if uso >= 0.8 else OK)
    txt = (f"Ainda pode gastar {moeda(mp.teto - gasto)} até o fim do mês." if mp.teto - gasto >= 0
           else f"Passou do limite em {moeda(gasto - mp.teto)}: pare os gastos não essenciais.")
    v.append(Verificacao("Gastos variáveis do mês × limite (teto)", gasto, mp.teto, sit, txt))

    # 3) Ritmo
    dias_mes, passados = _dias(mes, hoje)
    if passados == 0:
        v.append(Verificacao("Ritmo: onde o mês vai fechar se continuar assim", None, mp.teto, "—",
                             "Só funciona no mês corrente ou em meses passados."))
    else:
        proj_fim = gasto / passados * dias_mes
        sit = PERIGO if proj_fim > mp.teto else (ATENCAO if proj_fim >= 0.9 * mp.teto else OK)
        v.append(Verificacao("Ritmo: onde o mês vai fechar se continuar assim", proj_fim, mp.teto, sit,
                             f"No ritmo de hoje, os variáveis fecham em {moeda(proj_fim)}."))

    # 4) Comprometimento (parcelas + faturas)
    teto_comp = None
    if dados.cfg.teto_comprometimento is not None:
        teto_comp = dados.cfg.teto_comprometimento
    elif proj[0].receita:
        teto_comp = (proj[0].parcelas + proj[0].faturas) / proj[0].receita
    v.append(Verificacao("Peso das parcelas + faturas na renda", mp.comprometimento, teto_comp,
                         OK if mp.status_comprometimento == OK else PERIGO,
                         f"Regra: este índice só pode cair, nunca subir. Hoje: {pct(mp.comprometimento)} da renda.", "pct"))

    # 5) Envelopes estourados
    estourados = sum(1 for e in env if e.status == ESTOUROU)
    atencao = sum(1 for e in env if e.status == ATENCAO)
    sit = PERIGO if estourados else (ATENCAO if atencao else OK)
    v.append(Verificacao("Envelopes estourados", estourados, 0, sit,
                         f"{estourados} envelope(s) acima do limite: veja a tabela de envelopes." if estourados else "Nenhum envelope estourou.", "inteiro"))

    # 6) Sem envelope
    sem = next((e.gasto for e in env if e.status == DEFINIR_ENVELOPE), 0.0)
    v.append(Verificacao("Gastos sem envelope definido", sem, 0, ATENCAO if sem > 0.004 else OK,
                         "Todo gasto variável precisa de envelope: preencha em Lançamentos." if sem > 0.004 else "Todos os gastos têm envelope."))

    # 7) Reserva
    sit = OK if res.saldo_real >= res.proxima_meta else (ATENCAO if res.saldo_real > 0 else PERIGO)
    v.append(Verificacao("Reserva de emergência × próxima meta", res.saldo_real, res.proxima_meta, sit,
                         f"Faltam {moeda(max(0.0, res.proxima_meta - res.saldo_real))} para a próxima meta (aba Reserva)."))

    # 8) Parcelados incompletos
    incompletos = sum(1 for p in dados.parcelados if p.item and not p.total)
    v.append(Verificacao("Parcelados com total de parcelas em branco", incompletos, 0, ATENCAO if incompletos else OK,
                         "Preencha o total de parcelas em Parcelados; sem isso a conta fica incerta." if incompletos else "Todos os parcelados estão completos.", "inteiro"))

    # Maiores gastos
    var = sorted((l for l in dados.lancamentos if l.mes == mes and l.bloco == "Variável"), key=lambda l: -(l.valor or 0))[:5]
    maiores = [GastoGrande(i + 1, l.descricao, l.categoria, l.valor or 0, (l.valor or 0) / gasto if gasto else 0.0,
                           l.classificacao, l.envelope or "sem envelope") for i, l in enumerate(var)]
    return Controle(mes, mp, gasto, v, maiores, env)
