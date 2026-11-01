"""Tela inicial: situação do mês em um olhar."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from ..analises import analisar_controle, analisar_cortes
from ..formatacao import mes_abrev, mes_extenso, moeda
from ..motor import mes_da_projecao
from .componentes import cabecalho, cartao, faixa
from .contexto import contexto


def render() -> None:
    ctx = contexto()
    mp = ctx.mp
    cabecalho("Orçamento da Família", f"Mês em análise: <b>{mes_extenso(ctx.mes)}</b> — troque o mês na barra lateral.")
    if ctx.banco.esta_vazio():
        faixa("O sistema ainda está vazio. Abra <b>Dados</b> no menu para importar sua planilha ou carregar um exemplo.", "atencao")
        return
    ctl = analisar_controle(ctx.dados, ctx.proj, ctx.mes)
    cortes = analisar_cortes(ctx.dados, ctx.proj, ctx.mes)
    if mp.saldo < 0:
        faixa(f"ATENÇÃO: neste mês as contas passam da renda em {moeda(-mp.saldo)}", "perigo")
    elif mp.saldo < mp.aporte_total:
        faixa(f"CUIDADO: fecha no azul (sobram {moeda(mp.saldo)}), mas não dá para guardar tudo na reserva", "atencao")
    else:
        faixa(f"TUDO CERTO: sobram {moeda(mp.saldo)} e dá para guardar na reserva", "ok")

    c = st.columns(6)
    with c[0]: cartao("Entrou", moeda(mp.receita), "renda do mês")
    with c[1]: cartao("Saiu (previsto)", moeda(mp.total), "fixas + parcelas + gastos")
    with c[2]: cartao("Sobra / falta", moeda(mp.saldo), "o que sobra (ou falta)", "ok" if mp.saldo >= mp.aporte_total else ("atencao" if mp.saldo >= 0 else "perigo"))
    with c[3]:
        restante = mp.teto - ctl.gasto_variaveis
        cartao("Ainda posso gastar", moeda(restante), "do limite dos variáveis", "ok" if restante >= 0 else "perigo")
    with c[4]: cartao("Falta cortar", moeda(cortes.falta_cortar), "para fechar no azul e poupar", "ok" if cortes.falta_cortar == 0 else "atencao")
    with c[5]:
        from ..analises import saldo_real
        cartao("Minha reserva", moeda(saldo_real(ctx.dados)), f"meta: {moeda(ctx.dados.cfg.meta_reserva)}")

    st.write("")
    st.markdown(f"**{ctl.ok_count} de {len(ctl.verificacoes)} verificações OK** — {ctl.resumo}")

    i0 = ctx.meses.index(ctx.mes)
    janela = ctx.proj[i0:i0 + 12]
    esq, dir_ = st.columns(2)
    with esq:
        fig = go.Figure()
        x = [mes_abrev(p.mes) for p in janela]
        fig.add_bar(x=x, y=[p.receita for p in janela], name="Receitas", marker_color="#2E75B6")
        fig.add_bar(x=x, y=[p.total for p in janela], name="Despesas", marker_color="#C00000")
        fig.add_scatter(x=x, y=[p.saldo for p in janela], name="Saldo", mode="lines+markers", line=dict(color="#548235", width=3))
        fig.update_layout(title="Receitas × despesas × saldo (12 meses)", barmode="group", height=340, margin=dict(t=50, b=10, l=10, r=10), legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, width="stretch")
    with dir_:
        fig = go.Figure()
        fig.add_scatter(x=[mes_abrev(p.mes) for p in ctx.proj], y=[p.reserva_saldo for p in ctx.proj], name="Reserva acumulada (plano)", line=dict(color="#548235", width=3))
        fig.add_scatter(x=[mes_abrev(p.mes) for p in ctx.proj], y=[p.meta_reserva for p in ctx.proj], name="Meta (etapa 1)", line=dict(color="#7F7F7F", dash="dash"))
        fig.update_layout(title="Reserva acumulada pelo plano (36 meses)", height=340, margin=dict(t=50, b=10, l=10, r=10), legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, width="stretch")
