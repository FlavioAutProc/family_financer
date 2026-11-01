"""Cortes: onde dá para economizar."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from ..analises import analisar_cortes
from ..formatacao import mes_abrev, mes_extenso, moeda
from .componentes import cabecalho, cartao, faixa, percentual_input
from .contexto import contexto


def render() -> None:
    ctx = contexto()
    cfg = ctx.dados.cfg
    cabecalho("Onde dá para economizar", f"Sugestões automáticas a partir dos lançamentos de <b>{mes_extenso(ctx.mes)}</b>. Nada é cortado sozinho: é uma lista de apoio.")
    with st.expander("⚙️ Ajustar percentuais de corte", expanded=False):
        with st.form("cortes_cfg"):
            a, b = st.columns(2)
            with a: ne = percentual_input("Redução nos gastos NÃO essenciais (%)", cfg.corte_nao_essencial, "pct_ne")
            with b: fx = percentual_input("Redução nas despesas FIXAS (%)", cfg.corte_fixas, "pct_fx")
            if st.form_submit_button("Aplicar", type="primary"):
                cfg.corte_nao_essencial, cfg.corte_fixas = ne, fx
                ctx.banco.salvar_config(cfg)
                st.rerun()
    c = analisar_cortes(ctx.dados, ctx.proj, ctx.mes)
    cols = st.columns(4)
    with cols[0]: cartao("Saldo do mês", moeda(c.saldo), tom="ok" if c.saldo >= 0 else "perigo")
    with cols[1]: cartao("Deveria sobrar", moeda(c.deveria_sobrar), "reserva + provisões")
    with cols[2]: cartao("Falta cortar", moeda(c.falta_cortar), tom="ok" if c.falta_cortar == 0 else "atencao")
    with cols[3]: cartao("Economia sugerida", moeda(c.economia_sugerida), "somando as listas abaixo", "ok" if c.economia_sugerida >= c.falta_cortar else "atencao")
    faixa(c.situacao, "ok" if c.falta_cortar == 0 or c.economia_sugerida >= c.falta_cortar else "atencao")

    def tabela(itens, rotulo_cat):
        return pd.DataFrame([{"Item": i.descricao, rotulo_cat: i.categoria, "Valor": i.valor, "Corte": i.pct_corte, "Economia": i.economia, "Dica": i.dica} for i in itens])
    conf = {"Valor": st.column_config.NumberColumn(format="R$ %.2f"), "Economia": st.column_config.NumberColumn(format="R$ %.2f"),
            "Corte": st.column_config.NumberColumn(format="percent")}
    st.markdown("##### Gastos variáveis não essenciais — maiores primeiro")
    if c.nao_essenciais:
        st.dataframe(tabela(c.nao_essenciais, "Categoria"), hide_index=True, width="stretch", column_config=conf)
    else:
        st.info("Nenhum gasto variável marcado como “Não Essencial” neste mês.")
    st.markdown("##### Despesas fixas — renegociar ou comparar preço")
    if c.fixas:
        st.dataframe(tabela(c.fixas, "Classificação"), hide_index=True, width="stretch", column_config=conf)
    st.markdown("##### Parcelas que terminam em breve — a folga que vem aí")
    if c.parcelas_encerrando:
        st.dataframe(pd.DataFrame([{"Item": p.item, "Última parcela": mes_abrev(p.ultima), "Valor da parcela": p.valor, "Libera a partir de": mes_abrev(p.libera_a_partir_de)} for p in c.parcelas_encerrando]),
                     hide_index=True, width="stretch", column_config={"Valor da parcela": st.column_config.NumberColumn(format="R$ %.2f")})
        st.caption("Regra de ouro: parcela que termina não vira gasto novo. O valor dela vira depósito na reserva (e depois investimento).")
