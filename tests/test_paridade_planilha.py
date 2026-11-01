"""Paridade com a planilha Excel original (opcional).

Rode com ``PLANILHA_REAL=/caminho/Orcamento_Familiar_05.xlsx pytest tests/test_paridade_planilha.py``.
Compara os 36 meses da projeção calculados pelo motor Python com os valores que o Excel calculou.
"""
import os

import openpyxl
import pytest

from orcamento.importador import importar_planilha
from orcamento.motor import projetar

CAMINHO = os.environ.get("PLANILHA_REAL")
pytestmark = pytest.mark.skipif(not CAMINHO, reason="defina PLANILHA_REAL para comparar com a planilha")

LINHAS = {"receita": 5, "fixas": 7, "parcelas": 8, "variaveis": 9, "faturas": 10, "total": 11, "saldo": 12,
          "teto": 18, "comprometimento": 20, "reserva_saldo": 22}


def test_projecao_igual_a_do_excel():
    dados, _ = importar_planilha(CAMINHO)
    ws = openpyxl.load_workbook(CAMINHO, data_only=True)["Projeção"]
    for i, mes in enumerate(projetar(dados)):
        for campo, linha in LINHAS.items():
            assert getattr(mes, campo) == pytest.approx(ws.cell(linha, 2 + i).value or 0, abs=1e-6), (campo, i)
