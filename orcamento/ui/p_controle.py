"""Controle: semáforo do mês, maiores gastos e envelopes."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from ..analises import analisar_controle
from ..formatacao import mes_extenso, moeda, pct
from .componentes import cabecalho, faixa, mostrar_df
from .contexto import contexto


def _fmt(v, formato):
    if v is None:
        return "—"
    return pct(v) if formato == "pct" else (str(int(v)) if formato == "inteiro" else moeda(v))


def render() -> None:
    ctx = contexto()
    cabecalho("Controle do mês", f"Verde = OK · Amarelo = atenção · Vermelho = perigo. Mês: <b>{mes_extenso(ctx.mes)}</b>.")
    c = analisar_controle(ctx.dados, ctx.proj, ctx.mes)
    faixa(f"{c.ok_count} de {len(c.verificacoes)} verificações OK — {c.resumo}", "ok" if c.ok_count == len(c.verificacoes) else ("atencao" if c.ok_count >= 5 else "perigo"))

    st.markdown("##### 1. Quanto entrou e quanto saiu")
    mp = c.mp
    base = mp.receita or 1
    df = pd.DataFrame([("Receitas (renda do mês)", mp.receita), ("Despesas fixas", mp.fixas), ("Parcelas", mp.parcelas),
                       ("Gastos variáveis", mp.variaveis), ("Faturas de cartão", mp.faturas), ("Total de despesas", mp.total),
                       ("SALDO DO MÊS", mp.saldo)], columns=["Item", "Valor"])
    df["% da renda"] = df["Valor"] / base
    st.dataframe(df, hide_index=True, width="stretch", column_config={
        "Valor": st.column_config.NumberColumn(format="R$ %.2f"), "% da renda": st.column_config.NumberColumn(format="percent")})

    st.markdown("##### 2. Semáforo — está tudo sob controle?")
    df = pd.DataFrame([{"Verificação": v.nome, "Resultado": _fmt(v.resultado, v.formato), "Meta / limite": _fmt(v.limite, v.formato),
                        "Situação": v.situacao, "O que fazer": v.orientacao} for v in c.verificacoes])
    mostrar_df(df, ["Situação"])

    st.markdown("##### 3. Os 5 maiores gastos variáveis do mês")
    if c.maiores:
        st.dataframe(pd.DataFrame([{"#": g.posicao, "O que foi": g.descricao, "Categoria": g.categoria, "Valor": g.valor,
                                    "% dos variáveis": g.pct_variaveis, "Classificação · Envelope": f"{g.classificacao} · {g.envelope}"} for g in c.maiores]),
                     hide_index=True, width="stretch", column_config={
            "Valor": st.column_config.NumberColumn(format="R$ %.2f"), "% dos variáveis": st.column_config.NumberColumn(format="percent")})
    else:
        st.info("Ainda não há gastos variáveis lançados neste mês.")

    st.markdown("##### 4. Envelopes do mês (limite × gasto)")
    df = pd.DataFrame([{"Envelope": e.nome, "Limite": e.limite, "Gasto": e.gasto, "Já em parcelas": e.parcelado_vinculado,
                        "Saldo": e.saldo, "% usado": min(1.0, e.pct_usado) if e.pct_usado is not None else None, "Situação": e.status} for e in c.envelopes])
    from .componentes import colorir_status
    st.dataframe(colorir_status(df, ["Situação"]).format({"Limite": moeda, "Gasto": moeda, "Já em parcelas": moeda, "Saldo": moeda}, na_rep="—"),
                 hide_index=True, width="stretch",
                 column_config={"% usado": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1)})
