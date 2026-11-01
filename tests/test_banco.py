from dataclasses import asdict
from datetime import date

from orcamento.banco import Banco, dados_para_json, json_para_dados
from orcamento.modelos import Lancamento, Parcelado, TABELAS


def _sem_ids(lista):
    return [{k: v for k, v in asdict(o).items() if k != "id"} for o in lista]


def test_roundtrip_completo_no_sqlite(banco, demo):
    banco.substituir_tudo(demo)
    lido = banco.carregar_dados()
    assert lido.cfg == demo.cfg
    for nome in TABELAS:
        esperado = _sem_ids(getattr(demo, nome))
        obtido = _sem_ids(getattr(lido, nome))
        if nome == "lancamentos":
            esperado = sorted(esperado, key=lambda x: (x["data"], x["descricao"]))
            obtido = sorted(obtido, key=lambda x: (x["data"], x["descricao"]))
        assert obtido == esperado, nome


def test_campos_opcionais_e_booleanos_sobrevivem(banco):
    from orcamento.modelos import Dados
    d = Dados()
    d.cfg.variaveis_projetados = None
    d.cfg.teto_comprometimento = 0.25
    d.cfg.redirecionar_parcelas = False
    d.parcelados = [Parcelado("X", valor=10.0, n_atual=None, mes_ref=None, total=None, taxa_juros=None)]
    banco.substituir_tudo(d)
    lido = banco.carregar_dados()
    assert lido.cfg.variaveis_projetados is None and lido.cfg.teto_comprometimento == 0.25 and lido.cfg.redirecionar_parcelas is False
    assert lido.parcelados[0].n_atual is None and lido.parcelados[0].taxa_juros is None


def test_sincronizar_insere_atualiza_e_exclui_so_no_escopo(banco):
    a = Lancamento(date(2026, 11, 3), "A", valor=10.0)
    b = Lancamento(date(2026, 11, 4), "B", valor=20.0)
    fora = Lancamento(date(2026, 12, 1), "Dezembro", valor=99.0)
    for l in (a, b, fora):
        banco.inserir(l)
    escopo = ("data >= ? AND data < ?", ("2026-11-01", "2026-12-01"))
    do_mes = banco.listar(Lancamento, *escopo)
    do_mes[0].valor = 11.0                    # atualiza A
    novo = Lancamento(date(2026, 11, 9), "C", valor=30.0)
    banco.sincronizar(Lancamento, [do_mes[0], novo], *escopo)   # B some do escopo => excluído
    nomes = sorted(l.descricao for l in banco.listar(Lancamento))
    assert nomes == ["A", "C", "Dezembro"]                       # dezembro (fora do escopo) intacto
    assert next(l for l in banco.listar(Lancamento) if l.descricao == "A").valor == 11.0


def test_backup_json_ida_e_volta(demo):
    volta = json_para_dados(dados_para_json(demo))
    assert volta.cfg == demo.cfg
    assert _sem_ids(volta.fixas) == _sem_ids(demo.fixas) and _sem_ids(volta.lancamentos) == _sem_ids(demo.lancamentos)


def test_backup_do_banco_gera_copia(banco, demo, tmp_path):
    banco.substituir_tudo(demo)
    copia = banco.backup(tmp_path / "pasta" / "copia.db")
    assert Banco(copia).carregar_dados().renda_base == demo.renda_base


def test_esta_vazio(banco, demo):
    assert banco.esta_vazio()
    banco.substituir_tudo(demo)
    assert not banco.esta_vazio()
