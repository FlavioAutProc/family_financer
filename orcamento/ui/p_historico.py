"""Histórico: planejado × realizado e taxa de poupança."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ..analises import analisar_historico
from ..formatacao import mes_abrev, moeda, pct
from .componentes import cabecalho, cartao, colorir_status, percentual_input
from .contexto import contexto


def render() -> None:
    ctx = contexto()
    cfg = ctx.dados.cfg
    cabecalho("Histórico e poupança", "Mês a mês: os gastos variáveis ficaram dentro do teto? Quanto da renda foi poupado de fato? Preenche sozinho conforme você lança gastos e registra depósitos na reserva.")
    linhas, resumo = analisar_historico(ctx.dados, ctx.proj)
    mp = ctx.mp
    c = st.columns(4)
    with c[0]: cartao("Meses com gastos lançados", str(resumo.meses_com_dados))
    with c[1]: cartao("Dentro do teto", f"{resumo.meses_no_teto} de {resumo.meses_com_dados}", tom="ok" if resumo.meses_no_teto == resumo.meses_com_dados else "atencao")
    with c[2]: cartao("Desvio acumulado", moeda(resumo.desvio_acumulado), "variáveis − teto", "ok" if resumo.desvio_acumulado <= 0 else "perigo")
    with c[3]: cartao("Poupança realizada", pct(resumo.taxa_realizada), "média ponderada pela renda")
    with st.form("meta_poup"):
        a, b = st.columns([1, 3])
        with a: meta = percentual_input("Minha meta de poupança (% da renda)", cfg.meta_poupanca, "meta_p")
        with b:
            st.write("")
            st.markdown(f"Para chegar na meta, guardar **{moeda(meta * mp.receita)}** por mês. O plano de hoje guarda **{moeda(mp.aporte_total)}** ({pct(mp.aporte_total / mp.receita if mp.receita else 0)} da renda).")
        if st.form_submit_button("Salvar meta", type="primary"):
            cfg.meta_poupanca = meta
            ctx.banco.salvar_config(cfg)
            st.rerun()

    df = pd.DataFrame([{"Mês": mes_abrev(l.mes), "Situação do mês": l.situacao_mes, "Receita": l.receita, "Teto (plano)": l.teto, "Variáveis gastos": l.variaveis,
                        "Desvio": l.desvio, "Desvio %": l.desvio_pct, "Saldo": l.saldo, "Planejado poupar": l.planejado_poupar, "Poupado de fato": l.poupado,
                        "Taxa real": l.taxa_real, "Taxa planejada": l.taxa_planejada, "Resultado": l.resultado} for l in linhas])
    fmt = {c: moeda for c in ("Receita", "Teto (plano)", "Variáveis gastos", "Desvio", "Saldo", "Planejado poupar", "Poupado de fato")}
    fmt.update({c: (lambda v: pct(v)) for c in ("Desvio %", "Taxa real", "Taxa planejada")})
    st.dataframe(colorir_status(df, ["Resultado"]).format(fmt, na_rep="—"), hide_index=True, width="stretch", height=420)
    st.caption("Resultado: OK = variáveis dentro do teto · ATENÇÃO = até 10% acima · PERIGO = mais de 10% acima. “Poupado de fato” = depósitos menos retiradas da reserva no mês.")

    i0 = 0
    jan = linhas[i0:i0 + 12]
    x = [mes_abrev(l.mes) for l in jan]
    a, b = st.columns(2)
    with a:
        fig = go.Figure()
        fig.add_bar(x=x, y=[l.teto for l in jan], name="Teto (plano)", marker_color="#2E75B6")
        fig.add_bar(x=x, y=[l.variaveis or 0 for l in jan], name="Gasto variável", marker_color="#C00000")
        fig.update_layout(title="Variáveis: teto × gasto (12 meses)", barmode="group", height=320, margin=dict(t=50, b=10), legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, width="stretch")
    with b:
        fig = go.Figure()
        fig.add_bar(x=x, y=[l.taxa_planejada or 0 for l in jan], name="Planejada", marker_color="#A6A6A6")
        fig.add_bar(x=x, y=[l.taxa_real or 0 for l in jan], name="Real", marker_color="#548235")
        fig.update_layout(title="Taxa de poupança: planejada × real", barmode="group", height=320, margin=dict(t=50, b=10), yaxis_tickformat=".0%", legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, width="stretch")
