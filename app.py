"""Orçamento Familiar Pro — ponto de entrada (``streamlit run app.py``)."""
import streamlit as st

from orcamento.formatacao import mes_extenso
from orcamento.ui import (p_cadastros, p_config, p_controle, p_cortes, p_dados, p_dividas, p_extras, p_folha, p_futuros,
                          p_historico, p_inicio, p_investimentos, p_lancamentos, p_reserva)
from orcamento.ui.componentes import aplicar_tema
from orcamento.ui.contexto import obter_banco
from orcamento.motor import linha_do_tempo, mes_corrente

st.set_page_config(page_title="Orçamento Familiar Pro", page_icon="💰", layout="wide")
aplicar_tema()

PAGINAS = {
    "Dia a dia": [st.Page(p_inicio.render, title="Início", icon="🏠", url_path="inicio", default=True),
                  st.Page(p_lancamentos.render, title="Lançamentos", icon="✍️", url_path="lancamentos"),
                  st.Page(p_folha.render, title="Folha de anotações", icon="🖨️", url_path="folha")],
    "Acompanhar": [st.Page(p_controle.render, title="Controle", icon="🚦", url_path="controle"),
                   st.Page(p_cortes.render, title="Cortes", icon="✂️", url_path="cortes"),
                   st.Page(p_futuros.render, title="Gastos futuros", icon="🔮", url_path="futuros"),
                   st.Page(p_historico.render, title="Histórico e poupança", icon="📈", url_path="historico")],
    "Planejar": [st.Page(p_dividas.render, title="Dívidas", icon="💳", url_path="dividas"),
                 st.Page(p_extras.render, title="Extras e provisões", icon="🎁", url_path="extras"),
                 st.Page(p_reserva.render, title="Reserva", icon="🛟", url_path="reserva"),
                 st.Page(p_investimentos.render, title="Investimentos", icon="🌱", url_path="investimentos")],
    "Configurar": [st.Page(p_cadastros.render, title="Cadastros", icon="🗂️", url_path="cadastros"),
                   st.Page(p_config.render, title="Configurações", icon="⚙️", url_path="config"),
                   st.Page(p_dados.render, title="Dados", icon="💾", url_path="dados")],
}

# Seletor de mês (vale para todas as telas)
banco = obter_banco()
cfg = banco.carregar_config()
meses = linha_do_tempo(cfg.primeiro_mes)
if st.session_state.get("mes") not in meses:
    st.session_state["mes"] = mes_corrente() if mes_corrente() in meses else meses[0]
with st.sidebar:
    st.markdown("### 💰 Orçamento Familiar")
    st.selectbox("Mês em análise", meses, key="mes", format_func=mes_extenso)
    st.divider()

st.navigation(PAGINAS).run()
