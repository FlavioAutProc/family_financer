"""Exportação de dados: Excel (relatório) e JSON (backup completo)."""
from __future__ import annotations

import io
from datetime import date

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from .banco import dados_para_json, json_para_dados
from .modelos import Dados
from .motor import projetar

__all__ = ["exportar_excel", "dados_para_json", "json_para_dados"]

MOEDA = '"R$ "#,##0.00;[Red]-"R$ "#,##0.00'
_BORDA = Border(*(Side(style="thin", color="BFBFBF"),) * 4)


def _escrever(ws, titulo: str, cabecalho: list[str], linhas: list[list], formatos: dict[int, str] | None = None) -> None:
    ws["A1"] = titulo
    ws["A1"].font = Font(name="Arial", size=14, bold=True, color="1F3864")
    for j, nome in enumerate(cabecalho, start=1):
        c = ws.cell(3, j, nome)
        c.font = Font(name="Arial", bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1F3864")
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for i, linha in enumerate(linhas, start=4):
        for j, v in enumerate(linha, start=1):
            c = ws.cell(i, j, v)
            c.font = Font(name="Arial", size=10)
            c.border = _BORDA
            if formatos and j in formatos:
                c.number_format = formatos[j]
    for j, nome in enumerate(cabecalho, start=1):
        maior = max([len(str(nome))] + [len(str(l[j - 1])) for l in linhas if j - 1 < len(l) and l[j - 1] is not None])
        ws.column_dimensions[get_column_letter(j)].width = min(48, max(12, maior + 3))
    ws.freeze_panes = "A4"
    ws.sheet_view.showGridLines = False


def exportar_excel(dados: Dados) -> bytes:
    """Relatório em Excel (somente leitura de dados — para arquivar ou compartilhar)."""
    wb = Workbook()
    wb.remove(wb.active)
    proj = projetar(dados)
    data, mes = "dd/mm/yyyy", "mmm/yy"

    ws = wb.create_sheet("Projeção")
    _escrever(ws, "Projeção de 36 meses",
              ["Mês", "Fonte", "Receitas", "Fixas", "Parcelas", "Variáveis", "Faturas", "Total despesas", "Saldo",
               "Reserva (aporte)", "Reserva (extra)", "Provisões", "Teto de variáveis", "Reserva acumulada"],
              [[p.mes, p.fonte, p.receita, p.fixas, p.parcelas, p.variaveis, p.faturas, p.total, p.saldo,
                p.aporte_base, p.aporte_extra, p.provisao, p.teto, p.reserva_saldo] for p in proj],
              {1: mes, **{k: MOEDA for k in range(3, 15)}})
    ws = wb.create_sheet("Lançamentos")
    _escrever(ws, "Lançamentos", ["Data", "Descrição", "Categoria", "Classificação", "Bloco", "Envelope", "Valor", "Observação"],
              [[l.data, l.descricao, l.categoria, l.classificacao, l.bloco, l.envelope, l.valor, l.obs] for l in dados.lancamentos],
              {1: data, 7: MOEDA})
    ws = wb.create_sheet("Fixas")
    _escrever(ws, "Despesas fixas", ["Item", "Categoria", "Classificação", "Valor mensal", "Início", "Fim", "Observação"],
              [[f.item, f.categoria, f.classificacao, f.valor, f.inicio, f.fim, f.obs] for f in dados.fixas], {4: MOEDA, 5: mes, 6: mes})
    ws = wb.create_sheet("Parcelados")
    _escrever(ws, "Parcelados", ["Item", "Categoria", "Envelope", "Valor da parcela", "Parcela (n)", "Mês desse n", "Total (m)",
                                 "1ª parcela", "Última parcela", "Taxa ao mês", "Observação"],
              [[p.item, p.categoria, p.envelope, p.valor, p.n_atual, p.mes_ref, p.total, p.primeira_parcela, p.ultima_parcela,
                p.taxa_juros, p.obs] for p in dados.parcelados], {4: MOEDA, 6: mes, 8: mes, 9: mes, 10: "0.00%"})
    ws = wb.create_sheet("Gastos futuros")
    _escrever(ws, "Gastos futuros (possíveis)", ["Descrição", "Categoria", "Mês", "Valor", "Chance", "Situação", "Observação"],
              [[g.descricao, g.categoria, g.mes, g.valor, g.chance, g.situacao, g.obs] for g in dados.gastos_futuros], {3: mes, 4: MOEDA})
    ws = wb.create_sheet("Extras e provisões")
    _escrever(ws, "Entradas extras", ["Descrição", "Tipo", "Mês", "Valor", "Situação", "Observação"],
              [[e.descricao, e.tipo, e.mes, e.valor, e.situacao, e.obs] for e in dados.extras], {3: mes, 4: MOEDA})
    r0 = len(dados.extras) + 7
    ws.cell(r0 - 1, 1, "Provisões anuais").font = Font(name="Arial", size=12, bold=True, color="1F3864")
    for j, nome in enumerate(["Descrição", "Mês do vencimento", "Valor", "Situação", "Observação"], start=1):
        ws.cell(r0, j, nome).font = Font(name="Arial", bold=True)
    for i, p in enumerate(dados.provisoes, start=r0 + 1):
        for j, v in enumerate([p.descricao, p.mes, p.valor, p.situacao, p.obs], start=1):
            ws.cell(i, j, v)
        ws.cell(i, 2).number_format, ws.cell(i, 3).number_format = mes, MOEDA
    ws = wb.create_sheet("Reserva")
    _escrever(ws, "Movimentos da reserva", ["Data", "Tipo", "Valor", "Observação"],
              [[m.data, m.tipo, m.valor, m.obs] for m in dados.mov_reserva], {1: data, 3: MOEDA})
    ws = wb.create_sheet("Investimentos")
    _escrever(ws, "Carteira de investimentos", ["Produto", "Tipo", "Instituição", "Objetivo", "Liquidez", "Valor aplicado", "Valor atual"],
              [[i.produto, i.tipo, i.instituicao, i.objetivo, i.liquidez, i.aplicado, i.atual] for i in dados.investimentos], {6: MOEDA, 7: MOEDA})
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
