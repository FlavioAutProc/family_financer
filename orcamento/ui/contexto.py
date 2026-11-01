"""Contexto da sessão: banco, dados carregados, projeção e mês selecionado."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import streamlit as st

from ..banco import Banco
from ..modelos import Dados
from ..motor import MesProj, linha_do_tempo, mes_corrente, projetar


@st.cache_resource
def obter_banco() -> Banco:
    return Banco()


@dataclass
class Contexto:
    banco: Banco
    dados: Dados
    proj: list[MesProj]
    mes: date
    meses: list[date]

    @property
    def mp(self) -> MesProj:
        return next(p for p in self.proj if p.mes == self.mes)


def contexto() -> Contexto:
    banco = obter_banco()
    dados = banco.carregar_dados()
    proj = projetar(dados)
    meses = [p.mes for p in proj]
    mes = st.session_state.get("mes")
    if mes not in meses:
        atual = mes_corrente()
        mes = atual if atual in meses else meses[0]
        st.session_state["mes"] = mes
    return Contexto(banco, dados, proj, mes, meses)
