"""Testes de tela: cada página roda sem exceções e o formulário de lançamento grava no banco."""
import os
from datetime import date

import pytest
from streamlit.testing.v1 import AppTest

from orcamento.banco import Banco
from orcamento.demo import dados_demo
from orcamento.modelos import Dados

M0 = date(2026, 11, 1)
TELAS = ["p_inicio", "p_lancamentos", "p_folha", "p_controle", "p_cortes", "p_futuros", "p_historico", "p_dividas",
         "p_extras", "p_reserva", "p_investimentos", "p_cadastros", "p_config", "p_dados"]


def _rodar(tela: str) -> AppTest:
    codigo = (f"import streamlit as st\nfrom datetime import date\nst.session_state['mes'] = date(2026, 11, 1)\n"
              f"from orcamento.ui import {tela}\n{tela}.render()")
    return AppTest.from_string(codigo, default_timeout=60).run()


@pytest.fixture
def banco_ui():
    b = Banco(os.environ["ORCAMENTO_DB"])
    yield b
    b.substituir_tudo(Dados())


@pytest.mark.parametrize("tela", TELAS)
def test_tela_com_dados_de_exemplo(tela, banco_ui):
    banco_ui.substituir_tudo(dados_demo(M0))
    at = _rodar(tela)
    assert not at.exception, [str(e.value) for e in at.exception]


@pytest.mark.parametrize("tela", TELAS)
def test_tela_com_banco_vazio(tela, banco_ui):
    banco_ui.substituir_tudo(Dados())
    at = _rodar(tela)
    assert not at.exception, [str(e.value) for e in at.exception]


def test_formulario_anota_um_gasto(banco_ui):
    banco_ui.substituir_tudo(dados_demo(M0))
    antes = len(banco_ui.carregar_dados().lancamentos)
    at = _rodar("p_lancamentos")
    next(t for t in at.text_input if t.label == "O que foi?").set_value("Teste de formulário")
    next(n for n in at.number_input if n.label == "Valor (R$)").set_value(12.5)
    next(b for b in at.button if b.label == "Anotar").click()
    at.run()
    lancs = banco_ui.carregar_dados().lancamentos
    assert len(lancs) == antes + 1
    novo = next(l for l in lancs if l.descricao == "Teste de formulário")
    assert novo.valor == 12.5 and novo.bloco == "Variável"


def test_formulario_recusa_valor_zero(banco_ui):
    banco_ui.substituir_tudo(dados_demo(M0))
    antes = len(banco_ui.carregar_dados().lancamentos)
    at = _rodar("p_lancamentos")
    next(t for t in at.text_input if t.label == "O que foi?").set_value("Sem valor")
    next(b for b in at.button if b.label == "Anotar").click()
    at.run()
    assert len(banco_ui.carregar_dados().lancamentos) == antes and at.error


def test_conversao_do_editor_preserva_campos_fora_da_tabela():
    """Salvar a aba Parcelados não pode apagar a taxa de juros (que é editada em Dívidas)."""
    from orcamento.modelos import Parcelado
    from orcamento.ui.componentes import df_para_registros, registros_para_df
    orig = [Parcelado("Sofá", valor=190.0, n_atual=8, mes_ref=M0, total=10, taxa_juros=0.021, id=7)]
    cols = ["id", "item", "valor", "n_atual", "mes_ref", "total"]
    df = registros_para_df(orig, Parcelado, cols)
    df.loc[0, "valor"] = 200.0
    novo = df_para_registros(df, Parcelado, cols, {7: orig[0]})[0]
    assert novo.id == 7 and novo.valor == 200.0 and novo.taxa_juros == 0.021 and novo.mes_ref == M0
