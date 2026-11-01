"""Dados de exemplo (família fictícia) para conhecer o sistema sem digitar nada."""
from __future__ import annotations

from datetime import date

from .modelos import (AjusteReceita, Dados, Envelope, Extra, Fixa, GastoFuturo, Investimento, Lancamento, MovReserva,
                      OutraDivida, Parcelado, Provisao, Renda, primeiro_dia, somar_meses)
from .config import ENVELOPES_PADRAO


def dados_demo(primeiro_mes: date | None = None) -> Dados:
    m0 = primeiro_dia(primeiro_mes or date.today())
    d = Dados()
    c = d.cfg
    c.primeiro_mes, c.reserva_aporte, c.meta_reserva = m0, 400.0, 3000.0
    c.inicio_redirecionamento, c.saldo_inicial_reserva = somar_meses(m0, 6), 0.0
    d.rendas = [Renda("Salário", 4200.0), Renda("Renda do cônjuge", 1800.0)]
    d.fixas = [Fixa("Aluguel", "Moradia", "Essencial", 1400.0), Fixa("Energia e água", "Moradia", "Essencial", 320.0),
               Fixa("Internet e celulares", "Telefonia", "Essencial", 190.0), Fixa("Escola", "Educação", "Essencial", 650.0),
               Fixa("Plano de saúde", "Saúde", "Essencial", 380.0, obs="Pedir reajuste menor ou comparar planos."),
               Fixa("Streaming", "Lazer", "Não Essencial", 55.0)]
    d.parcelados = [
        Parcelado("Geladeira", "Moradia", "Pontuais", 280.0, 3, m0, 10, 0.0),
        Parcelado("Notebook", "Educação", "Pontuais", 310.0, 2, m0, 12, 0.021),
        Parcelado("Empréstimo pessoal", "Financiamento", "", 295.0, 5, m0, 24, 0.034),
        Parcelado("Sofá", "Moradia", "Pontuais", 190.0, 8, m0, 10, 0.0),
    ]
    d.envelopes = [Envelope(n, p, i) for i, (n, p) in enumerate(ENVELOPES_PADRAO)]
    L = lambda dia, desc, cat, cl, val, env="", bloco="Variável": Lancamento(date(m0.year, m0.month, dia), desc, cat, cl, bloco, env, val)
    d.lancamentos = [
        L(2, "Supermercado", "Alimentação", "Essencial", 412.30, "Alimentação e lanches"), L(3, "Padaria", "Alimentação", "Essencial", 38.50, "Alimentação e lanches"),
        L(4, "Farmácia", "Saúde", "Essencial", 86.90, "Saúde e escola"), L(5, "Pizza em família", "Lazer", "Não Essencial", 92.00, "Avulsos"),
        L(7, "Material escolar", "Educação", "Essencial", 74.00, "Saúde e escola"), L(9, "Combustível", "Transporte", "Essencial", 180.00, "Contas de consumo e transporte"),
        L(10, "Recarga de celular", "Telefonia", "Não Essencial", 30.00, "Avulsos"), L(12, "Supermercado", "Alimentação", "Essencial", 298.75, "Alimentação e lanches"),
        L(14, "Cinema", "Lazer", "Não Essencial", 64.00, "Avulsos"), L(15, "Presente de aniversário", "Dependentes", "Não Essencial", 120.00),
        L(16, "Cartão de loja", "Dependentes", "Não Essencial", 240.00, bloco="Fatura"),
    ]
    d.gastos_futuros = [GastoFuturo("Conserto do carro", "Transporte", somar_meses(m0, 1), 900.0, "Média", "Possível"),
                        GastoFuturo("Dentista", "Saúde", somar_meses(m0, 2), 450.0, "Alta", "Possível")]
    d.extras = [Extra("13º salário", "13º salário", date(m0.year, 12, 1), 3000.0, "Prevista")]
    d.provisoes = [Provisao("IPVA", somar_meses(m0, 3), 1200.0), Provisao("Material escolar", somar_meses(m0, 2), 600.0)]
    d.mov_reserva = [MovReserva(date(m0.year, m0.month, 5), "Depósito", 400.0, "Aporte do mês")]
    d.investimentos = [Investimento("Tesouro Selic", "Tesouro Selic", "Corretora X", "Reserva de emergência", "Diária", 380.0, 400.0)]
    d.outras_dividas = [OutraDivida("Cartão rotativo", 650.0, 0.12, 120.0)]
    return d
