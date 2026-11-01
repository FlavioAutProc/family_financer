"""Dívidas: juros, prioridade de quitação e outras dívidas."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from ..analises import analisar_dividas
from ..formatacao import mes_abrev, moeda, pct
from ..modelos import OutraDivida
from .componentes import cabecalho, cartao, colorir_status, faixa
from .contexto import contexto


def render() -> None:
    ctx = contexto()
    d = ctx.dados
    cabecalho("Dívidas — quanto custam os juros e qual quitar primeiro",
              "Informe a taxa de juros <b>ao mês</b> de cada parcelamento (está no contrato ou no app da loja/banco; sem juros, digite 0). Os valores são <b>estimativas</b>: peça o valor de quitação à loja ou ao banco.")
    r = analisar_dividas(d, ctx.mes)
    c = st.columns(5)
    with c[0]: cartao("Ainda vai pagar", moeda(r.total_restante), "em todas as parcelas")
    with c[1]: cartao("Juros restantes", moeda(r.juros_restantes), "onde há taxa informada", "atencao" if r.juros_restantes else "neutro")
    with c[2]: cartao("Saldo devedor", moeda(r.saldo_devedor), "estimado hoje (onde há taxa)")
    with c[3]: cartao("Taxas informadas", f"{r.com_taxa} de {r.ativas}", "parcelamentos ativos", "ok" if not r.faltam_taxas else "atencao")
    with c[4]: cartao("Verba dos extras", moeda(r.verba_extras), "destinada a dívidas")
    if r.faltam_taxas:
        faixa("Faltam taxas: preencha a coluna “Taxa ao mês” na tabela abaixo.", "atencao")

    st.markdown("##### Prioridade de quitação — maior taxa primeiro")
    if r.prioridade:
        st.dataframe(pd.DataFrame([{"Dívida": f"{p.posicao}. {p.divida.item} ({p.divida.rotulo})", "Taxa ao mês": p.divida.taxa, "Quitar hoje custa": p.divida.saldo_devedor,
                                    "Economia de juros": p.divida.juros_restantes, "Libera por mês": p.divida.parcela, "Terminaria em": mes_abrev(p.divida.termina_em),
                                    "Verba necessária (soma)": p.verba_acumulada,
                                    "Cabe nos extras?": "—" if p.cabe_nos_extras is None else ("Sim" if p.cabe_nos_extras else "Não")} for p in r.prioridade]),
                     hide_index=True, width="stretch", column_config={
            "Taxa ao mês": st.column_config.NumberColumn(format="percent"), **{k: st.column_config.NumberColumn(format="R$ %.2f") for k in
             ("Quitar hoje custa", "Economia de juros", "Libera por mês", "Verba necessária (soma)")}})
        p1 = r.prioridade[0].divida
        st.markdown(f"**Quitar a primeira da lista economiza {moeda(p1.juros_restantes)} de juros e libera {moeda(p1.parcela)} por mês.**")
    else:
        st.info("Preencha as taxas para ver a prioridade.")
    st.caption("Estimativa pelo valor presente das parcelas restantes (em geral, ao antecipar, os juros futuros são abatidos). Rotativo do cartão e cheque especial costumam ter juros bem maiores que parcelamentos: se existirem, vêm primeiro.")

    st.markdown("##### Parcelamentos — informe a taxa de juros ao mês")
    base = pd.DataFrame([{"id": ctx.dados.parcelados[x.indice].id, "Item": x.item, "Parcela atual": x.rotulo, "Valor da parcela": x.parcela,
                          "Restantes": x.restantes, "Total restante": x.total_restante,
                          "Taxa ao mês (%)": None if x.taxa is None else round(x.taxa * 100, 4),
                          "Saldo devedor estimado": x.saldo_devedor, "Juros que ainda vai pagar": x.juros_restantes} for x in r.parceladas])
    if base.empty:
        st.info("Cadastre parcelados em Cadastros → Parcelados.")
    else:
        ed = st.data_editor(base, hide_index=True, width="stretch", key="ed_taxas",
                            disabled=[c for c in base.columns if c != "Taxa ao mês (%)"],
                            column_config={"id": None, "Valor da parcela": st.column_config.NumberColumn(format="R$ %.2f"),
                                           "Total restante": st.column_config.NumberColumn(format="R$ %.2f"),
                                           "Taxa ao mês (%)": st.column_config.NumberColumn(min_value=0.0, max_value=100.0, format="%.2f", help="Ex.: 3,5. Sem juros: 0."),
                                           "Saldo devedor estimado": st.column_config.NumberColumn(format="R$ %.2f"),
                                           "Juros que ainda vai pagar": st.column_config.NumberColumn(format="R$ %.2f")})
        if st.button("💾 Salvar taxas", type="primary", key="bt_taxas"):
            por_id = {p.id: p for p in d.parcelados}
            for _, l in ed.iterrows():
                p = por_id[int(l["id"])]
                p.taxa_juros = None if pd.isna(l["Taxa ao mês (%)"]) else float(l["Taxa ao mês (%)"]) / 100
                ctx.banco.atualizar(p)
            st.toast("Taxas salvas!", icon="✅")
            st.rerun()

    st.markdown("##### Outras dívidas (rotativo do cartão, cheque especial, empréstimos fora dos parcelados)")
    df = pd.DataFrame([{"id": o.id, "Descrição": o.descricao, "Saldo devedor (R$)": o.saldo,
                        "Taxa ao mês (%)": None if o.taxa is None else round(o.taxa * 100, 4), "Pagamento por mês (R$)": o.pagamento} for o in d.outras_dividas],
                      columns=["id", "Descrição", "Saldo devedor (R$)", "Taxa ao mês (%)", "Pagamento por mês (R$)"])
    ed2 = st.data_editor(df, hide_index=True, num_rows="dynamic", width="stretch", key="ed_outras",
                         column_config={"id": None, "Saldo devedor (R$)": st.column_config.NumberColumn(format="R$ %.2f", min_value=0),
                                        "Taxa ao mês (%)": st.column_config.NumberColumn(format="%.2f", min_value=0, max_value=100),
                                        "Pagamento por mês (R$)": st.column_config.NumberColumn(format="R$ %.2f", min_value=0)})
    if st.button("💾 Salvar outras dívidas", type="primary", key="bt_outras"):
        novas = []
        for _, l in ed2.iterrows():
            if pd.isna(l["Descrição"]) and pd.isna(l["Saldo devedor (R$)"]):
                continue
            novas.append(OutraDivida(
                descricao="" if pd.isna(l["Descrição"]) else str(l["Descrição"]),
                saldo=0.0 if pd.isna(l["Saldo devedor (R$)"]) else float(l["Saldo devedor (R$)"]),
                taxa=None if pd.isna(l["Taxa ao mês (%)"]) else float(l["Taxa ao mês (%)"]) / 100,
                pagamento=None if pd.isna(l["Pagamento por mês (R$)"]) else float(l["Pagamento por mês (R$)"]),
                id=None if pd.isna(l["id"]) else int(l["id"])))
        ctx.banco.sincronizar(OutraDivida, novas)
        st.toast("Salvo!", icon="✅")
        st.rerun()
    if r.outras:
        st.dataframe(colorir_status(pd.DataFrame([{"Descrição": o.descricao, "Juros por mês": o.juros_mes, "Meses para quitar": o.meses_para_quitar,
                                                  "Juros até quitar": o.juros_ate_quitar, "Situação": o.situacao} for o in r.outras]), ["Situação"]).format(
            {"Juros por mês": moeda, "Juros até quitar": moeda}, na_rep="—"), hide_index=True, width="stretch")
