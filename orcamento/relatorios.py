"""Folha de anotações em PDF (A4 retrato) para conferência manual no papel."""
from __future__ import annotations

import calendar
import io
from datetime import date
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Flowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .analises import analisar_controle, resumo_futuros, situacao_reserva
from .formatacao import data_br, mes_extenso, moeda
from .modelos import Dados
from .motor import mes_da_projecao, projetar, rotulo_parcela, valor_parcela_no_mes, envelopes_do_mes

AZUL, CLARO, CINZA = colors.HexColor("#1F3864"), colors.HexColor("#D9E1F2"), colors.HexColor("#595959")
LARGURA = A4[0] - 24 * mm

_h = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=9.5, textColor=colors.white, leading=12)
_n = ParagraphStyle("n", fontName="Helvetica", fontSize=7.8, leading=9.5)
_nb = ParagraphStyle("nb", parent=_n, fontName="Helvetica-Bold")
_i = ParagraphStyle("i", fontName="Helvetica-Oblique", fontSize=7, textColor=CINZA, leading=9)


_nd = ParagraphStyle("nd", parent=_n, alignment=TA_RIGHT)


def _p(txt, estilo=_n):
    return Paragraph(str(txt), estilo)


def _d(txt):
    """Parágrafo alinhado à direita (valores em R$)."""
    return Paragraph(str(txt), _nd)


class Caixa(Flowable):
    """Quadradinho vazio para marcar com caneta."""

    def __init__(self, lado: float = 3.2 * mm):
        super().__init__()
        self.lado, self.width, self.height = lado, lado, lado

    def draw(self):
        self.canv.setLineWidth(0.7)
        self.canv.rect(0, 0, self.lado, self.lado)


def _secao(texto: str) -> Table:
    t = Table([[Paragraph(texto, _h)]], colWidths=[LARGURA])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), AZUL), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return t


def _tabela(cab: list[str], linhas: list[list], larguras: list[float], direita: tuple[int, ...] = (), altura: Optional[float] = None,
            total: bool = False) -> Table:
    dados = [[_p(f"<b>{c}</b>") for c in cab]] + [[c if not isinstance(c, str) else _p(c) for c in l] for l in linhas]
    t = Table(dados, colWidths=[w * LARGURA for w in larguras], rowHeights=[None] + [altura] * len(linhas) if altura else None, repeatRows=1)
    est = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#8C8C8C")), ("BACKGROUND", (0, 0), (-1, 0), CLARO),
           ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
           ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]
    for c in direita:
        est.append(("ALIGN", (c, 1), (c, -1), "RIGHT"))
    if total:
        est.append(("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EAF1FB")))
    t.setStyle(TableStyle(est))
    return t


def _vazias(n: int, cols: int) -> list[list]:
    return [[""] * cols for _ in range(n)]


def gerar_folha_anotacoes(dados: Dados, mes: date, hoje: Optional[date] = None) -> bytes:
    """Devolve os bytes de um PDF A4 com 4 páginas: resumo, parcelas/reserva, lançamentos e anotações."""
    hoje = hoje or date.today()
    proj = projetar(dados)
    mp = mes_da_projecao(proj, mes)
    ctl = analisar_controle(dados, proj, mes, hoje)
    reserva = situacao_reserva(dados, proj, mes)
    fut = resumo_futuros(dados, proj, mes)
    el: list = []

    # -------- página 1 -------------------------------------------------------------
    el += [_secao("1. Resumo do mês — confira com seus extratos"),
           _tabela(["Item", "Sistema", "Conferido (à mão)", "Diferença (à mão)", "Observação"],
                   [[_p(a), _d(moeda(b)), "", "", ""] for a, b in [
                       ("Receitas", mp.receita), ("Despesas fixas", mp.fixas), ("Parcelas", mp.parcelas),
                       ("Gastos variáveis lançados", ctl.gasto_variaveis), ("Faturas de cartão", mp.faturas),
                       ("SALDO DO MÊS (receitas − despesas)", mp.saldo), ("Teto dos gastos variáveis", mp.teto),
                       ("Ainda posso gastar (teto − lançados)", mp.teto - ctl.gasto_variaveis)]],
                   [0.34, 0.15, 0.15, 0.15, 0.21], direita=(1,), altura=14.5), Spacer(1, 5)]

    dias = calendar.monthrange(mes.year, mes.month)[1]
    sem = []
    for k in range(1, 6):
        ini, fim = (k - 1) * 7 + 1, min(k * 7, dias)
        if ini > dias:
            continue
        gasto = sum(l.valor or 0 for l in dados.lancamentos if l.mes == mes and l.bloco == "Variável" and l.data and ini <= l.data.day <= fim)
        sem.append([_p(f"Semana {k} — dias {ini} a {fim}"), _d(moeda(mp.teto * (fim - ini + 1) / dias)), _d(moeda(gasto)), "", ""])
    el += [_secao("2. Semana a semana — gastos variáveis"),
           _tabela(["Semana", "Limite", "No sistema", "Anotado (à mão)", "Sobrou / passou (à mão)"], sem, [0.31, 0.16, 0.16, 0.18, 0.19], direita=(1, 2), altura=14.5), Spacer(1, 5)]

    env = envelopes_do_mes(dados, proj, mes)
    el += [_secao("3. Envelopes — limite × gasto"),
           _tabela(["Envelope", "Limite", "No sistema", "Anotado (à mão)", "Saldo (à mão)"],
                   [[_p(e.nome), _d(moeda(e.limite)), _d(moeda(e.gasto)), "", ""] for e in env], [0.34, 0.14, 0.16, 0.18, 0.18], direita=(1, 2), altura=14.5), Spacer(1, 5)]

    fixas = [(f.item, f.valor_no_mes(mes)) for f in dados.fixas if f.valor_no_mes(mes) > 0]
    linhas = [[Caixa(), _p(i), _d(moeda(v)), "", "", ""] for i, v in fixas]
    linhas += [[Caixa(), "", "", "", "", ""] for _ in range(max(0, 8 - len(fixas)))]
    linhas.append([_p(""), _p("<b>Total das fixas do mês</b>"), _d(f"<b>{moeda(mp.fixas)}</b>"), "", "", ""])
    el += [_secao("4. Contas fixas do mês"),
           _tabela(["✓", "Item", "Valor previsto", "Pago em (à mão)", "Valor pago (à mão)", "Observação"], linhas, [0.05, 0.27, 0.15, 0.16, 0.17, 0.20], direita=(2,), altura=14.5, total=True), PageBreak()]

    # -------- página 2 -------------------------------------------------------------
    parc = [(p.item, rotulo_parcela(p, mes), valor_parcela_no_mes(p, mes, dados.cfg.manter_parcelados_sem_total)) for p in dados.parcelados]
    parc = [x for x in parc if x[2] > 0]
    linhas = [[Caixa(), _p(i), _p(r), _d(moeda(v)), "", "", ""] for i, r, v in parc]
    linhas += [[Caixa(), "", "", "", "", "", ""] for _ in range(max(0, 16 - len(parc)))]
    linhas.append([_p(""), _p("<b>Total das parcelas do mês</b>"), "", _d(f"<b>{moeda(mp.parcelas)}</b>"), "", "", ""])
    el += [_secao("5. Parcelas do mês"),
           _tabela(["✓", "Item", "Parcela", "Valor", "Pago em (à mão)", "Valor pago (à mão)", "Observação"], linhas,
                   [0.05, 0.27, 0.10, 0.14, 0.15, 0.15, 0.14], direita=(3,), altura=14.5, total=True), Spacer(1, 6)]
    el += [_secao("6. Reserva de emergência"),
           _tabela(["Item", "Sistema", "Anotado (à mão)", "Observação"],
                   [[_p("Saldo real da reserva"), _d(moeda(reserva.saldo_real)), "", ""], [_p("Próxima meta"), _d(moeda(reserva.proxima_meta)), "", ""],
                    [_p("Depósito planejado para o mês"), _d(moeda(mp.aporte_total)), "", ""], [_p("Depositei neste mês (valor e data)"), "", "", ""]],
                   [0.38, 0.17, 0.2, 0.25], direita=(1,), altura=14.5), Spacer(1, 6)]
    possiveis = [g for g in dados.gastos_futuros if g.mes == mes and g.situacao not in ("Descartada", "Já lançado")]
    linhas = [[Caixa(), _p(g.descricao), _d(moeda(g.valor)), _p(g.chance if g.situacao == "Possível" else g.situacao), ""] for g in possiveis[:6]]
    linhas += [[Caixa(), "", "", "", ""] for _ in range(max(0, 6 - len(possiveis)))]
    el += [_secao("7. Gastos possíveis neste mês (Gastos futuros)"),
           _tabela(["✓", "O que pode acontecer", "Valor", "Chance", "Observação (à mão)"], linhas, [0.05, 0.36, 0.15, 0.14, 0.30], direita=(2,), altura=14.5),
           Spacer(1, 3), _p(f"Se tudo acontecer (todos os meses): {moeda(fut.pior_caso)} | valor esperado: {moeda(fut.esperado)} | {fut.reserva_cobre}", _i), PageBreak()]

    # -------- página 3 -------------------------------------------------------------
    lanc = [l for l in dados.lancamentos if l.mes == mes]
    linhas = [[Caixa(), _p(l.descricao), _p(data_br(l.data)[:5]), _p(l.categoria), _p(l.bloco), _d(moeda(l.valor)), _p(l.envelope), ""] for l in lanc[:34]]
    linhas += [[Caixa(), "", "", "", "", "", "", ""] for _ in range(max(0, 34 - len(lanc)))]
    nota = f" (só 34 listados de {len(lanc)}; veja o sistema)" if len(lanc) > 34 else ""
    linhas.append([_p(""), _p(f"<b>Total do mês — {len(lanc)} lançamento(s){nota}</b>"), "", "", "", _d(f"<b>{moeda(sum(l.valor or 0 for l in lanc))}</b>"), "", ""])
    el += [_secao("8. Lançamentos do mês — na ordem em que foram anotados"),
           _tabela(["✓", "Descrição", "Data", "Categoria", "Bloco", "Valor", "Envelope", "Obs."], linhas,
                   [0.04, 0.22, 0.07, 0.14, 0.09, 0.13, 0.19, 0.12], direita=(5,), altura=14.5, total=True), PageBreak()]

    # -------- página 4 -------------------------------------------------------------
    el += [_secao("9. Novos gastos — anote à mão e depois lance no sistema"),
           _tabela(["✓", "O que foi", "Data", "Categoria", "Bloco", "Valor", "Envelope", "Obs."],
                   [[Caixa()] + [""] * 7 for _ in range(16)], [0.04, 0.22, 0.08, 0.14, 0.09, 0.12, 0.19, 0.12], altura=19), Spacer(1, 8),
           _secao("10. Conferência final do mês"),
           _tabela(["Item", "Valor"],
                   [[_p("Total recebido no mês (à mão)"), ""], [_p("Total pago no mês: fixas, parcelas, gastos e faturas (à mão)"), ""],
                    [_p("Sobra real: recebido − pago (à mão)"), ""], [_p("<b>Sobra segundo o sistema</b>"), _d(f"<b>{moeda(mp.saldo)}</b>")],
                    [_p("Diferença entre a sobra real e a do sistema (à mão)"), ""], [_p("Conferido por / data"), ""]],
                   [0.6, 0.4], altura=19), Spacer(1, 8),
           _secao("Observações"), _tabela(["Anotações"], [[""] for _ in range(5)], [1.0], altura=19)]

    def rodape(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica-Bold", 10)
        canvas.setFillColor(AZUL)
        canvas.drawString(12 * mm, A4[1] - 9 * mm, "FOLHA DE ANOTAÇÕES — conferência manual do mês")
        canvas.setFont("Helvetica", 8.5)
        canvas.setFillColor(colors.black)
        canvas.drawString(12 * mm, A4[1] - 13.5 * mm, f"Mês de referência: {mes_extenso(mes)}")
        canvas.drawRightString(A4[0] - 12 * mm, A4[1] - 13.5 * mm, f"Impresso em: {data_br(hoje)}")
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(CINZA)
        canvas.drawCentredString(A4[0] / 2, 8 * mm, f"Orçamento Familiar Pro — página {doc.page}")
        canvas.restoreState()

    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm, topMargin=19 * mm, bottomMargin=13 * mm,
                      title=f"Folha de anotações — {mes_extenso(mes)}", author="Orçamento Familiar Pro").build(el, onFirstPage=rodape, onLaterPages=rodape)
    return buf.getvalue()
