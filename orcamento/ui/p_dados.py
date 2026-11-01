"""Dados: importar a planilha, exportar, backup e dados de exemplo."""
from __future__ import annotations

from datetime import datetime

import streamlit as st

from ..banco import dados_para_json, json_para_dados
from ..demo import dados_demo
from ..exportador import exportar_excel
from ..importador import importar_planilha
from .componentes import cabecalho, faixa
from .contexto import contexto


def render() -> None:
    ctx = contexto()
    cabecalho("Dados", "Traga sua planilha, guarde cópias de segurança e exporte relatórios.")
    t = st.tabs(["📥 Importar planilha", "📤 Exportar", "🛟 Backup", "🧪 Exemplo / limpar"])

    with t[0]:
        st.markdown("Envie o arquivo **Orcamento_Familiar_05.xlsx** (ou versões anteriores). O sistema lê só as células digitadas; as contas ele refaz sozinho.")
        arq = st.file_uploader("Planilha Excel (.xlsx)", type=["xlsx"])
        if arq is not None:
            try:
                dados, rel = importar_planilha(arq)
            except Exception as e:  # arquivo inválido
                st.error(f"Não consegui ler esse arquivo: {e}")
            else:
                st.success("Planilha lida. Confira o que será importado:")
                st.table({"Item": list(rel.contagens), "Quantidade": list(rel.contagens.values())})
                for a in rel.avisos:
                    st.warning(a)
                faixa("Importar <b>substitui</b> todos os dados atuais do sistema.", "atencao")
                if st.checkbox("Entendi, pode substituir"):
                    if st.button("Importar agora", type="primary"):
                        ctx.banco.backup(ctx.banco.caminho.parent / f"antes_da_importacao_{datetime.now():%Y%m%d_%H%M%S}.db")
                        ctx.banco.substituir_tudo(dados)
                        st.session_state.pop("mes", None)
                        st.success("Dados importados! (uma cópia dos dados anteriores foi guardada na pasta dados/)")
                        st.rerun()

    with t[1]:
        st.markdown("Relatório completo em Excel: projeção de 36 meses, lançamentos, fixas, parcelados, gastos futuros, extras, reserva e investimentos.")
        st.download_button("⬇️ Baixar relatório Excel", exportar_excel(ctx.dados), file_name=f"orcamento_{datetime.now():%Y%m%d}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with t[2]:
        st.markdown("O backup em JSON guarda **tudo** (dados e configurações) e pode ser restaurado aqui.")
        st.download_button("⬇️ Baixar backup (JSON)", dados_para_json(ctx.dados), file_name=f"backup_orcamento_{datetime.now():%Y%m%d_%H%M}.json", mime="application/json")
        up = st.file_uploader("Restaurar backup (.json)", type=["json"], key="up_json")
        if up is not None and st.button("Restaurar este backup", type="primary"):
            try:
                ctx.banco.substituir_tudo(json_para_dados(up.getvalue().decode("utf-8")))
                st.session_state.pop("mes", None)
                st.rerun()
            except Exception as e:
                st.error(f"Backup inválido: {e}")

    with t[3]:
        st.markdown("**Dados de exemplo** (família fictícia) para conhecer o sistema. Substituem os dados atuais.")
        if st.button("Carregar exemplo"):
            ctx.banco.substituir_tudo(dados_demo())
            st.session_state.pop("mes", None)
            st.rerun()
        st.divider()
        st.markdown("**Apagar tudo** deixa o sistema vazio (faça um backup antes).")
        if st.checkbox("Tenho certeza que quero apagar tudo") and st.button("Apagar tudo"):
            from ..modelos import Dados
            ctx.banco.substituir_tudo(Dados())
            st.session_state.pop("mes", None)
            st.rerun()
