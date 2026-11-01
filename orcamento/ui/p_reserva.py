"""Reserva de emergência."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from ..analises import situacao_reserva
from ..config import TIPOS_MOVIMENTO
from ..formatacao import mes_abrev, moeda
from ..modelos import MovReserva
from .componentes import cabecalho, cartao, editor_tabela, opcional_input
from .contexto import contexto


def render() -> None:
    ctx = contexto()
    d, cfg = ctx.dados, ctx.dados.cfg
    cabecalho("Reserva de emergência", "Dinheiro guardado para imprevistos (doença, conserto, falta de renda) sem precisar de cartão ou empréstimo. Anote depósitos e retiradas abaixo.")
    s = situacao_reserva(d, ctx.proj, ctx.mes)
    c = st.columns(4)
    with c[0]: cartao("Saldo real", moeda(s.saldo_real), "saldo inicial + depósitos − retiradas", "ok" if s.saldo_real >= s.proxima_meta else "atencao")
    with c[1]: cartao("Pelo plano", moeda(s.planejado_no_mes), "deveria ter no mês")
    with c[2]: cartao("Diferença", moeda(s.diferenca), "em dia ou adiantado" if s.diferenca >= 0 else "atrasado em relação ao plano", "ok" if s.diferenca >= 0 else "perigo")
    with c[3]: cartao("Cobertura", f"{s.meses_cobertura:.1f} meses", "de contas essenciais")

    st.markdown("##### Metas por etapa")
    for e in s.etapas:
        a, b = st.columns([3, 2])
        previsao = e.previsao if isinstance(e.previsao, str) else mes_abrev(e.previsao)
        a.progress(e.pct, text=f"{e.nome} — {moeda(e.ja_tenho)} de {moeda(e.meta)} ({e.pct:.0%})")
        b.caption(f"Falta {moeda(e.falta)} · previsão pelo plano: {previsao}")

    with st.expander("⚙️ Como o tamanho da reserva é calculado", expanded=False):
        k = s.custo
        st.markdown(f"Fixas essenciais: **{moeda(k.fixas)}** + variáveis essenciais: **{moeda(k.variaveis)}** + parcelas: **{moeda(k.parcelas)}** = **{moeda(k.calculado)}** por mês (usado: **{moeda(k.usado)}**).")
        with st.form("reserva_cfg"):
            x = st.columns(3)
            with x[0]: incluir = st.toggle("Incluir parcelas no cálculo", value=cfg.incluir_parcelas_custo_essencial)
            with x[1]: manual = opcional_input("Usar outro custo essencial (R$/mês)", cfg.custo_essencial_manual, "custo_manual")
            with x[2]: meta1 = st.number_input("Meta da etapa 1 (R$)", min_value=0.0, value=float(cfg.meta_reserva), step=100.0, format="%.2f")
            if st.form_submit_button("Aplicar", type="primary"):
                cfg.incluir_parcelas_custo_essencial, cfg.custo_essencial_manual, cfg.meta_reserva = incluir, manual, meta1
                ctx.banco.salvar_config(cfg)
                st.rerun()
        st.caption("Onde guardar: conta separada, de liquidez diária e baixo risco (ex.: Tesouro Selic ou CDB com liquidez diária). Registre a aplicação em Investimentos.")

    st.markdown("##### Registro de depósitos e retiradas")
    from datetime import date
    editor_tabela(ctx, MovReserva, d.mov_reserva, ["data", "tipo", "valor", "obs"],
                  {"data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"), "tipo": st.column_config.SelectboxColumn("Tipo", options=TIPOS_MOVIMENTO, required=True),
                   "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f", min_value=0), "obs": st.column_config.TextColumn("Observação", width="large")},
                  "reserva", ajustar=lambda m: (setattr(m, "data", m.data or date.today()), setattr(m, "tipo", m.tipo or "Depósito")))
