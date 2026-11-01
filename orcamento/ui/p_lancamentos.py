"""Lançamentos: anotar gastos do dia a dia."""
from __future__ import annotations

from datetime import date

import streamlit as st

from ..config import BLOCOS, CATEGORIAS_PADRAO, CLASSIFICACOES, SEM_ENVELOPE
from ..formatacao import mes_extenso, moeda
from ..modelos import Lancamento, somar_meses
from .componentes import cabecalho, cartao, editor_tabela
from .contexto import contexto


def render() -> None:
    ctx = contexto()
    d, mes = ctx.dados, ctx.mes
    cabecalho("Lançamentos", f"Anote cada compra ou fatura. Mês: <b>{mes_extenso(mes)}</b>.")
    envelopes = [e.nome for e in d.envelopes]
    categorias = sorted(set(CATEGORIAS_PADRAO) | {l.categoria for l in d.lancamentos if l.categoria})
    hoje = date.today()
    padrao = hoje if (hoje.year, hoje.month) == (mes.year, mes.month) else mes

    with st.form("novo_lancamento", clear_on_submit=True):
        st.markdown("##### ➕ Anotar um gasto")
        c = st.columns([1.1, 2, 1.4, 1.2, 1])
        data = c[0].date_input("Data", value=padrao, format="DD/MM/YYYY")
        desc = c[1].text_input("O que foi?")
        cat = c[2].selectbox("Categoria", categorias)
        cls = c[3].selectbox("Classificação", CLASSIFICACOES)
        valor = c[4].number_input("Valor (R$)", min_value=0.0, step=1.0, format="%.2f")
        c2 = st.columns([1.2, 1.6, 3])
        bloco = c2[0].selectbox("Bloco", BLOCOS, help="Variável = compras do dia a dia. Fatura = fatura de cartão.")
        env = c2[1].selectbox("Envelope", [""] + envelopes)
        obs = c2[2].text_input("Observação")
        if st.form_submit_button("Anotar", type="primary"):
            if not desc.strip() or valor <= 0:
                st.error("Preencha o que foi e um valor maior que zero.")
            else:
                ctx.banco.inserir(Lancamento(data, desc.strip(), cat, cls, bloco, env, valor, obs))
                st.toast("Gasto anotado!", icon="✅")
                st.rerun()

    doMes = [l for l in d.lancamentos if l.mes == mes]
    var = sum(l.valor for l in doMes if l.bloco == "Variável")
    fat = sum(l.valor for l in doMes if l.bloco == "Fatura")
    sem = sum(1 for l in doMes if l.bloco == "Variável" and not l.envelope)
    c = st.columns(4)
    with c[0]: cartao("Variáveis no mês", moeda(var), f"{len(doMes)} lançamento(s)")
    with c[1]: cartao("Faturas no mês", moeda(fat))
    with c[2]: cartao("Teto de variáveis", moeda(ctx.mp.teto), "limite do mês")
    with c[3]: cartao("Sem envelope", str(sem), "precisam de envelope", "atencao" if sem else "ok")
    st.write("")

    cfg = {"data": st.column_config.DateColumn("Data", format="DD/MM/YYYY", required=True),
           "descricao": st.column_config.TextColumn("Descrição", width="large"),
           "categoria": st.column_config.SelectboxColumn("Categoria", options=categorias),
           "classificacao": st.column_config.SelectboxColumn("Classificação", options=CLASSIFICACOES),
           "bloco": st.column_config.SelectboxColumn("Bloco", options=BLOCOS),
           "envelope": st.column_config.SelectboxColumn("Envelope", options=envelopes),
           "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f", min_value=0),
           "obs": st.column_config.TextColumn("Observação")}

    def ajustar(l: Lancamento) -> None:
        l.data = l.data or mes
        l.envelope = "" if l.envelope == SEM_ENVELOPE else l.envelope

    editor_tabela(ctx, Lancamento, doMes, ["data", "descricao", "categoria", "classificacao", "bloco", "envelope", "valor", "obs"],
                  cfg, "lanc", where="data >= ? AND data < ?", params=(mes.isoformat(), somar_meses(mes, 1).isoformat()), ajustar=ajustar)
    st.caption("Dica: para apagar, selecione a linha na esquerda e aperte Delete; depois clique em Salvar.")
