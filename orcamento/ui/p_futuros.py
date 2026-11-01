"""Gastos futuros: despesas possíveis, mas não garantidas."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ..analises import peso_futuro, projecao_futuros, resumo_futuros
from ..config import CATEGORIAS_PADRAO, CHANCES, SITUACOES_FUTURO
from ..formatacao import mes_abrev, moeda
from ..modelos import GastoFuturo
from .componentes import cabecalho, cartao, editor_tabela, faixa, mostrar_df, percentual_input
from .contexto import contexto


def render() -> None:
    ctx = contexto()
    d, cfg = ctx.dados, ctx.dados.cfg
    cabecalho("Gastos futuros", "Anote o que <b>pode</b> acontecer (emergência, conserto, compra incerta). Fica por fora das contas reais: só entra na análise.")
    r = resumo_futuros(d, ctx.proj, ctx.mes)
    c = st.columns(4)
    with c[0]: cartao("Pior caso", moeda(r.pior_caso), "tudo acontece")
    with c[1]: cartao("Valor esperado", moeda(r.esperado), "cada gasto × sua chance")
    with c[2]: cartao("Reserva hoje", moeda(r.reserva))
    with c[3]: cartao("Meses negativos (pior caso)", str(r.meses_negativos), "nos próximos 12", "ok" if r.meses_negativos == 0 else "perigo")
    faixa(f"A reserva dá conta? {r.reserva_cobre}", "ok" if r.reserva_cobre.startswith("Sim") or r.reserva_cobre.startswith("Nenhum") else ("atencao" if r.reserva_cobre.startswith("Em parte") else "perigo"))
    if r.itens_sem_mes:
        st.warning(f"{r.itens_sem_mes} item(ns) sem mês previsto: não entram na projeção.")

    st.markdown("##### Anote aqui (uma linha por gasto possível)")
    meses = ctx.meses
    cfgcol = {"descricao": st.column_config.TextColumn("O que pode acontecer", width="large"),
              "categoria": st.column_config.SelectboxColumn("Categoria", options=CATEGORIAS_PADRAO),
              "mes": st.column_config.DateColumn("Mês previsto", format="MM/YYYY", min_value=meses[0], max_value=meses[-1]),
              "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f", min_value=0),
              "chance": st.column_config.SelectboxColumn("Chance", options=CHANCES, help="Em branco conta como Média."),
              "situacao": st.column_config.SelectboxColumn("Situação", options=SITUACOES_FUTURO,
                                                           help="Possível = incerto · Confirmada = vai acontecer · Já lançado = virou gasto real (sai desta conta) · Descartada = não vai mais acontecer."),
              "obs": st.column_config.TextColumn("Observação")}
    def ajustar(g: GastoFuturo):
        g.chance, g.situacao = g.chance or "Média", g.situacao or "Possível"
    editor_tabela(ctx, GastoFuturo, d.gastos_futuros, ["descricao", "categoria", "mes", "valor", "chance", "situacao", "obs"], cfgcol, "futuros", ajustar=ajustar)

    with st.expander("⚙️ Quanto vale cada nível de chance"):
        with st.form("chances"):
            a, b, cc = st.columns(3)
            with a: lo = percentual_input("Baixa (%)", cfg.chance_baixa, "ch_b")
            with b: me = percentual_input("Média (%)", cfg.chance_media, "ch_m")
            with cc: hi = percentual_input("Alta (%)", cfg.chance_alta, "ch_a")
            if st.form_submit_button("Aplicar", type="primary"):
                cfg.chance_baixa, cfg.chance_media, cfg.chance_alta = lo, me, hi
                ctx.banco.salvar_config(cfg)
                st.rerun()

    st.markdown("##### Projeção parcial — próximos 12 meses")
    linhas = projecao_futuros(d, ctx.proj, ctx.mes)
    df = pd.DataFrame([{"Mês": mes_abrev(l.mes), "Receita": l.receita, "Despesas confirmadas": l.despesas, "Saldo confirmado": l.saldo_confirmado,
                        "Possíveis (esperado)": l.esperado, "Saldo esperado": l.saldo_esperado, "Possíveis (pior caso)": l.pior_caso,
                        "Saldo no pior caso": l.saldo_pior, "Situação": l.situacao} for l in linhas])
    from .componentes import colorir_status
    moeda_cols = {c: moeda for c in df.columns if c not in ("Mês", "Situação")}
    st.dataframe(colorir_status(df, ["Situação"]).format(moeda_cols), hide_index=True, width="stretch")
    st.caption("OK = fecha no azul mesmo no pior caso · ATENÇÃO = fecha no azul no valor esperado, mas não no pior caso · PERIGO = não fecha nem no valor esperado.")
    fig = go.Figure()
    x = [l["Mês"] for l in df.to_dict("records")]
    for nome, col, cor in (("Confirmado", "Saldo confirmado", "#2E75B6"), ("Esperado", "Saldo esperado", "#ED7D31"), ("Pior caso", "Saldo no pior caso", "#C00000")):
        fig.add_scatter(x=x, y=df[col], name=nome, mode="lines+markers", line=dict(color=cor, width=3))
    fig.update_layout(title="Saldo do mês: confirmado × esperado × pior caso", height=360, margin=dict(t=50, b=10), legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, width="stretch")
