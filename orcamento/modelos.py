"""Entidades do domínio.

Todas as entidades são dataclasses simples. O banco de dados (``banco.py``) deriva o
esquema das tabelas a partir dos campos e dos tipos declarados aqui, então adicionar um
campo novo é só acrescentá-lo à classe correspondente.

Convenção: campos de "mês" guardam sempre o **primeiro dia** do mês.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


def primeiro_dia(d: date) -> date:
    return d.replace(day=1)


def somar_meses(d: date, n: int) -> date:
    """Soma ``n`` meses ao primeiro dia do mês de ``d`` (equivale ao EDATE do Excel)."""
    ano, mes = divmod(d.year * 12 + d.month - 1 + n, 12)
    return date(ano, mes + 1, 1)


def diferenca_meses(a: date, b: date) -> int:
    """Quantos meses de ``a`` até ``b`` (positivo se b é posterior)."""
    return (b.year - a.year) * 12 + b.month - a.month


# ---------------------------------------------------------------------------
# Registros persistidos (uma tabela por classe)
# ---------------------------------------------------------------------------

@dataclass
class Renda:
    descricao: str = ""
    valor: float = 0.0
    id: Optional[int] = None


@dataclass
class Fixa:
    item: str = ""
    categoria: str = "Fixa"
    classificacao: str = "Essencial"
    valor: float = 0.0
    inicio: Optional[date] = None
    fim: Optional[date] = None
    obs: str = ""
    id: Optional[int] = None

    def valor_no_mes(self, mes: date) -> float:
        if not self.item or not self.valor:
            return 0.0
        if self.inicio and mes < primeiro_dia(self.inicio):
            return 0.0
        if self.fim and mes > primeiro_dia(self.fim):
            return 0.0
        return float(self.valor)


@dataclass
class Parcelado:
    item: str = ""
    categoria: str = ""
    envelope: str = ""
    valor: float = 0.0
    n_atual: Optional[int] = None      # parcela "n" informada...
    mes_ref: Optional[date] = None     # ...e o mês a que esse "n" se refere
    total: Optional[int] = None        # total de parcelas "m" (vazio = desconhecido)
    taxa_juros: Optional[float] = None  # taxa ao mês (0.035 = 3,5%)
    obs: str = ""
    id: Optional[int] = None

    @property
    def primeira_parcela(self) -> Optional[date]:
        if not self.n_atual or not self.mes_ref:
            return None
        return somar_meses(primeiro_dia(self.mes_ref), -(int(self.n_atual) - 1))

    @property
    def ultima_parcela(self) -> Optional[date]:
        ini = self.primeira_parcela
        if ini is None or not self.total:
            return None
        return somar_meses(ini, int(self.total) - 1)


@dataclass
class Lancamento:
    data: Optional[date] = None
    descricao: str = ""
    categoria: str = ""
    classificacao: str = "Essencial"
    bloco: str = "Variável"      # "Variável" ou "Fatura"
    envelope: str = ""
    valor: float = 0.0
    obs: str = ""
    id: Optional[int] = None

    @property
    def mes(self) -> Optional[date]:
        return primeiro_dia(self.data) if self.data else None


@dataclass
class Envelope:
    nome: str = ""
    pct: float = 0.0
    ordem: int = 0
    id: Optional[int] = None


@dataclass
class AjusteReceita:
    mes: Optional[date] = None
    valor: float = 0.0
    obs: str = ""
    id: Optional[int] = None


@dataclass
class GastoFuturo:
    descricao: str = ""
    categoria: str = ""
    mes: Optional[date] = None
    valor: float = 0.0
    chance: str = "Média"
    situacao: str = "Possível"
    obs: str = ""
    id: Optional[int] = None


@dataclass
class OutraDivida:
    descricao: str = ""
    saldo: float = 0.0
    taxa: Optional[float] = None
    pagamento: Optional[float] = None
    id: Optional[int] = None


@dataclass
class Extra:
    descricao: str = ""
    tipo: str = "Renda extra"
    mes: Optional[date] = None
    valor: float = 0.0
    situacao: str = "Prevista"
    obs: str = ""
    id: Optional[int] = None


@dataclass
class Provisao:
    descricao: str = ""
    mes: Optional[date] = None        # mês do PRÓXIMO vencimento (repete todo ano)
    valor: float = 0.0
    situacao: str = "Ativa"
    obs: str = ""
    id: Optional[int] = None


@dataclass
class MovReserva:
    data: Optional[date] = None
    tipo: str = "Depósito"
    valor: float = 0.0
    obs: str = ""
    id: Optional[int] = None


@dataclass
class Investimento:
    produto: str = ""
    tipo: str = ""
    instituicao: str = ""
    objetivo: str = ""
    liquidez: str = ""
    aplicado: float = 0.0
    atual: float = 0.0
    id: Optional[int] = None


TABELAS: dict[str, type] = {
    "rendas": Renda, "fixas": Fixa, "parcelados": Parcelado, "lancamentos": Lancamento,
    "envelopes": Envelope, "ajustes_receita": AjusteReceita, "gastos_futuros": GastoFuturo,
    "outras_dividas": OutraDivida, "extras": Extra, "provisoes": Provisao,
    "mov_reserva": MovReserva, "investimentos": Investimento,
}


# ---------------------------------------------------------------------------
# Configurações (chave/valor)
# ---------------------------------------------------------------------------

@dataclass
class Configuracoes:
    # Linha do tempo e reserva
    primeiro_mes: date = field(default_factory=lambda: primeiro_dia(date.today()))
    reserva_aporte: float = 0.0
    redirecionar_parcelas: bool = True
    inicio_redirecionamento: Optional[date] = None
    meta_reserva: float = 1000.0
    saldo_inicial_reserva: float = 0.0
    # Projeções (vazio = calcula a partir dos lançamentos do 1º mês)
    variaveis_projetados: Optional[float] = None
    faturas_projetadas: Optional[float] = None
    incluir_faturas: bool = True
    manter_parcelados_sem_total: bool = True
    parcelas_referencia: Optional[float] = None
    teto_comprometimento: Optional[float] = None
    # Reserva de emergência
    incluir_parcelas_custo_essencial: bool = True
    custo_essencial_manual: Optional[float] = None
    # Extras: destino (soma = 100%)
    destino_reserva: float = 0.5
    destino_dividas: float = 0.3
    destino_investir: float = 0.0
    destino_livre: float = 0.2
    # Provisões
    provisao_guardado_inicial: float = 0.0
    provisao_por_mes_manual: Optional[float] = None
    # Gastos futuros: peso de cada nível de chance
    chance_baixa: float = 0.25
    chance_media: float = 0.50
    chance_alta: float = 0.75
    # Cortes
    corte_nao_essencial: float = 0.40
    corte_fixas: float = 0.05
    # Poupança
    meta_poupanca: float = 0.10
    # Investimentos
    reserva_minima_investir: Optional[float] = None
    aporte_simulador: Optional[float] = None
    rendimento_anual: float = 0.10

    def peso_chance(self, chance: str) -> float:
        return {"Baixa": self.chance_baixa, "Alta": self.chance_alta}.get(chance, self.chance_media)


@dataclass
class Dados:
    """Fotografia completa dos dados — é tudo que o motor e as análises precisam."""
    cfg: Configuracoes = field(default_factory=Configuracoes)
    rendas: list[Renda] = field(default_factory=list)
    fixas: list[Fixa] = field(default_factory=list)
    parcelados: list[Parcelado] = field(default_factory=list)
    lancamentos: list[Lancamento] = field(default_factory=list)
    envelopes: list[Envelope] = field(default_factory=list)
    ajustes_receita: list[AjusteReceita] = field(default_factory=list)
    gastos_futuros: list[GastoFuturo] = field(default_factory=list)
    outras_dividas: list[OutraDivida] = field(default_factory=list)
    extras: list[Extra] = field(default_factory=list)
    provisoes: list[Provisao] = field(default_factory=list)
    mov_reserva: list[MovReserva] = field(default_factory=list)
    investimentos: list[Investimento] = field(default_factory=list)

    @property
    def renda_base(self) -> float:
        return sum(r.valor or 0.0 for r in self.rendas)
