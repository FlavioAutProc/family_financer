"""Configurações (premissas do plano)."""
from __future__ import annotations

import streamlit as st

from ..formatacao import mes_extenso
from ..motor import linha_do_tempo
from .componentes import cabecalho, opcional_input
from .contexto import contexto


def render() -> None:
    ctx = contexto()
    cfg = ctx.dados.cfg
    cabecalho("Configurações", "Premissas do plano. Mexa só quando algo mudar de verdade (nova meta, novo aporte...).")
    with st.form("cfg"):
        st.markdown("##### Linha do tempo e reserva")
        a, b, c = st.columns(3)
        with a:
            opcoes_primeiro = linha_do_tempo(cfg.primeiro_mes.replace(year=cfg.primeiro_mes.year - 2), 60)
            primeiro = st.selectbox("Primeiro mês da projeção", opcoes_primeiro, index=opcoes_primeiro.index(cfg.primeiro_mes), format_func=mes_extenso)
            aporte = st.number_input("Depósito mensal na reserva (R$)", min_value=0.0, value=float(cfg.reserva_aporte), step=10.0, format="%.2f")
        with b:
            meta = st.number_input("Meta da reserva — etapa 1 (R$)", min_value=0.0, value=float(cfg.meta_reserva), step=100.0, format="%.2f")
            saldo_ini = st.number_input("Saldo inicial da reserva (R$)", min_value=0.0, value=float(cfg.saldo_inicial_reserva), step=50.0, format="%.2f")
        with c:
            redir = st.toggle("Redirecionar parcelas que terminam para a reserva", value=cfg.redirecionar_parcelas)
            meses_redir = [None] + ctx.meses
            atual = cfg.inicio_redirecionamento if cfg.inicio_redirecionamento in meses_redir else None
            inicio = st.selectbox("Redirecionar a partir de", meses_redir, index=meses_redir.index(atual), format_func=lambda m: "—" if m is None else mes_extenso(m))
        st.markdown("##### Projeções (vazio = automático)")
        d1, d2, d3 = st.columns(3)
        with d1:
            var = opcional_input("Variáveis projetados (R$/mês)", cfg.variaveis_projetados, "c_var", "Vazio: usa os lançamentos variáveis do primeiro mês.")
            incluir_fat = st.toggle("Contar faturas de cartão nas despesas", value=cfg.incluir_faturas)
        with d2:
            fat = opcional_input("Faturas projetadas (R$/mês)", cfg.faturas_projetadas, "c_fat", "Vazio: usa as faturas lançadas no primeiro mês.")
            manter = st.toggle("Manter parcelados sem total nos meses seguintes", value=cfg.manter_parcelados_sem_total)
        with d3:
            ref = opcional_input("Parcelas de referência (R$/mês)", cfg.parcelas_referencia, "c_ref", "Vazio: parcelas do mês anterior ao início do redirecionamento.")
            teto_pct = opcional_input("Teto de comprometimento (% da renda)", None if cfg.teto_comprometimento is None else cfg.teto_comprometimento * 100, "c_teto",
                                      "Vazio: igual ao do primeiro mês (só pode cair).")
        if st.form_submit_button("💾 Salvar configurações", type="primary"):
            cfg.primeiro_mes, cfg.reserva_aporte, cfg.meta_reserva, cfg.saldo_inicial_reserva = primeiro, aporte, meta, saldo_ini
            cfg.redirecionar_parcelas, cfg.inicio_redirecionamento = redir, inicio
            cfg.variaveis_projetados, cfg.faturas_projetadas, cfg.incluir_faturas, cfg.manter_parcelados_sem_total = var, fat, incluir_fat, manter
            cfg.parcelas_referencia = ref
            cfg.teto_comprometimento = None if teto_pct is None else teto_pct / 100
            ctx.banco.salvar_config(cfg)
            st.session_state.pop("mes", None)
            st.toast("Configurações salvas!", icon="✅")
            st.rerun()
