"""Extras (13º, férias...) e provisões anuais."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ..analises import analisar_extras, soma_percentuais
from ..config import SITUACOES_EXTRA, SITUACOES_PROVISAO, TIPOS_EXTRA
from ..formatacao import mes_abrev, moeda
from ..modelos import Extra, Provisao
from .componentes import cabecalho, cartao, colorir_status, editor_tabela, faixa, opcional_input, percentual_input
from .contexto import contexto


def _txt(v) -> str:
    return mes_abrev(v) if hasattr(v, "year") else str(v)


def render() -> None:
    ctx = contexto()
    d, cfg = ctx.dados, ctx.dados.cfg
    cabecalho("Extras e provisões", "Extras (13º, férias, restituição, renda extra) ficam <b>fora</b> do orçamento mensal: não aumentam o teto de gastos, só vão para as metas. "
                                    "Provisões são gastos anuais guardados aos poucos em um “cofrinho”.")
    r = analisar_extras(d, ctx.proj)

    st.markdown("##### 1. Regra de destino do dinheiro extra")
    with st.form("destino"):
        c = st.columns(4)
        with c[0]: a = percentual_input("Reserva de emergência (%)", cfg.destino_reserva, "d_res")
        with c[1]: b = percentual_input("Quitar dívidas (%)", cfg.destino_dividas, "d_div")
        with c[2]: i = percentual_input("Investir (%)", cfg.destino_investir, "d_inv")
        with c[3]: l = percentual_input("Gastar livremente (%)", cfg.destino_livre, "d_liv")
        if st.form_submit_button("Salvar regra", type="primary"):
            if abs(a + b + i + l - 1) > 0.0001:
                st.error(f"A soma precisa ser 100%. Hoje: {(a + b + i + l) * 100:.0f}%.")
            else:
                cfg.destino_reserva, cfg.destino_dividas, cfg.destino_investir, cfg.destino_livre = a, b, i, l
                ctx.banco.salvar_config(cfg)
                st.rerun()
    if abs(soma_percentuais(d) - 1) > 0.0001:
        faixa(f"ATENÇÃO: a soma dos percentuais está em {soma_percentuais(d) * 100:.0f}%.", "perigo")

    st.markdown("##### 2. Entradas extras")
    meses = ctx.meses
    editor_tabela(ctx, Extra, d.extras, ["descricao", "tipo", "mes", "valor", "situacao", "obs"],
                  {"descricao": st.column_config.TextColumn("Descrição", width="large"), "tipo": st.column_config.SelectboxColumn("Tipo", options=TIPOS_EXTRA),
                   "mes": st.column_config.DateColumn("Mês", format="MM/YYYY", min_value=meses[0], max_value=meses[-1]),
                   "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f", min_value=0),
                   "situacao": st.column_config.SelectboxColumn("Situação", options=SITUACOES_EXTRA), "obs": st.column_config.TextColumn("Observação")},
                  "extras", ajustar=lambda e: setattr(e, "situacao", e.situacao or "Prevista"))
    from ..analises import partes_extra
    ativos = [e for e in d.extras if e.situacao != "Descartada" and e.valor]
    if ativos:
        tot = {k: sum(partes_extra(d, e.valor)[k] for e in ativos) for k in ("reserva", "dividas", "investir", "livre")}
        st.caption(f"Total previsto: {moeda(sum(e.valor for e in ativos))} → reserva {moeda(tot['reserva'])} · dívidas {moeda(tot['dividas'])} · investir {moeda(tot['investir'])} · livre {moeda(tot['livre'])}")

    st.markdown("##### 3. Provisões anuais (IPVA, material escolar, presentes, Natal...)")
    editor_tabela(ctx, Provisao, d.provisoes, ["descricao", "mes", "valor", "situacao", "obs"],
                  {"descricao": st.column_config.TextColumn("Descrição", width="large"),
                   "mes": st.column_config.DateColumn("Mês do próximo vencimento", format="MM/YYYY", help="A conta se repete todo ano."),
                   "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f", min_value=0),
                   "situacao": st.column_config.SelectboxColumn("Situação", options=SITUACOES_PROVISAO), "obs": st.column_config.TextColumn("Observação")},
                  "provisoes", ajustar=lambda p: setattr(p, "situacao", p.situacao or "Ativa"))
    with st.form("prov_cfg"):
        c = st.columns(2)
        with c[0]:
            guardado = st.number_input("Já guardado hoje para provisões (R$)", min_value=0.0, value=float(cfg.provisao_guardado_inicial), step=10.0, format="%.2f")
        with c[1]:
            manual = opcional_input("Quanto vou guardar por mês (vazio = total ÷ 12)", cfg.provisao_por_mes_manual, "prov_manual")
        if st.form_submit_button("Salvar", type="primary"):
            cfg.provisao_guardado_inicial, cfg.provisao_por_mes_manual = guardado, manual
            ctx.banco.salvar_config(cfg)
            st.rerun()
    c = st.columns(4)
    with c[0]: cartao("Sugerido por mês", moeda(r.provisao_sugerida), "total ÷ 12")
    with c[1]: cartao("Usado no orçamento", moeda(r.provisao_usada), "sai do teto de variáveis", "atencao" if r.provisao_usada else "neutro")
    with c[2]: cartao("1º mês no vermelho", _txt(r.primeiro_mes_no_vermelho) if r.primeiro_mes_no_vermelho else "nunca", "cofrinho", "perigo" if r.primeiro_mes_no_vermelho else "ok")
    with c[3]: cartao("Para nunca faltar", moeda(r.guardar_para_nunca_faltar), "guardar por mês (36 meses)")

    st.markdown("##### 4. Efeito dos extras nas metas da reserva")
    st.dataframe(pd.DataFrame([{"Etapa": e.nome, "Meta": e.meta, "Pelo plano (sem extras)": _txt(e.pelo_plano), "Com extras": _txt(e.com_extras),
                                "Antecipa em": "—" if e.antecipa_meses is None else f"{e.antecipa_meses} meses"} for e in r.etapas]),
                 hide_index=True, width="stretch", column_config={"Meta": st.column_config.NumberColumn(format="R$ %.2f")})

    st.markdown("##### 5. Linha do tempo — 36 meses")
    df = pd.DataFrame([{"Mês": mes_abrev(l.mes), "Extras": l.extras, "→ Reserva": l.reserva, "→ Dívidas": l.dividas, "→ Investir": l.investir, "→ Livre": l.livre,
                        "Provisão guardada": l.provisao_guardada, "Provisões a pagar": l.provisoes_a_pagar, "Cofrinho": l.cofrinho,
                        "Situação": l.situacao_cofrinho, "Reserva c/ extras": l.reserva_com_extras} for l in r.linha])
    fmt = {c: moeda for c in df.columns if c not in ("Mês", "Situação")}
    st.dataframe(colorir_status(df, ["Situação"]).format(fmt), hide_index=True, width="stretch", height=380)
    fig = go.Figure()
    fig.add_scatter(x=df["Mês"], y=df["Cofrinho"], name="Cofrinho de provisões", line=dict(color="#ED7D31", width=3))
    fig.add_scatter(x=df["Mês"], y=df["Reserva c/ extras"], name="Reserva com extras", line=dict(color="#548235", width=3))
    fig.update_layout(height=340, margin=dict(t=30, b=10), legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, width="stretch")
