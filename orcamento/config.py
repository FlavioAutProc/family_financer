"""Constantes e listas de opções usadas em todo o sistema."""
from __future__ import annotations

import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CAMINHO_BANCO = Path(os.environ.get("ORCAMENTO_DB", RAIZ / "dados" / "orcamento.db"))

HORIZONTE_MESES = 36

# Semáforo
OK = "OK"
ATENCAO = "ATENÇÃO"
PERIGO = "PERIGO"
ESTOUROU = "ESTOUROU"
DEFINIR_ENVELOPE = "DEFINIR ENVELOPE"

CLASSIFICACOES = ["Essencial", "Não Essencial"]
BLOCOS = ["Variável", "Fatura"]
CATEGORIAS_PADRAO = [
    "Alimentação", "Dependentes", "Saúde", "Lazer", "Telefonia", "Transporte", "Educação",
    "Moradia", "Imóvel", "E-comerce", "Financiamento", "Fixa", "Outros",
]
SEM_ENVELOPE = "(sem envelope)"
ENVELOPES_PADRAO = [
    ("Alimentação e lanches", 0.40), ("Avulsos", 0.10), ("Pontuais", 0.15),
    ("Saúde e escola", 0.15), ("Contas de consumo e transporte", 0.20),
]

TIPOS_INVESTIMENTO = [
    "Poupança", "Tesouro Selic", "CDB/RDB liquidez diária", "CDB prazo fixo",
    "Tesouro IPCA+ / Prefixado", "LCI/LCA", "Fundo de investimento", "Ações / FIIs / ETFs",
    "Previdência", "Outro",
]
OBJETIVOS = ["Reserva de emergência", "Meta de médio prazo", "Longo prazo / aposentadoria", "Outro"]
LIQUIDEZ = ["Diária", "Até 30 dias", "No vencimento", "Baixa"]

CHANCES = ["Baixa", "Média", "Alta"]
SITUACOES_FUTURO = ["Possível", "Confirmada", "Já lançado", "Descartada"]
TIPOS_EXTRA = ["13º salário", "Férias", "Restituição IR", "Renda extra", "Outro"]
SITUACOES_EXTRA = ["Prevista", "Recebida", "Descartada"]
SITUACOES_PROVISAO = ["Ativa", "Pausada"]
TIPOS_MOVIMENTO = ["Depósito", "Retirada"]

DICAS_CATEGORIA = {
    "Dependentes": "Combine um valor mensal fixo para esse tipo de gasto e avise a todos.",
    "Lazer": "Defina um valor por semana e pague em dinheiro ou débito, não no cartão.",
    "Telefonia": "Compare recarga avulsa com plano mensal e veja qual sai mais barato.",
    "Alimentação": "Faça lista antes de ir ao mercado e compare preços; evite compras de última hora.",
    "Saúde": "Pergunte por genérico ou farmácia popular antes de comprar.",
    "E-comerce": "Espere 7 dias antes de comprar e evite parcelar.",
    "Transporte": "Veja se dá para juntar corridas ou usar uma alternativa mais barata.",
    "Educação": "Verifique descontos por pagamento em dia ou bolsas.",
    "Moradia": "Veja se há contas (luz, água, gás) com consumo para reduzir.",
}
DICA_PADRAO = "Pergunte: dá para adiar ou reduzir este gasto neste mês?"
DICA_FATURA = "Parece fatura de cartão: não se corta, se negocia e quita. Evite novas compras no cartão."
DICA_FIXA = "Pedir desconto, comparar fornecedores ou trocar de plano."
