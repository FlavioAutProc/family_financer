"""Importação da planilha Excel (``Orcamento_Familiar_05.xlsx`` e versões anteriores).

Lê só as células de **entrada** (constantes digitadas pelo usuário). Células de fórmula
são ignoradas — o sistema recalcula tudo. Abas ausentes (planilhas mais antigas) são
simplesmente puladas e aparecem no relatório de importação.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, BinaryIO, Optional, Union

import openpyxl

from .config import SEM_ENVELOPE
from .modelos import (AjusteReceita, Dados, Envelope, Extra, Fixa, GastoFuturo, Investimento, Lancamento,
                      MovReserva, OutraDivida, Parcelado, Provisao, Renda, primeiro_dia, somar_meses)


@dataclass
class RelatorioImportacao:
    contagens: dict[str, int] = field(default_factory=dict)
    avisos: list[str] = field(default_factory=list)

    def somar(self, nome: str, n: int) -> None:
        self.contagens[nome] = self.contagens.get(nome, 0) + n


# -- conversores tolerantes ---------------------------------------------------

def _formula(v: Any) -> bool:
    return isinstance(v, str) and v.startswith("=")


def _num(v: Any) -> Optional[float]:
    if v is None or _formula(v) or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace("R$", "").replace(".", "").replace(",", ".").strip())
    except ValueError:
        return None


def _int(v: Any) -> Optional[int]:
    n = _num(v)
    return None if n is None else int(n)


def _txt(v: Any) -> str:
    if v is None or _formula(v):
        return ""
    return str(v).strip()


def _data(v: Any) -> Optional[date]:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return None


def _mes(v: Any) -> Optional[date]:
    d = _data(v)
    return primeiro_dia(d) if d else None


def _sim(v: Any, padrao: bool) -> bool:
    t = _txt(v).lower()
    return padrao if not t else t.startswith("s")


def _linhas(ws, a: int, b: int, ate_col: int):
    for r in range(a, b + 1):
        yield r, [ws.cell(r, c).value for c in range(1, ate_col + 1)]


# -- importação -----------------------------------------------------------------

def importar_planilha(origem: Union[str, Path, BinaryIO]) -> tuple[Dados, RelatorioImportacao]:
    wb = openpyxl.load_workbook(origem, data_only=False)
    rel = RelatorioImportacao()
    d = Dados()
    cfg = d.cfg

    def aba(nome: str):
        if nome in wb.sheetnames:
            return wb[nome]
        rel.avisos.append(f"Aba '{nome}' não encontrada — pulada.")
        return None

    # Premissas ---------------------------------------------------------------
    ws = aba("Premissas")
    if ws:
        for r in (5, 6, 7):
            nome, valor = _txt(ws.cell(r, 1).value), _num(ws.cell(r, 2).value)
            if nome:
                d.rendas.append(Renda(nome, valor or 0.0))
        cfg.primeiro_mes = _mes(ws["B11"].value) or cfg.primeiro_mes
        cfg.reserva_aporte = _num(ws["B12"].value) or 0.0
        cfg.redirecionar_parcelas = _sim(ws["B13"].value, True)
        cfg.inicio_redirecionamento = _mes(ws["B14"].value)
        cfg.meta_reserva = _num(ws["B15"].value) or cfg.meta_reserva
        cfg.saldo_inicial_reserva = _num(ws["B16"].value) or 0.0
        cfg.variaveis_projetados = _num(ws["B17"].value)      # fórmula -> None (automático)
        cfg.faturas_projetadas = _num(ws["B18"].value)
        cfg.incluir_faturas = _sim(ws["B19"].value, True)
        cfg.manter_parcelados_sem_total = _sim(ws["B20"].value, True)
        cfg.parcelas_referencia = _num(ws["B21"].value)
        cfg.teto_comprometimento = _num(ws["B22"].value)
        rel.somar("rendas", len(d.rendas))

    # Fixas ---------------------------------------------------------------------
    ws = aba("Fixas")
    if ws:
        for _, v in _linhas(ws, 5, 24, 7):
            if _txt(v[0]):
                d.fixas.append(Fixa(_txt(v[0]), _txt(v[1]) or "Fixa", _txt(v[2]) or "Essencial", _num(v[3]) or 0.0,
                                    _mes(v[4]), _mes(v[5]), _txt(v[6])))
        rel.somar("fixas", len(d.fixas))

    # Parcelados (+ taxas da aba Dívidas, alinhadas linha a linha) ------------------
    ws = aba("Parcelados")
    taxas: dict[int, float] = {}
    wd = wb["Dívidas"] if "Dívidas" in wb.sheetnames else None
    if wd:
        for r in range(33, 72):
            t = _num(wd.cell(r, 6).value)
            if t is not None:
                taxas[r - 28] = t
    if ws:
        for r, v in _linhas(ws, 5, 43, 11):
            if _txt(v[0]):
                d.parcelados.append(Parcelado(_txt(v[0]), _txt(v[1]), _txt(v[2]), _num(v[3]) or 0.0, _int(v[4]), _mes(v[5]),
                                              _int(v[6]), taxas.get(r), _txt(v[10])))
        rel.somar("parcelados", len(d.parcelados))

    # Lançamentos ---------------------------------------------------------------------
    ws = aba("Lançamentos")
    if ws:
        for _, v in _linhas(ws, 5, 1000, 9):
            if v[0] is None and _num(v[7]) is None:
                continue
            env = _txt(v[6])
            d.lancamentos.append(Lancamento(_data(v[0]), _txt(v[2]), _txt(v[3]), _txt(v[4]) or "Essencial",
                                            _txt(v[5]) or "Variável", "" if env == SEM_ENVELOPE else env, _num(v[7]) or 0.0, _txt(v[8])))
        rel.somar("lançamentos", len(d.lancamentos))

    # Envelopes ------------------------------------------------------------------------
    ws = aba("Envelopes")
    if ws:
        for i, r in enumerate(range(7, 12)):
            nome = _txt(ws.cell(r, 1).value)
            if nome:
                d.envelopes.append(Envelope(nome, _num(ws.cell(r, 2).value) or 0.0, i))
        rel.somar("envelopes", len(d.envelopes))

    # Ajustes de receita (Projeção, linha 6) -----------------------------------------------
    ws = aba("Projeção")
    if ws:
        for i in range(36):
            v = _num(ws.cell(6, 2 + i).value)
            if v:
                d.ajustes_receita.append(AjusteReceita(somar_meses(cfg.primeiro_mes, i), v))
        rel.somar("ajustes de receita", len(d.ajustes_receita))

    # Abas novas (v05) -------------------------------------------------------------------
    if "Gastos futuro" in wb.sheetnames:
        ws = wb["Gastos futuro"]
        for _, v in _linhas(ws, 14, 43, 9):
            if _txt(v[0]):
                d.gastos_futuros.append(GastoFuturo(_txt(v[0]), _txt(v[1]), _mes(v[2]), _num(v[3]) or 0.0,
                                                    _txt(v[4]) or "Média", _txt(v[5]) or "Possível", _txt(v[8])))
        for ref, campo in (("B46", "chance_baixa"), ("B47", "chance_media"), ("B48", "chance_alta")):
            n = _num(ws[ref].value)
            if n is not None:
                setattr(cfg, campo, n)
        rel.somar("gastos futuros", len(d.gastos_futuros))

    if wd:
        for _, v in _linhas(wd, 23, 28, 4):
            if _txt(v[0]) or _num(v[1]):
                d.outras_dividas.append(OutraDivida(_txt(v[0]), _num(v[1]) or 0.0, _num(v[2]), _num(v[3])))
        rel.somar("outras dívidas", len(d.outras_dividas))
        rel.somar("taxas de parcelados", len(taxas))

    if "Extras e provisões" in wb.sheetnames:
        ws = wb["Extras e provisões"]
        for ref, campo in (("B6", "destino_reserva"), ("B7", "destino_dividas"), ("B8", "destino_investir"), ("B9", "destino_livre")):
            n = _num(ws[ref].value)
            if n is not None:
                setattr(cfg, campo, n)
        for _, v in _linhas(ws, 14, 25, 10):
            if _txt(v[0]):
                d.extras.append(Extra(_txt(v[0]), _txt(v[1]) or "Renda extra", _mes(v[2]), _num(v[3]) or 0.0, _txt(v[4]) or "Prevista", _txt(v[9])))
        for _, v in _linhas(ws, 30, 41, 6):
            if _txt(v[0]):
                d.provisoes.append(Provisao(_txt(v[0]), _mes(v[1]), _num(v[2]) or 0.0, _txt(v[4]) or "Ativa", _txt(v[5])))
        cfg.provisao_guardado_inicial = _num(ws["B43"].value) or 0.0
        cfg.provisao_por_mes_manual = _num(ws["B45"].value)
        rel.somar("extras", len(d.extras))
        rel.somar("provisões", len(d.provisoes))

    if "RESERVA" in wb.sheetnames:
        ws = wb["RESERVA"]
        for _, v in _linhas(ws, 32, 91, 4):
            if _num(v[2]) is not None and _txt(v[1]):
                d.mov_reserva.append(MovReserva(_data(v[0]), _txt(v[1]), _num(v[2]) or 0.0, _txt(v[3])))
        cfg.incluir_parcelas_custo_essencial = _sim(ws["B16"].value, True)
        cfg.custo_essencial_manual = _num(ws["B18"].value)
        rel.somar("movimentos da reserva", len(d.mov_reserva))

    if "INVESTIMENTOS" in wb.sheetnames:
        ws = wb["INVESTIMENTOS"]
        for _, v in _linhas(ws, 13, 32, 7):
            if _txt(v[0]):
                d.investimentos.append(Investimento(_txt(v[0]), _txt(v[1]), _txt(v[2]), _txt(v[3]), _txt(v[4]), _num(v[5]) or 0.0, _num(v[6]) or 0.0))
        cfg.reserva_minima_investir = _num(ws["B6"].value)
        cfg.aporte_simulador = _num(ws["B49"].value)
        cfg.rendimento_anual = _num(ws["B50"].value) if _num(ws["B50"].value) is not None else cfg.rendimento_anual
        rel.somar("investimentos", len(d.investimentos))

    if "CORTES" in wb.sheetnames:
        ws = wb["CORTES"]
        cfg.corte_nao_essencial = _num(ws["B13"].value) if _num(ws["B13"].value) is not None else cfg.corte_nao_essencial
        cfg.corte_fixas = _num(ws["B14"].value) if _num(ws["B14"].value) is not None else cfg.corte_fixas
    if "Histórico" in wb.sheetnames:
        n = _num(wb["Histórico"]["B10"].value)
        cfg.meta_poupanca = n if n is not None else cfg.meta_poupanca

    if not d.rendas:
        rel.avisos.append("Nenhuma renda encontrada em Premissas.")
    return d, rel
