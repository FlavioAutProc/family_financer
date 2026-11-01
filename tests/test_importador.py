from datetime import datetime

import openpyxl
import pytest

from orcamento.importador import importar_planilha


@pytest.fixture
def planilha(tmp_path):
    """Planilha mínima no mesmo layout do Orcamento_Familiar_05.xlsx."""
    wb = openpyxl.Workbook()
    ws = wb.active; ws.title = "Premissas"
    for r, (nome, v) in enumerate([("Salário", 2500), ("Renda do cônjuge", 600), ("Outra renda", 0)], start=5):
        ws.cell(r, 1, nome); ws.cell(r, 2, v)
    ws["B11"] = datetime(2026, 11, 1); ws["B12"] = 150; ws["B13"] = "Sim"; ws["B14"] = datetime(2027, 2, 1)
    ws["B15"] = 1000; ws["B16"] = 0
    ws["B17"] = "=SUMIFS(Lançamentos!H:H,Lançamentos!B:B,B11)"       # fórmula -> ignorada (automático)
    ws["B19"] = "Sim"; ws["B20"] = "Não"
    f = wb.create_sheet("Fixas")
    for c, v in enumerate(["Aluguel", "Fixa", "Essencial", 1000, None, None, "obs"], start=1): f.cell(5, c, v)
    p = wb.create_sheet("Parcelados")
    for c, v in enumerate(["TV", "Casa", "Pontuais", 250, 3, datetime(2026, 11, 1), 10, None, None, None, "nota"], start=1): p.cell(5, c, v)
    d = wb.create_sheet("Dívidas"); d.cell(33, 6, 0.035)                  # taxa do 1º parcelado (linha 5 de Parcelados)
    d.cell(23, 1, "Rotativo"); d.cell(23, 2, 500); d.cell(23, 3, 0.12); d.cell(23, 4, 100)
    l = wb.create_sheet("Lançamentos")
    for c, v in enumerate([datetime(2026, 11, 2), "=A5", "Mercado", "Alimentação", "Essencial", "Variável", "(sem envelope)", 120.5, None], start=1): l.cell(5, c, v)
    for c, v in enumerate([datetime(2026, 11, 5), None, "Fatura", "Outros", "Não Essencial", "Fatura", "Avulsos", 80, None], start=1): l.cell(6, c, v)
    e = wb.create_sheet("Envelopes"); e["A7"], e["B7"] = "Comida", 0.4; e["A8"], e["B8"] = "Avulsos", 0.1
    j = wb.create_sheet("Projeção"); j.cell(6, 3, 300)                       # ajuste de receita no 2º mês
    r = wb.create_sheet("RESERVA"); r["A32"], r["B32"], r["C32"], r["D32"] = datetime(2026, 11, 5), "Depósito", 150, "ok"
    caminho = tmp_path / "p.xlsx"; wb.save(caminho)
    return caminho


def test_importa_entradas_e_ignora_formulas(planilha):
    d, rel = importar_planilha(planilha)
    assert d.renda_base == 3100 and len(d.rendas) == 3
    assert d.cfg.primeiro_mes.isoformat() == "2026-11-01" and d.cfg.reserva_aporte == 150 and d.cfg.inicio_redirecionamento.isoformat() == "2027-02-01"
    assert d.cfg.variaveis_projetados is None                  # fórmula -> automático
    assert d.cfg.manter_parcelados_sem_total is False
    assert d.fixas[0].item == "Aluguel" and d.fixas[0].valor == 1000
    p = d.parcelados[0]
    assert (p.item, p.valor, p.n_atual, p.total, p.taxa_juros) == ("TV", 250, 3, 10, 0.035)
    assert [l.bloco for l in d.lancamentos] == ["Variável", "Fatura"]
    assert d.lancamentos[0].envelope == "" and d.lancamentos[0].valor == 120.5      # "(sem envelope)" vira vazio
    assert [e.nome for e in d.envelopes] == ["Comida", "Avulsos"]
    assert d.ajustes_receita[0].mes.isoformat() == "2026-12-01" and d.ajustes_receita[0].valor == 300
    assert d.outras_dividas[0].descricao == "Rotativo" and d.mov_reserva[0].valor == 150
    assert rel.contagens["lançamentos"] == 2 and "Aba 'Gastos futuro' não encontrada" not in " ".join(rel.avisos)


def test_aba_ausente_vira_aviso(tmp_path):
    wb = openpyxl.Workbook(); wb.active.title = "Premissas"
    wb.save(tmp_path / "vazia.xlsx")
    d, rel = importar_planilha(tmp_path / "vazia.xlsx")
    assert any("Fixas" in a for a in rel.avisos) and d.fixas == []
