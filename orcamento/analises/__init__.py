"""Análises financeiras (todas funções puras sobre ``Dados`` + projeção)."""
from .controle import Controle, analisar_controle
from .cortes import Cortes, analisar_cortes
from .dividas import ResultadoDividas, analisar_dividas, valor_presente
from .extras import ResultadoExtras, analisar_extras, partes_extra, soma_percentuais, vencimento_no_mes
from .futuros import projecao_futuros, resumo_futuros, peso as peso_futuro
from .historico import analisar_historico
from .investimentos import liberacao_para_investir, resumo_carteira, simular_aportes
from .reserva import custo_essencial, saldo_real, situacao_reserva

__all__ = [
    "Controle", "analisar_controle", "Cortes", "analisar_cortes", "ResultadoDividas", "analisar_dividas",
    "valor_presente", "ResultadoExtras", "analisar_extras", "partes_extra", "soma_percentuais",
    "vencimento_no_mes", "projecao_futuros", "resumo_futuros", "peso_futuro", "analisar_historico",
    "liberacao_para_investir", "resumo_carteira", "simular_aportes", "custo_essencial", "saldo_real", "situacao_reserva",
]
