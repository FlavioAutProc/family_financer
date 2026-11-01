from datetime import date

import pytest

from orcamento.analises import (analisar_controle, analisar_cortes, analisar_dividas, analisar_extras, analisar_historico,
                                liberacao_para_investir, projecao_futuros, resumo_carteira, resumo_futuros, saldo_real,
                                simular_aportes, situacao_reserva, valor_presente)
from orcamento.analises.dividas import analisar_outra
from orcamento.config import ATENCAO, OK, PERIGO
from orcamento.modelos import (Extra, GastoFuturo, Investimento, Lancamento, MovReserva, OutraDivida, Parcelado, Provisao)
from orcamento.motor import projetar

M0 = date(2026, 11, 1)


# --- dívidas ------------------------------------------------------------------
def test_valor_presente_confere_com_a_planilha():
    # Empréstimo: 9 parcelas de R$ 87 a 6% ao mês => R$ 591,75 hoje; juros = 783 − 591,75
    vp = valor_presente(87.0, 9, 0.06)
    assert vp == pytest.approx(591.75, abs=0.01)
    assert 87 * 9 - vp == pytest.approx(191.25, abs=0.01)
    assert valor_presente(100.0, 5, 0.0) == 500.0 and valor_presente(100.0, 0, 0.05) == 0.0


def test_prioridade_de_quitacao_maior_taxa_primeiro(simples):
    simples.parcelados = [Parcelado("A", valor=100.0, n_atual=1, mes_ref=M0, total=10, taxa_juros=0.02),
                          Parcelado("B", valor=200.0, n_atual=1, mes_ref=M0, total=10, taxa_juros=0.06),
                          Parcelado("C", valor=50.0, n_atual=1, mes_ref=M0, total=10)]       # sem taxa
    simples.extras = [Extra("13º", "13º salário", date(2026, 12, 1), 6000.0)]               # 30% p/ dívidas = 1.800
    r = analisar_dividas(simples, M0)
    assert [p.divida.item for p in r.prioridade] == ["B", "A"]
    assert r.faltam_taxas and r.com_taxa == 2 and r.ativas == 3
    assert r.verba_extras == pytest.approx(1800)
    assert r.prioridade[0].cabe_nos_extras is True            # B hoje custa ~R$ 1.472
    assert r.prioridade[1].cabe_nos_extras is False           # B + A ~R$ 2.370 passa da verba
    assert r.prioridade[0].divida.saldo_devedor == pytest.approx(valor_presente(200, 10, 0.06))


def test_outras_dividas_nper_e_nunca_quita():
    ok = analisar_outra(OutraDivida("Rotativo", 800.0, 0.12, 100.0))
    assert ok.meses_para_quitar == 29 and ok.juros_mes == pytest.approx(96.0) and ok.juros_ate_quitar == pytest.approx(2100.0)
    assert ok.situacao == ATENCAO                               # mais de 24 meses
    pior = analisar_outra(OutraDivida("Rotativo", 800.0, 0.12, 90.0))
    assert pior.meses_para_quitar == "nunca quita" and pior.situacao == PERIGO


# --- extras e provisões -------------------------------------------------------------
def test_cofrinho_fica_no_vermelho_e_calcula_quanto_guardar(simples):
    simples.provisoes = [Provisao("IPVA", date(2027, 1, 1), 480.0), Provisao("Material escolar", date(2027, 2, 1), 600.0)]
    r = analisar_extras(simples, projetar(simples))
    assert r.provisao_usada == pytest.approx(90.0)
    assert r.linha[1].cofrinho == pytest.approx(180.0) and r.linha[2].cofrinho == pytest.approx(-210.0)
    assert r.primeiro_mes_no_vermelho == date(2027, 1, 1)
    assert r.guardar_para_nunca_faltar == pytest.approx(270.0)   # 1.080 ÷ 4 meses (até fev/27)
    assert r.linha[14].provisoes_a_pagar == pytest.approx(480.0)  # jan/2028: a conta se repete


def test_extras_seguem_a_regra_de_destino_e_antecipam_etapas(simples):
    simples.extras = [Extra("13º", "13º salário", date(2026, 12, 1), 1500.0), Extra("Cancelado", "Renda extra", date(2026, 12, 1), 999.0, "Descartada")]
    r = analisar_extras(simples, projetar(simples))
    dez = r.linha[1]
    assert (dez.extras, dez.reserva, dez.dividas, dez.livre) == (1500, 750, 450, 300)
    assert dez.reserva_com_extras == pytest.approx(400 + 750)
    etapa1 = r.etapas[0]
    assert etapa1.com_extras == date(2026, 12, 1) and (etapa1.antecipa_meses or 0) > 0


# --- gastos futuros ----------------------------------------------------------------------
def test_gastos_futuros_tres_cenarios(simples):
    simples.gastos_futuros = [GastoFuturo("Conserto", "", M0, 1000.0, "Alta", "Possível"),
                              GastoFuturo("Dentista", "", M0, 400.0, "Baixa", "Confirmada"),
                              GastoFuturo("Descartado", "", M0, 700.0, "Alta", "Descartada"),
                              GastoFuturo("Sem mês", "", None, 50.0)]
    proj = projetar(simples)
    nov = projecao_futuros(simples, proj, M0)[0]
    assert nov.esperado == pytest.approx(1000 * 0.75 + 400)
    assert nov.pior_caso == 1400
    assert nov.saldo_confirmado == 700 and nov.saldo_pior == -700 and nov.situacao == PERIGO
    r = resumo_futuros(simples, proj, M0)
    assert r.pior_caso == 1450 and r.itens_sem_mes == 1 and r.reserva_cobre.startswith("Não")


# --- reserva ----------------------------------------------------------------------------------
def test_reserva_saldo_etapas_e_custo_essencial(simples):
    simples.mov_reserva = [MovReserva(date(2026, 11, 5), "Depósito", 300.0), MovReserva(date(2026, 11, 20), "Retirada", 50.0)]
    assert saldo_real(simples) == 250
    s = situacao_reserva(simples, projetar(simples), M0)
    # essencial: aluguel 1.000 + mercado 500 (essencial) + TV 500 = 2.000
    assert s.custo.fixas == 1000 and s.custo.variaveis == 500 and s.custo.parcelas == 500 and s.custo.usado == 2000
    assert [e.meta for e in s.etapas] == [1000, 2000, 6000, 12000]
    assert s.etapas[0].pct == pytest.approx(0.25) and s.proxima_meta == 1000
    assert s.etapas[0].previsao == date(2027, 1, 1)       # plano: 200, 400, 1.100


def test_liberacao_para_investir(simples):
    proj = projetar(simples)
    assert not liberacao_para_investir(simples, proj, M0).liberado
    simples.mov_reserva = [MovReserva(date(2026, 11, 5), "Depósito", 2500.0)]
    assert liberacao_para_investir(simples, proj, M0).liberado


def test_carteira_e_simulador(simples):
    simples.investimentos = [Investimento("Selic", "Tesouro Selic", "X", "Reserva de emergência", "Diária", 1000.0, 1100.0)]
    rc = resumo_carteira(simples)
    assert rc.resultado == 100 and rc.resultado_pct == pytest.approx(0.1) and not rc.confere
    n, aportado, final, rend = simular_aportes(100.0, 0.12, 0.0, (12,))[0]
    assert aportado == 1200
    assert 1200 < final < 1300 and rend == pytest.approx(final - 1200)
    assert simular_aportes(100.0, 0.0, 0.0, (12,))[0][2] == 1200


# --- controle e cortes -----------------------------------------------------------------------------
def test_controle_semaforo_e_ritmo(simples):
    proj = projetar(simples)
    c = analisar_controle(simples, proj, M0, hoje=date(2026, 11, 10))
    v = {x.nome: x for x in c.verificacoes}
    saldo = v["Saldo do mês (receita − despesas)"]
    assert saldo.resultado == 700 and saldo.limite == 200 and saldo.situacao == OK
    var = v["Gastos variáveis do mês × limite (teto)"]
    assert var.resultado == 800 and var.limite == 1300 and var.situacao == OK
    ritmo = v["Ritmo: onde o mês vai fechar se continuar assim"]
    assert ritmo.resultado == pytest.approx(800 / 10 * 30) and ritmo.situacao == PERIGO       # 2.400 > teto 1.300
    assert analisar_controle(simples, proj, M0, hoje=date(2026, 10, 20)).verificacoes[2].situacao == "—"   # mês futuro
    assert [g.descricao for g in c.maiores] == ["Mercado", "Cinema"]


def test_cortes_falta_cortar_e_cartao_nao_se_corta(simples):
    simples.lancamentos.append(Lancamento(date(2026, 11, 12), "Cartão Loja", "", "Não Essencial", "Variável", "", 700.0))   # estoura o teto
    proj = projetar(simples)
    c = analisar_cortes(simples, proj, M0)
    assert c.falta_cortar == pytest.approx(200 - (3000 - 1000 - 500 - 1500))               # meta 200 − saldo 0 = 200
    assert [i.descricao for i in c.nao_essenciais] == ["Cartão Loja", "Cinema"]
    assert c.nao_essenciais[0].economia == 0 and "fatura" in c.nao_essenciais[0].dica
    assert c.nao_essenciais[1].economia == pytest.approx(300 * 0.4)
    assert c.parcelas_encerrando[0].item == "TV" and c.parcelas_encerrando[0].libera_a_partir_de == date(2027, 1, 1)


# --- histórico ----------------------------------------------------------------------------------------
def test_historico_planejado_x_realizado(simples):
    simples.mov_reserva = [MovReserva(date(2026, 11, 5), "Depósito", 200.0)]
    linhas, resumo = analisar_historico(simples, projetar(simples), hoje=date(2026, 12, 15))
    nov, dez, jan = linhas[0], linhas[1], linhas[2]
    assert nov.situacao_mes == "Fechado" and nov.variaveis == 800 and nov.teto == 1300 and nov.resultado == OK
    assert nov.poupado == 200 and nov.taxa_real == pytest.approx(200 / 3000)
    assert dez.situacao_mes == "Em andamento" and dez.resultado == "—"       # sem lançamentos ainda
    assert jan.situacao_mes == "Futuro" and jan.poupado is None
    assert resumo.meses_com_dados == 1 and resumo.meses_no_teto == 1 and resumo.taxa_realizada == pytest.approx(200 / 6000)
