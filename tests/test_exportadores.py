import io
import re
from datetime import date

import openpyxl

from orcamento.exportador import exportar_excel
from orcamento.relatorios import gerar_folha_anotacoes

M0 = date(2026, 11, 1)


def test_folha_de_anotacoes_pdf_tem_4_paginas_a4(demo):
    pdf = gerar_folha_anotacoes(demo, M0, hoje=date(2026, 10, 30))
    assert pdf.startswith(b"%PDF")
    assert len(re.findall(rb"/Type\s*/Page\b", pdf)) == 4
    assert b"595.27" in pdf or b"595.28" in pdf or b"841.89" in pdf          # MediaBox A4


def test_folha_funciona_com_banco_vazio():
    from orcamento.modelos import Dados
    d = Dados(); d.rendas = []
    assert gerar_folha_anotacoes(d, M0).startswith(b"%PDF")


def test_excel_exportado_tem_as_abas_e_36_meses(demo):
    wb = openpyxl.load_workbook(io.BytesIO(exportar_excel(demo)))
    assert {"Projeção", "Lançamentos", "Fixas", "Parcelados", "Gastos futuros", "Extras e provisões", "Reserva", "Investimentos"} <= set(wb.sheetnames)
    ws = wb["Projeção"]
    assert ws.max_row == 3 + 36 and ws["A4"].value.date() == M0
    assert wb["Lançamentos"].max_row == 3 + len(demo.lancamentos)
