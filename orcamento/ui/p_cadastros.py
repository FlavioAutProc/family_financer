"""Cadastros: rendas, fixas, parcelados, envelopes e ajustes de receita."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from ..config import CATEGORIAS_PADRAO, CLASSIFICACOES
from ..formatacao import moeda, pct
from ..modelos import AjusteReceita, Envelope, Fixa, Parcelado, Renda
from .componentes import cabecalho, editor_tabela, faixa
from .contexto import contexto


def render() -> None:
    ctx = contexto()
    d = ctx.dados
    cabecalho("Cadastros", "Cadastre uma vez; o sistema espalha pelos meses. Depois de editar, clique em <b>Salvar</b>.")
    abas = st.tabs(["💵 Rendas", "🏠 Fixas", "🧾 Parcelados", "✉️ Envelopes", "➕ Ajustes de receita"])
    meses = ctx.meses

    with abas[0]:
        st.caption("Rendas mensais (salário, renda do cônjuge, outras). A soma é a receita-base de todos os meses.")
        editor_tabela(ctx, Renda, d.rendas, ["descricao", "valor"],
                      {"descricao": st.column_config.TextColumn("Descrição", width="large"), "valor": st.column_config.NumberColumn("Valor mensal", format="R$ %.2f", min_value=0)}, "rendas")
        st.markdown(f"**Renda total por mês: {moeda(d.renda_base)}**")

    with abas[1]:
        st.caption("O valor entra em todos os meses entre **Início** e **Fim** (vazio = sem limite). Se o valor mudar, encerre a linha e crie outra.")
        editor_tabela(ctx, Fixa, d.fixas, ["item", "categoria", "classificacao", "valor", "inicio", "fim", "obs"],
                      {"item": st.column_config.TextColumn("Item", width="medium"), "categoria": st.column_config.SelectboxColumn("Categoria", options=CATEGORIAS_PADRAO),
                       "classificacao": st.column_config.SelectboxColumn("Classificação", options=CLASSIFICACOES),
                       "valor": st.column_config.NumberColumn("Valor mensal", format="R$ %.2f", min_value=0),
                       "inicio": st.column_config.DateColumn("Início", format="MM/YYYY"), "fim": st.column_config.DateColumn("Fim", format="MM/YYYY"),
                       "obs": st.column_config.TextColumn("Observação", width="large")}, "fixas",
                      ajustar=lambda f: setattr(f, "classificacao", f.classificacao or "Essencial"))

    with abas[2]:
        st.caption("Informe: valor da parcela, a parcela atual (**n**), o mês a que esse n se refere e o total (**m**). O n avança sozinho e o parcelamento some depois da última parcela. As taxas de juros ficam em **Dívidas**.")
        envs = [e.nome for e in d.envelopes]
        editor_tabela(ctx, Parcelado, d.parcelados, ["item", "categoria", "envelope", "valor", "n_atual", "mes_ref", "total", "obs"],
                      {"item": st.column_config.TextColumn("Item"), "categoria": st.column_config.SelectboxColumn("Categoria", options=CATEGORIAS_PADRAO),
                       "envelope": st.column_config.SelectboxColumn("Envelope", options=envs),
                       "valor": st.column_config.NumberColumn("Valor da parcela", format="R$ %.2f", min_value=0),
                       "n_atual": st.column_config.NumberColumn("Parcela (n)", min_value=1, step=1, format="%d"),
                       "mes_ref": st.column_config.DateColumn("Mês desse n", format="MM/YYYY"),
                       "total": st.column_config.NumberColumn("Total (m)", min_value=1, step=1, format="%d", help="Vazio = desconhecido (o sistema avisa em Controle)."),
                       "obs": st.column_config.TextColumn("Observação", width="large")}, "parcelados")

    with abas[3]:
        st.caption("Distribuição do teto de gastos variáveis entre envelopes. A soma dos percentuais deve dar 100%.")
        df = pd.DataFrame([{"id": e.id, "Envelope": e.nome, "% do teto": round(e.pct * 100, 2)} for e in d.envelopes], columns=["id", "Envelope", "% do teto"])
        ed = st.data_editor(df, hide_index=True, num_rows="dynamic", width="stretch", key="ed_env",
                            column_config={"id": None, "% do teto": st.column_config.NumberColumn(min_value=0.0, max_value=100.0, format="%.2f")})
        soma = float(ed["% do teto"].fillna(0).sum())
        faixa(f"Soma dos percentuais: {soma:.1f}%" + ("" if abs(soma - 100) < 0.01 else " — ajuste para fechar 100%"), "ok" if abs(soma - 100) < 0.01 else "atencao")
        if st.button("💾 Salvar envelopes", type="primary", key="bt_env"):
            novos = [Envelope(nome=str(l["Envelope"]), pct=float(l["% do teto"] or 0) / 100, ordem=i, id=None if pd.isna(l["id"]) else int(l["id"]))
                     for i, (_, l) in enumerate(ed.iterrows()) if not pd.isna(l["Envelope"]) and str(l["Envelope"]).strip()]
            ctx.banco.sincronizar(Envelope, novos)
            st.toast("Salvo!", icon="✅")
            st.rerun()

    with abas[4]:
        st.caption("Aumento ou redução pontual de receita em um mês (ex.: hora extra, mês sem um salário). Use valores negativos para reduzir.")
        editor_tabela(ctx, AjusteReceita, d.ajustes_receita, ["mes", "valor", "obs"],
                      {"mes": st.column_config.DateColumn("Mês", format="MM/YYYY", min_value=meses[0], max_value=meses[-1]),
                       "valor": st.column_config.NumberColumn("Ajuste (+/−)", format="R$ %.2f"), "obs": st.column_config.TextColumn("Observação", width="large")}, "ajustes")
