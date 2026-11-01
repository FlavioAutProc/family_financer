"""Folha de anotações em PDF (A4) para conferência manual."""
from __future__ import annotations

import streamlit as st

from ..formatacao import mes_extenso
from ..relatorios import gerar_folha_anotacoes
from .componentes import cabecalho
from .contexto import contexto


def render() -> None:
    ctx = contexto()
    cabecalho("Folha de anotações", "Imprima para conferir no papel: resumo, semanas, envelopes, fixas, parcelas, lançamentos e linhas em branco.")
    st.markdown(f"Mês de referência: **{mes_extenso(ctx.mes)}** (troque na barra lateral). O PDF sai em **4 páginas A4 em pé**:")
    st.markdown("1. Resumo, semana a semana, envelopes e contas fixas  \n2. Parcelas, reserva e gastos possíveis  \n3. Lançamentos do mês (com ☐ para conferir)  \n4. Novos gastos à mão, conferência final e observações")
    if st.button("📄 Gerar PDF", type="primary"):
        st.session_state["pdf_folha"] = (ctx.mes, gerar_folha_anotacoes(ctx.dados, ctx.mes))
    gerado = st.session_state.get("pdf_folha")
    if gerado and gerado[0] == ctx.mes:
        st.download_button("⬇️ Baixar folha de anotações (PDF)", gerado[1], file_name=f"folha_anotacoes_{ctx.mes:%Y_%m}.pdf", mime="application/pdf")
        st.success("PDF pronto. Na hora de imprimir, escolha papel A4 e escala 100%.")
