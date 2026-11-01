"""Motor de projeção financeira.

Funções puras: recebem ``Dados`` e devolvem resultados, sem tocar em banco nem interface.
Reproduz fielmente a lógica da planilha original (aba *Projeção*):

    receitas   = renda base + ajuste do mês
    teto       = receitas − fixas − parcelas − faturas − aporte da reserva − aporte extra − provisões
    saldo      = receitas − (fixas + parcelas + variáveis [+ faturas])

O "teto de variáveis" é o quanto a família pode gastar em compras do dia a dia sem
comprometer o depósito na reserva nem as provisões anuais.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Optional

from .config import ATENCAO, DEFINIR_ENVELOPE, ESTOUROU, HORIZONTE_MESES, OK, SEM_ENVELOPE
from .modelos import (Dados, Parcelado, diferenca_meses, primeiro_dia, somar_meses)


# ---------------------------------------------------------------------------
# Linha do tempo
# ---------------------------------------------------------------------------

def linha_do_tempo(primeiro: date, n: int = HORIZONTE_MESES) -> list[date]:
    primeiro = primeiro_dia(primeiro)
    return [somar_meses(primeiro, i) for i in range(n)]


def mes_corrente(hoje: Optional[date] = None) -> date:
    return primeiro_dia(hoje or date.today())


# ---------------------------------------------------------------------------
# Parcelados
# ---------------------------------------------------------------------------

def valor_parcela_no_mes(p: Parcelado, mes: date, manter_sem_total: bool = True) -> float:
    """Valor que o parcelado pesa em ``mes`` (0 se não está ativo)."""
    if not p.item or not p.valor:
        return 0.0
    ini = p.primeira_parcela
    if ini is None:
        return 0.0
    if not p.total:  # total desconhecido
        ativo = mes >= ini and (manter_sem_total or mes == primeiro_dia(p.mes_ref))
    else:
        ativo = ini <= mes <= somar_meses(ini, int(p.total) - 1)
    return float(p.valor) if ativo else 0.0


def rotulo_parcela(p: Parcelado, mes: date) -> str:
    """'4/8' quando o parcelado está ativo no mês; '' caso contrário."""
    ini = p.primeira_parcela
    if not p.item or ini is None:
        return ""
    if mes >= ini and (not p.total or mes <= somar_meses(ini, int(p.total) - 1)):
        return f"{diferenca_meses(ini, mes) + 1}/{int(p.total) if p.total else '?'}"
    return ""


def parcelas_restantes(p: Parcelado, mes: date) -> Optional[int]:
    """Parcelas que ainda faltam pagar a partir de ``mes`` (inclusive). None = total desconhecido."""
    ini, fim = p.primeira_parcela, p.ultima_parcela
    if ini is None or fim is None:
        return None
    primeira = max(mes, ini)
    return 0 if fim < primeira else diferenca_meses(primeira, fim) + 1


# ---------------------------------------------------------------------------
# Índice de lançamentos
# ---------------------------------------------------------------------------

class IndiceLancamentos:
    """Soma e contagem de lançamentos por (mês, bloco) — evita varrer a lista várias vezes."""

    def __init__(self, dados: Dados):
        self._soma: dict[tuple[date, str], float] = defaultdict(float)
        self._qtd: dict[tuple[date, str], int] = defaultdict(int)
        for l in dados.lancamentos:
            if l.mes is None:
                continue
            self._soma[(l.mes, l.bloco)] += l.valor or 0.0
            self._qtd[(l.mes, l.bloco)] += 1

    def soma(self, mes: date, bloco: str) -> float:
        return self._soma.get((mes, bloco), 0.0)

    def qtd(self, mes: date, bloco: str) -> int:
        return self._qtd.get((mes, bloco), 0)


# ---------------------------------------------------------------------------
# Projeção
# ---------------------------------------------------------------------------

@dataclass
class MesProj:
    mes: date
    fonte: str                 # "Lançado" ou "Projetado"
    receita: float
    fixas: float
    parcelas: float
    variaveis: float
    faturas: float
    total: float
    saldo: float
    aporte_base: float
    aporte_extra: float
    provisao: float
    teto: float
    teto_pct: float
    comprometimento: float
    status_comprometimento: str
    reserva_saldo: float
    meta_reserva: float
    meta_atingida: bool
    reserva_em_meses_de_fixas: float

    @property
    def aporte_total(self) -> float:
        """Quanto deveria sobrar no mês: reserva + provisões."""
        return self.aporte_base + self.aporte_extra + self.provisao


def provisao_mensal(dados: Dados) -> float:
    """Quanto se guarda por mês para as provisões anuais (manual, ou total ÷ 12)."""
    if dados.cfg.provisao_por_mes_manual is not None:
        return float(dados.cfg.provisao_por_mes_manual)
    ativas = sum(p.valor or 0.0 for p in dados.provisoes if p.situacao != "Pausada" and p.descricao)
    return ativas / 12.0


def projetar(dados: Dados, n: int = HORIZONTE_MESES) -> list[MesProj]:
    cfg = dados.cfg
    meses = linha_do_tempo(cfg.primeiro_mes, n)
    idx = IndiceLancamentos(dados)
    primeiro = meses[0]

    ajustes: dict[date, float] = defaultdict(float)
    for a in dados.ajustes_receita:
        if a.mes:
            ajustes[primeiro_dia(a.mes)] += a.valor or 0.0

    fixas = [sum(f.valor_no_mes(m) for f in dados.fixas) for m in meses]
    parcelas = [sum(valor_parcela_no_mes(p, m, cfg.manter_parcelados_sem_total) for p in dados.parcelados) for m in meses]

    var_proj = cfg.variaveis_projetados if cfg.variaveis_projetados is not None else idx.soma(primeiro, "Variável")
    fat_proj = cfg.faturas_projetadas if cfg.faturas_projetadas is not None else idx.soma(primeiro, "Fatura")

    receitas = [dados.renda_base + ajustes.get(m, 0.0) for m in meses]
    variaveis, faturas, fontes = [], [], []
    for m in meses:
        lancado = idx.qtd(m, "Variável") > 0
        fontes.append("Lançado" if lancado else "Projetado")
        variaveis.append(idx.soma(m, "Variável") if lancado else var_proj)
        faturas.append(idx.soma(m, "Fatura") if idx.qtd(m, "Fatura") > 0 else fat_proj)

    # Parcelas de referência: o mês anterior ao início do redirecionamento
    if cfg.parcelas_referencia is not None:
        parc_ref = cfg.parcelas_referencia
    elif cfg.inicio_redirecionamento:
        anterior = somar_meses(primeiro_dia(cfg.inicio_redirecionamento), -1)
        parc_ref = parcelas[meses.index(anterior)] if anterior in meses else 0.0
    else:
        parc_ref = 0.0

    if cfg.teto_comprometimento is not None:
        teto_comp = cfg.teto_comprometimento
    else:
        teto_comp = (parcelas[0] + faturas[0]) / receitas[0] if receitas[0] else 0.0

    prov = provisao_mensal(dados)
    saida: list[MesProj] = []
    reserva = cfg.saldo_inicial_reserva
    for i, m in enumerate(meses):
        extra = 0.0
        if cfg.redirecionar_parcelas and cfg.inicio_redirecionamento and m >= primeiro_dia(cfg.inicio_redirecionamento):
            extra = max(0.0, parc_ref - parcelas[i])
        total = fixas[i] + parcelas[i] + variaveis[i] + (faturas[i] if cfg.incluir_faturas else 0.0)
        teto = receitas[i] - fixas[i] - parcelas[i] - faturas[i] - cfg.reserva_aporte - extra - prov
        comp = (parcelas[i] + faturas[i]) / receitas[i] if receitas[i] else 0.0
        reserva += cfg.reserva_aporte + extra
        saida.append(MesProj(
            mes=m, fonte=fontes[i], receita=receitas[i], fixas=fixas[i], parcelas=parcelas[i],
            variaveis=variaveis[i], faturas=faturas[i], total=total, saldo=receitas[i] - total,
            aporte_base=cfg.reserva_aporte, aporte_extra=extra, provisao=prov, teto=teto,
            teto_pct=teto / receitas[i] if receitas[i] else 0.0, comprometimento=comp,
            status_comprometimento=OK if comp <= teto_comp + 1e-5 else "ACIMA",
            reserva_saldo=reserva, meta_reserva=cfg.meta_reserva, meta_atingida=reserva >= cfg.meta_reserva,
            reserva_em_meses_de_fixas=reserva / fixas[i] if fixas[i] else 0.0,
        ))
    return saida


def mes_da_projecao(proj: list[MesProj], mes: date) -> MesProj:
    """Linha da projeção do mês (se o mês sair da linha do tempo, devolve a mais próxima)."""
    for p in proj:
        if p.mes == mes:
            return p
    return proj[0] if mes < proj[0].mes else proj[-1]


# ---------------------------------------------------------------------------
# Envelopes
# ---------------------------------------------------------------------------

@dataclass
class LinhaEnvelope:
    nome: str
    pct: Optional[float]
    limite: float
    gasto: float
    parcelado_vinculado: float
    saldo: float
    pct_usado: Optional[float]
    status: str


def envelopes_do_mes(dados: Dados, proj: list[MesProj], mes: date) -> list[LinhaEnvelope]:
    """Limite × gasto de cada envelope no mês, mais a linha '(sem envelope)'."""
    teto = mes_da_projecao(proj, mes).teto
    gastos: dict[str, float] = defaultdict(float)
    total_var = 0.0
    for l in dados.lancamentos:
        if l.mes == mes and l.bloco == "Variável":
            gastos[l.envelope] += l.valor or 0.0
            total_var += l.valor or 0.0
    linhas, soma_gastos = [], 0.0
    for e in sorted(dados.envelopes, key=lambda x: (x.ordem, x.id or 0)):
        limite = (e.pct or 0.0) * teto
        gasto = gastos.get(e.nome, 0.0)
        soma_gastos += gasto
        vinc = sum(valor_parcela_no_mes(p, mes, dados.cfg.manter_parcelados_sem_total) for p in dados.parcelados if p.envelope == e.nome)
        uso = gasto / limite if limite else 0.0
        status = ESTOUROU if uso > 1 else (ATENCAO if uso >= 0.8 else OK)
        linhas.append(LinhaEnvelope(e.nome, e.pct, limite, gasto, vinc, limite - gasto, uso, status))
    sem = total_var - soma_gastos
    linhas.append(LinhaEnvelope(SEM_ENVELOPE, None, 0.0, sem, 0.0, -sem, None, DEFINIR_ENVELOPE if sem > 0.004 else "—"))
    return linhas
