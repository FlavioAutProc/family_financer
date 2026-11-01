"""Carteira de investimentos e simulador."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ..analises import liberacao_para_investir, resumo_carteira, simular_aportes
from ..config import LIQUIDEZ, OBJETIVOS, TIPOS_INVESTIMENTO
from ..formatacao import moeda, pct
from ..modelos import Investimento
from .componentes import cabecalho, cartao, editor_tabela, faixa, opcional_input, percentual_input
from .contexto import contexto


def render() -> None:
    ctx = contexto()
    d, cfg = ctx.dados, ctx.dados.cfg
    cabecalho("Carteira de investimentos", "Registre onde o dinheiro está aplicado. Atualize o “Valor atual” uma vez por mês. Informação geral — não substitui orientação individual.")
    lib = liberacao_para_investir(d, ctx.proj, ctx.mes)
    faixa(lib.mensagem, "ok" if lib.liberado else "atencao")
    st.caption(f"Reserva real {moeda(lib.reserva_real)} · mínimo para liberar {moeda(lib.reserva_minima)} · saldo do mês {moeda(lib.saldo_mes)}. "
               "Ordem geral de prioridade: 1) reserva 2) reduzir ou quitar dívidas caras 3) aportes mensais.")
    with st.expander("⚙️ Alterar a reserva mínima para liberar investimentos"):
        with st.form("inv_min"):
            v = opcional_input("Reserva mínima (R$) — vazio = 1 mês de contas essenciais", cfg.reserva_minima_investir, "res_min")
            if st.form_submit_button("Aplicar", type="primary"):
                cfg.reserva_minima_investir = v
                ctx.banco.salvar_config(cfg)
                st.rerun()

    st.markdown("##### Minha carteira")
    editor_tabela(ctx, Investimento, d.investimentos, ["produto", "tipo", "instituicao", "objetivo", "liquidez", "aplicado", "atual"],
                  {"produto": st.column_config.TextColumn("Produto / ativo", width="large"), "tipo": st.column_config.SelectboxColumn("Tipo", options=TIPOS_INVESTIMENTO),
                   "instituicao": st.column_config.TextColumn("Instituição"), "objetivo": st.column_config.SelectboxColumn("Objetivo", options=OBJETIVOS),
                   "liquidez": st.column_config.SelectboxColumn("Liquidez", options=LIQUIDEZ),
                   "aplicado": st.column_config.NumberColumn("Valor aplicado", format="R$ %.2f", min_value=0),
                   "atual": st.column_config.NumberColumn("Valor atual", format="R$ %.2f", min_value=0)}, "invest")
    rc = resumo_carteira(d)
    c = st.columns(4)
    with c[0]: cartao("Aplicado", moeda(rc.aplicado))
    with c[1]: cartao("Valor atual", moeda(rc.atual))
    with c[2]: cartao("Resultado", moeda(rc.resultado), pct(rc.resultado_pct), "ok" if rc.resultado >= 0 else "perigo")
    with c[3]: cartao("Conferência com a reserva", "Confere" if rc.confere else "Diferença", f"aplicado como reserva {moeda(rc.aplicado_como_reserva)} × saldo {moeda(rc.saldo_reserva)}", "ok" if rc.confere else "atencao")
    tipos = {k: v for k, v in rc.por_tipo.items() if v > 0}
    if tipos:
        fig = go.Figure(go.Pie(labels=list(tipos), values=list(tipos.values()), hole=.5))
        fig.update_layout(title="Carteira por tipo", height=320, margin=dict(t=50, b=10))
        st.plotly_chart(fig, width="stretch")

    st.markdown("##### Simulador de aportes (estimativa — não é promessa de retorno)")
    with st.form("simulador"):
        x = st.columns(3)
        with x[0]: aporte = st.number_input("Aporte mensal (R$)", min_value=0.0, value=float(cfg.aporte_simulador if cfg.aporte_simulador is not None else cfg.reserva_aporte), step=10.0, format="%.2f")
        with x[1]: taxa = percentual_input("Rendimento líquido ao ano (%)", cfg.rendimento_anual, "rend")
        with x[2]: ini = st.number_input("Valor inicial (R$)", min_value=0.0, value=float(rc.atual), step=100.0, format="%.2f")
        if st.form_submit_button("Simular", type="primary"):
            cfg.aporte_simulador, cfg.rendimento_anual = aporte, taxa
            ctx.banco.salvar_config(cfg)
            st.session_state["sim_inicial"] = ini
    ini = st.session_state.get("sim_inicial", rc.atual)
    aporte = cfg.aporte_simulador if cfg.aporte_simulador is not None else cfg.reserva_aporte
    st.dataframe(pd.DataFrame([{"Prazo": f"{n} meses", "Total aportado": a, "Valor estimado": f, "Rendimento estimado": g}
                               for n, a, f, g in simular_aportes(aporte, cfg.rendimento_anual, ini)]), hide_index=True, width="stretch",
                 column_config={k: st.column_config.NumberColumn(format="R$ %.2f") for k in ("Total aportado", "Valor estimado", "Rendimento estimado")})
    st.caption("Premissa inicial conservadora (10% ao ano líquido de imposto). Confira a taxa real do seu produto.")
