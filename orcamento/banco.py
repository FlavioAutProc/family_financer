"""Persistência em SQLite.

O esquema é derivado das dataclasses de ``modelos.py``. Datas são guardadas como texto
ISO (``YYYY-MM-DD``); booleanos como 0/1. Cada operação abre e fecha sua própria conexão
(o banco é local e pequeno), o que evita problemas de threads no Streamlit.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import types
import typing
from contextlib import contextmanager
from dataclasses import fields, is_dataclass, asdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional, Type, TypeVar

from .config import CAMINHO_BANCO
from .modelos import TABELAS, Configuracoes, Dados

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Conversão tipo Python <-> SQLite
# ---------------------------------------------------------------------------

def _tipo_base(tp: Any) -> Any:
    """Remove o Optional: Optional[float] -> float."""
    origem = typing.get_origin(tp)
    if origem in (typing.Union, types.UnionType):
        restantes = [a for a in typing.get_args(tp) if a is not type(None)]
        return restantes[0] if restantes else str
    return tp


def _tipo_sql(tp: Any) -> str:
    base = _tipo_base(tp)
    if base is float:
        return "REAL"
    if base in (int, bool):
        return "INTEGER"
    return "TEXT"


def _para_sql(valor: Any, tp: Any) -> Any:
    if valor is None:
        return None
    base = _tipo_base(tp)
    if base is date:
        return valor.isoformat() if isinstance(valor, (date, datetime)) else str(valor)
    if base is bool:
        return int(bool(valor))
    return valor


def _de_sql(valor: Any, tp: Any) -> Any:
    base = _tipo_base(tp)
    if valor is None:
        return "" if base is str else None
    if base is date:
        return date.fromisoformat(str(valor)[:10])
    if base is bool:
        return bool(valor)
    if base is float:
        return float(valor)
    if base is int:
        return int(valor)
    return valor


def _campos(cls: Type[T]) -> list[tuple[str, Any]]:
    dicas = typing.get_type_hints(cls)
    return [(f.name, dicas[f.name]) for f in fields(cls)]


def _colunas_dados(cls: Type[T]) -> list[tuple[str, Any]]:
    return [(n, t) for n, t in _campos(cls) if n != "id"]


def nome_tabela(cls: type) -> str:
    for nome, c in TABELAS.items():
        if c is cls:
            return nome
    raise KeyError(cls)


# ---------------------------------------------------------------------------
# Banco
# ---------------------------------------------------------------------------

class Banco:
    def __init__(self, caminho: Path | str | None = None):
        self.caminho = Path(caminho or CAMINHO_BANCO)
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        self._criar_esquema()

    # -- infraestrutura ----------------------------------------------------
    @contextmanager
    def _conexao(self) -> Iterator[sqlite3.Connection]:
        con = sqlite3.connect(self.caminho, timeout=15)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def _criar_esquema(self) -> None:
        with self._conexao() as con:
            con.execute("CREATE TABLE IF NOT EXISTS config (chave TEXT PRIMARY KEY, valor TEXT)")
            for nome, cls in TABELAS.items():
                cols = ", ".join(f"{n} {_tipo_sql(t)}" for n, t in _colunas_dados(cls))
                con.execute(f"CREATE TABLE IF NOT EXISTS {nome} (id INTEGER PRIMARY KEY AUTOINCREMENT, {cols})")
                existentes = {r["name"] for r in con.execute(f"PRAGMA table_info({nome})")}
                for n, t in _colunas_dados(cls):  # migração simples: acrescenta colunas novas
                    if n not in existentes:
                        con.execute(f"ALTER TABLE {nome} ADD COLUMN {n} {_tipo_sql(t)}")
            con.execute("CREATE INDEX IF NOT EXISTS ix_lanc_data ON lancamentos(data)")

    # -- CRUD genérico -------------------------------------------------------
    def listar(self, cls: Type[T], where: str = "", params: Iterable = (), ordem: str = "id") -> list[T]:
        tabela, campos = nome_tabela(cls), _campos(cls)
        sql = f"SELECT * FROM {tabela}" + (f" WHERE {where}" if where else "") + f" ORDER BY {ordem}"
        with self._conexao() as con:
            linhas = con.execute(sql, tuple(params)).fetchall()
        return [cls(**{n: _de_sql(l[n], t) for n, t in campos}) for l in linhas]

    def inserir(self, obj: Any) -> int:
        cls = type(obj)
        cols = _colunas_dados(cls)
        sql = f"INSERT INTO {nome_tabela(cls)} ({', '.join(n for n, _ in cols)}) VALUES ({', '.join('?' * len(cols))})"
        with self._conexao() as con:
            cur = con.execute(sql, [_para_sql(getattr(obj, n), t) for n, t in cols])
            obj.id = cur.lastrowid
        return obj.id

    def atualizar(self, obj: Any) -> None:
        cls = type(obj)
        cols = _colunas_dados(cls)
        sql = f"UPDATE {nome_tabela(cls)} SET {', '.join(n + ' = ?' for n, _ in cols)} WHERE id = ?"
        with self._conexao() as con:
            con.execute(sql, [_para_sql(getattr(obj, n), t) for n, t in cols] + [obj.id])

    def salvar(self, obj: Any) -> int:
        if obj.id is None:
            return self.inserir(obj)
        self.atualizar(obj)
        return obj.id

    def excluir(self, cls: type, id_: int) -> None:
        with self._conexao() as con:
            con.execute(f"DELETE FROM {nome_tabela(cls)} WHERE id = ?", (id_,))

    def sincronizar(self, cls: Type[T], registros: list[T], where: str = "", params: Iterable = ()) -> None:
        """Faz o conteúdo do escopo (``where``) ficar igual a ``registros``.

        Registros com ``id`` são atualizados, sem ``id`` são inseridos, e os que existem
        no banco (dentro do escopo) mas não vieram na lista são excluídos. É o que as
        tabelas editáveis da interface usam ao clicar em "Salvar".
        """
        tabela, cols = nome_tabela(cls), _colunas_dados(cls)
        params = tuple(params)
        with self._conexao() as con:
            sql = f"SELECT id FROM {tabela}" + (f" WHERE {where}" if where else "")
            existentes = {r["id"] for r in con.execute(sql, params)}
            mantidos = set()
            for obj in registros:
                valores = [_para_sql(getattr(obj, n), t) for n, t in cols]
                if obj.id is not None and obj.id in existentes:
                    con.execute(f"UPDATE {tabela} SET {', '.join(n + ' = ?' for n, _ in cols)} WHERE id = ?", valores + [obj.id])
                    mantidos.add(obj.id)
                else:
                    cur = con.execute(f"INSERT INTO {tabela} ({', '.join(n for n, _ in cols)}) VALUES ({', '.join('?' * len(cols))})", valores)
                    obj.id = cur.lastrowid
                    mantidos.add(obj.id)
            for id_ in existentes - mantidos:
                con.execute(f"DELETE FROM {tabela} WHERE id = ?", (id_,))

    # -- configurações ---------------------------------------------------------
    def carregar_config(self) -> Configuracoes:
        dicas = typing.get_type_hints(Configuracoes)
        with self._conexao() as con:
            salvos = {r["chave"]: r["valor"] for r in con.execute("SELECT chave, valor FROM config")}
        cfg = Configuracoes()
        for nome, tp in dicas.items():
            if nome in salvos:
                bruto = json.loads(salvos[nome])
                setattr(cfg, nome, _de_sql(bruto, tp))
        return cfg

    def salvar_config(self, cfg: Configuracoes) -> None:
        dicas = typing.get_type_hints(Configuracoes)
        with self._conexao() as con:
            for nome in dicas:
                valor = _para_sql(getattr(cfg, nome), dicas[nome])
                con.execute("INSERT INTO config (chave, valor) VALUES (?, ?) ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor",
                            (nome, json.dumps(valor)))

    # -- conjunto completo -----------------------------------------------------
    def carregar_dados(self) -> Dados:
        d = Dados(cfg=self.carregar_config())
        for nome, cls in TABELAS.items():
            ordem = "ordem, id" if nome == "envelopes" else ("data, id" if nome == "lancamentos" else "id")
            setattr(d, nome, self.listar(cls, ordem=ordem))
        return d

    def substituir_tudo(self, dados: Dados) -> None:
        """Apaga tudo e grava ``dados`` (usado em importação, restauração e demo)."""
        with self._conexao() as con:
            for nome in TABELAS:
                con.execute(f"DELETE FROM {nome}")
                con.execute("DELETE FROM sqlite_sequence WHERE name = ?", (nome,))
            con.execute("DELETE FROM config")
        self.salvar_config(dados.cfg)
        for nome, cls in TABELAS.items():
            for obj in getattr(dados, nome):
                obj.id = None
                self.inserir(obj)

    def esta_vazio(self) -> bool:
        with self._conexao() as con:
            return all(con.execute(f"SELECT COUNT(*) c FROM {n}").fetchone()["c"] == 0 for n in ("fixas", "parcelados", "lancamentos", "rendas"))

    def backup(self, destino: Path | str) -> Path:
        destino = Path(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.caminho, destino)
        return destino


# ---------------------------------------------------------------------------
# Serialização completa (backup em JSON)
# ---------------------------------------------------------------------------

def _json_padrao(o: Any) -> Any:
    if isinstance(o, (date, datetime)):
        return o.isoformat()
    raise TypeError(type(o))


def dados_para_json(dados: Dados) -> str:
    corpo = {"versao": 1, "cfg": asdict(dados.cfg)}
    for nome in TABELAS:
        corpo[nome] = [asdict(o) for o in getattr(dados, nome)]
    return json.dumps(corpo, default=_json_padrao, ensure_ascii=False, indent=1)


def json_para_dados(texto: str) -> Dados:
    corpo = json.loads(texto)
    d = Dados()
    dicas = typing.get_type_hints(Configuracoes)
    for nome, tp in dicas.items():
        if nome in corpo.get("cfg", {}):
            setattr(d.cfg, nome, _de_sql(corpo["cfg"][nome], tp))
    for nome, cls in TABELAS.items():
        campos = _campos(cls)
        lista = []
        for item in corpo.get(nome, []):
            lista.append(cls(**{n: _de_sql(item.get(n), t) for n, t in campos if n in item}))
        setattr(d, nome, lista)
    return d
