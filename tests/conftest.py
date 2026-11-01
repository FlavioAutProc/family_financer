import os
import sys
import tempfile
from datetime import date
from pathlib import Path

import pytest

# Banco temporário para qualquer código que use o caminho padrão
os.environ.setdefault("ORCAMENTO_DB", str(Path(tempfile.mkdtemp()) / "teste.db"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orcamento.banco import Banco  # noqa: E402
from orcamento.demo import dados_demo  # noqa: E402
from orcamento.modelos import (Configuracoes, Dados, Fixa, Lancamento, Parcelado, Renda)  # noqa: E402

M0 = date(2026, 11, 1)


@pytest.fixture
def banco(tmp_path):
    return Banco(tmp_path / "t.db")


@pytest.fixture
def demo():
    return dados_demo(M0)


@pytest.fixture
def simples():
    """Cenário pequeno, com contas fáceis de conferir à mão.

    Renda 3.000 · fixa 1.000 · parcela 500 (1/2: nov e dez) · reserva 200/mês ·
    parcelas que terminam vão para a reserva a partir de jan/2027 · variáveis de nov: 800.
    """
    d = Dados(cfg=Configuracoes(primeiro_mes=M0, reserva_aporte=200.0, inicio_redirecionamento=date(2027, 1, 1), meta_reserva=1000.0))
    d.rendas = [Renda("Salário", 3000.0)]
    d.fixas = [Fixa("Aluguel", "Moradia", "Essencial", 1000.0)]
    d.parcelados = [Parcelado("TV", "", "", 500.0, 1, M0, 2)]
    d.lancamentos = [Lancamento(date(2026, 11, 3), "Mercado", "Alimentação", "Essencial", "Variável", "", 500.0),
                     Lancamento(date(2026, 11, 9), "Cinema", "Lazer", "Não Essencial", "Variável", "", 300.0)]
    return d
