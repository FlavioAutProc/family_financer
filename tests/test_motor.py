from datetime import date

import pytest

from orcamento.config import ATENCAO, DEFINIR_ENVELOPE, ESTOUROU, OK
from orcamento.modelos import Envelope, Lancamento, Parcelado, Provisao, somar_meses
from orcamento.motor import (envelopes_do_mes, linha_do_tempo, parcelas_restantes, projetar, provisao_mensal,
                             rotulo_parcela, valor_parcela_no_mes)

M0 = date(2026, 11, 1)


def test_linha_do_tempo_tem_36_meses_consecutivos():
    meses = linha_do_tempo(date(2026, 11, 17))
    assert len(meses) == 36 and meses[0] == M0 and meses[-1] == date(2029, 10, 1)


def test_somar_meses_atravessa_o_ano():
    assert somar_meses(date(2026, 11, 1), 3) == date(2027, 2, 1)
    assert somar_meses(date(2026, 1, 1), -1) == date(2025, 12, 1)


def test_parcelado_ativo_apenas_entre_primeira_e_ultima():
    p = Parcelado("Notebook", valor=310.0, n_atual=4, mes_ref=date(2026, 11, 1), total=8)   # 1ª em ago/26, última em mar/27
    assert p.primeira_parcela == date(2026, 8, 1) and p.ultima_parcela == date(2027, 3, 1)
    assert valor_parcela_no_mes(p, date(2026, 7, 1)) == 0
    assert valor_parcela_no_mes(p, date(2026, 11, 1)) == 310.0
    assert valor_parcela_no_mes(p, date(2027, 3, 1)) == 310.0
    assert valor_parcela_no_mes(p, date(2027, 4, 1)) == 0
    assert rotulo_parcela(p, date(2026, 11, 1)) == "4/8"
    assert rotulo_parcela(p, date(2027, 4, 1)) == ""
    assert parcelas_restantes(p, date(2026, 11, 1)) == 5      # 4/8 ... 8/8
    assert parcelas_restantes(p, date(2027, 4, 1)) == 0


def test_parcelado_sem_total_segue_a_regra_de_manter():
    p = Parcelado("Sem total", valor=100.0, n_atual=2, mes_ref=M0, total=None)
    assert valor_parcela_no_mes(p, date(2027, 5, 1), manter_sem_total=True) == 100.0
    assert valor_parcela_no_mes(p, date(2027, 5, 1), manter_sem_total=False) == 0.0
    assert valor_parcela_no_mes(p, M0, manter_sem_total=False) == 100.0
    assert parcelas_restantes(p, M0) is None


def test_projecao_do_cenario_simples(simples):
    proj = projetar(simples)
    nov, dez, jan = proj[0], proj[1], proj[2]
    assert (nov.receita, nov.fixas, nov.parcelas, nov.variaveis, nov.fonte) == (3000, 1000, 500, 800, "Lançado")
    assert nov.total == 2300 and nov.saldo == 700
    assert nov.teto == 1300                         # 3000 − 1000 − 500 − 200
    assert dez.fonte == "Projetado" and dez.variaveis == 800
    assert jan.parcelas == 0 and jan.aporte_extra == 500   # a parcela que acabou vira reserva
    assert jan.teto == 1300                          # o dinheiro liberado não "engorda" o teto
    assert [round(p.reserva_saldo) for p in proj[:3]] == [200, 400, 1100]
    assert nov.comprometimento == pytest.approx(500 / 3000) and jan.comprometimento == 0


def test_provisao_reduz_o_teto_e_aumenta_a_meta_de_sobra(simples):
    simples.provisoes = [Provisao("IPVA", date(2027, 1, 1), 1200.0)]
    assert provisao_mensal(simples) == 100.0
    nov = projetar(simples)[0]
    assert nov.teto == 1200 and nov.aporte_total == 300
    simples.cfg.provisao_por_mes_manual = 250.0
    assert projetar(simples)[0].teto == 1050


def test_ajuste_de_receita_mexe_so_no_mes(simples):
    from orcamento.modelos import AjusteReceita
    simples.ajustes_receita = [AjusteReceita(date(2026, 12, 15), 400.0)]
    proj = projetar(simples)
    assert proj[0].receita == 3000 and proj[1].receita == 3400 and proj[2].receita == 3000


def test_envelopes_status_e_sem_envelope(simples):
    simples.envelopes = [Envelope("Comida", 0.5, 0), Envelope("Avulsos", 0.1, 1)]
    simples.lancamentos = [Lancamento(date(2026, 11, 2), "Mercado", "", "Essencial", "Variável", "Comida", 700.0),     # limite 650
                           Lancamento(date(2026, 11, 3), "Café", "", "Essencial", "Variável", "Avulsos", 100.0),      # limite 130 -> 77%
                           Lancamento(date(2026, 11, 4), "Sem dono", "", "Essencial", "Variável", "", 50.0)]
    proj = projetar(simples)
    env = {e.nome: e for e in envelopes_do_mes(simples, proj, M0)}
    assert env["Comida"].limite == pytest.approx(650) and env["Comida"].status == ESTOUROU
    assert env["Avulsos"].limite == pytest.approx(130) and env["Avulsos"].status == OK
    assert env["(sem envelope)"].gasto == 50 and env["(sem envelope)"].status == DEFINIR_ENVELOPE
    simples.lancamentos[1].valor = 110.0   # 84,6% do limite
    assert {e.nome: e for e in envelopes_do_mes(simples, projetar(simples), M0)}["Avulsos"].status == ATENCAO
