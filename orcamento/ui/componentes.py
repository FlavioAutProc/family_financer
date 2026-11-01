"""Componentes visuais reutilizáveis e editor genérico de tabelas."""
from __future__ import annotations

import typing
from dataclasses import fields
from datetime import date, datetime
from typing import Any, Optional, Type

import pandas as pd
import streamlit as st

from ..banco import _tipo_base
from ..config import ATENCAO, DEFINIR_ENVELOPE, ESTOUROU, OK, PERIGO
from ..modelos import primeiro_dia
from .contexto import Contexto

AZUL, VERDE, AMARELO, VERMELHO, CINZA = "#1F3864", "#548235", "#FFC000", "#C00000", "#7F7F7F"
TONS = {"ok": ("#E2F0D9", "#548235"), "atencao": ("#FFF2CC", "#BF9000"), "perigo": ("#FBE0E0", "#C00000"),
        "neutro": ("#EAF1FB", "#1F3864")}
CAMPOS_MES = {"mes", "inicio", "fim", "mes_ref"}

CSS = """
<style>
.block-container {padding-top: 2.2rem; max-width: 1250px;}
.cartao {border-radius: 14px; padding: 14px 16px; border: 1px solid rgba(0,0,0,.08); height: 100%;}
.cartao .t {font-size: .74rem; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; opacity: .75;}
.cartao .v {font-size: 1.55rem; font-weight: 800; line-height: 1.25;}
.cartao .l {font-size: .78rem; opacity: .75;}
.faixa {border-radius: 12px; padding: 14px 18px; font-weight: 700; font-size: 1.05rem; margin: 6px 0 14px 0;}
.titulo {font-size: 1.9rem; font-weight: 800; color: #1F3864; margin-bottom: 0;}
.subtitulo {color: #595959; margin-bottom: 14px;}
</style>
"""


def aplicar_tema() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def cabecalho(titulo: str, subtitulo: str = "") -> None:
    st.markdown(f'<div class="titulo">{titulo}</div><div class="subtitulo">{subtitulo}</div>', unsafe_allow_html=True)


def cartao(titulo: str, valor: str, legenda: str = "", tom: str = "neutro") -> None:
    fundo, cor = TONS[tom]
    st.markdown(f'<div class="cartao" style="background:{fundo}"><div class="t">{titulo}</div>'
                f'<div class="v" style="color:{cor}">{valor}</div><div class="l">{legenda}</div></div>', unsafe_allow_html=True)


def faixa(texto: str, tom: str = "neutro") -> None:
    fundo, cor = TONS[tom]
    st.markdown(f'<div class="faixa" style="background:{fundo};color:{cor};border:1px solid {cor}33">{texto}</div>', unsafe_allow_html=True)


def tom_status(status: str) -> str:
    return {OK: "ok", ATENCAO: "atencao", DEFINIR_ENVELOPE: "atencao", PERIGO: "perigo", ESTOUROU: "perigo", "ACIMA": "perigo"}.get(status, "neutro")


def colorir_status(df: pd.DataFrame, colunas: list[str]):
    """Styler que pinta células de status (OK / ATENÇÃO / PERIGO / ESTOUROU)."""
    def cor(v):
        t = tom_status(str(v))
        if t == "neutro":
            return ""
        fundo, fonte = TONS[t]
        return f"background-color:{fundo};color:{fonte};font-weight:700;text-align:center"
    est = df.style
    aplicar = getattr(est, "map", None) or est.applymap
    return aplicar(cor, subset=[c for c in colunas if c in df.columns])


def mostrar_df(df: pd.DataFrame, status: Optional[list[str]] = None, **kw) -> None:
    st.dataframe(colorir_status(df, status) if status else df, hide_index=True, width="stretch", **kw)


# ---------------------------------------------------------------------------
# Editor genérico: DataFrame editável <-> registros do banco
# ---------------------------------------------------------------------------

def _vazio(v: Any) -> bool:
    return v is None or (isinstance(v, float) and pd.isna(v)) or v is pd.NaT or (isinstance(v, str) and not v.strip())


def registros_para_df(registros: list, cls: type, colunas: list[str]) -> pd.DataFrame:
    dicas = typing.get_type_hints(cls)
    linhas = []
    for r in registros:
        linhas.append({c: getattr(r, c) for c in colunas})
    df = pd.DataFrame(linhas, columns=colunas)
    for c in colunas:
        base = _tipo_base(dicas[c])
        if base is date:
            df[c] = pd.to_datetime(df[c])
        elif base is float:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("float64")
        elif base is int and c != "id":
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("Float64")
    return df


def df_para_registros(df: pd.DataFrame, cls: Type, colunas: list[str], originais: Optional[dict[int, Any]] = None) -> list:
    """Converte o DataFrame editado em objetos ``cls``; campos fora de ``colunas`` são preservados pelo id."""
    dicas = typing.get_type_hints(cls)
    saida = []
    for _, linha in df.iterrows():
        if all(_vazio(linha[c]) for c in colunas if c != "id"):
            continue
        base_obj = None
        id_ = None if "id" not in colunas or _vazio(linha.get("id")) else int(linha["id"])
        if originais and id_ in originais:
            base_obj = originais[id_]
        kwargs: dict[str, Any] = {}
        for f in fields(cls):
            if f.name == "id":
                continue
            if f.name in colunas:
                v = linha[f.name]
                tipo = _tipo_base(dicas[f.name])
                opcional = typing.get_origin(dicas[f.name]) is not None
                if _vazio(v):
                    v = None if opcional else ("" if tipo is str else (0.0 if tipo is float else (0 if tipo is int else None)))
                elif tipo is date:
                    v = pd.to_datetime(v).date()
                    if f.name in CAMPOS_MES:
                        v = primeiro_dia(v)
                elif tipo is float:
                    v = float(v)
                elif tipo is int:
                    v = int(v)
                elif tipo is bool:
                    v = bool(v)
                else:
                    v = str(v)
                kwargs[f.name] = v
            elif base_obj is not None:
                kwargs[f.name] = getattr(base_obj, f.name)
        saida.append(cls(id=id_, **kwargs))
    return saida


def editor_tabela(ctx: Contexto, cls: Type, registros: list, colunas: list[str], config: dict, chave: str,
                  where: str = "", params: tuple = (), dinamico: bool = True, altura: Optional[int] = None,
                  ajustar: Optional[Any] = None, rotulo_salvar: str = "💾 Salvar alterações") -> bool:
    """Tabela editável com botão Salvar. Devolve True se salvou (a página é recarregada)."""
    cols = ["id"] + colunas
    df = registros_para_df(registros, cls, cols)
    extra = {"height": altura} if altura else {}
    editado = st.data_editor(df, column_config={"id": None, **config}, num_rows="dynamic" if dinamico else "fixed",
                             hide_index=True, width="stretch", key=f"ed_{chave}", **extra)
    if st.button(rotulo_salvar, key=f"bt_{chave}", type="primary"):
        novos = df_para_registros(editado, cls, cols, {r.id: r for r in registros})
        if ajustar:
            for o in novos:
                ajustar(o)
        ctx.banco.sincronizar(cls, novos, where, params)
        st.toast("Salvo!", icon="✅")
        st.rerun()
    return False


def percentual_input(rotulo: str, valor: float, chave: str, **kw) -> float:
    """Campo de porcentagem (digita 40 = 40%). Devolve fração (0.40)."""
    return st.number_input(rotulo, min_value=0.0, max_value=100.0, value=round((valor or 0.0) * 100, 4), step=0.5, key=chave, format="%.2f", **kw) / 100.0


def opcional_input(rotulo: str, valor: Optional[float], chave: str, ajuda: str = "") -> Optional[float]:
    """Número opcional: vazio significa 'automático'."""
    txt = st.text_input(rotulo, value="" if valor is None else f"{valor:.2f}".replace(".", ","), key=chave, help=ajuda or "Deixe vazio para o sistema calcular sozinho.")
    txt = txt.strip().replace("R$", "").replace(".", "").replace(",", ".") if txt and txt.count(",") else txt.strip().replace("R$", "")
    try:
        return float(txt) if txt else None
    except ValueError:
        st.warning(f"“{rotulo}”: digite só números (ex.: 150,00).")
        return valor
