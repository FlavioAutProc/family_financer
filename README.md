# 💰 Orçamento Familiar Pro

Sistema de controle financeiro familiar em **Python**, construído a partir de uma planilha de orçamento real
(`Orcamento_Familiar_05.xlsx`). Ele repete **exatamente** a mesma lógica de cálculo da planilha — conferida mês a mês
contra os valores calculados pelo Excel — e acrescenta banco de dados, telas amigáveis, importação da planilha,
relatórios e testes automatizados.

> **Foco:** controle rigoroso do mês, poupar, fazer o dinheiro render e pensar no futuro.
> Tudo roda **no seu computador**: os dados ficam em um arquivo local (`dados/orcamento.db`) e não vão para a internet.

## O que o sistema faz

| Grupo | Tela | Para que serve |
|---|---|---|
| **Dia a dia** | Início | Situação do mês em um olhar: faixa verde/amarela/vermelha, 6 cartões e gráficos |
| | Lançamentos | Anotar gastos (formulário rápido) e editar os do mês em uma tabela |
| | Folha de anotações | PDF **A4 de 4 páginas** para conferir no papel (resumo, semanas, envelopes, fixas, parcelas, lançamentos, linhas em branco) |
| **Acompanhar** | Controle | Semáforo com 8 verificações, 5 maiores gastos e envelopes (limite × gasto) |
| | Cortes | Quanto falta cortar e onde (não essenciais, fixas a renegociar, parcelas que terminam) |
| | Gastos futuros | Despesas **possíveis**: projeção de 12 meses em 3 cenários (confirmado, esperado, pior caso) |
| | Histórico e poupança | Planejado × realizado e taxa de poupança, com meta |
| **Planejar** | Dívidas | Taxa de juros por parcelamento, valor de quitação, economia de juros e **prioridade de quitação** |
| | Extras e provisões | 13º/férias/renda extra com regra de destino; cofrinho das contas anuais (IPVA, escola, Natal) |
| | Reserva | Saldo real × plano, metas por etapa (1, 3 e 6 meses), depósitos e retiradas |
| | Investimentos | Carteira, regra "posso investir?" e simulador de aportes |
| **Configurar** | Cadastros / Configurações / Dados | Rendas, fixas, parcelados, envelopes, premissas, importar planilha, backup, exportar Excel |

## Como usar

### Windows
1. Instale o Python (https://www.python.org/downloads/ — marque **Add Python to PATH**).
2. Dê dois cliques em **`Iniciar.bat`**. Na primeira vez ele prepara tudo sozinho; depois abre o sistema no navegador.

### Linux / macOS
```bash
./iniciar.sh
```

### Primeiro acesso
Abra **Dados → Importar planilha** e envie o `Orcamento_Familiar_05.xlsx`. O sistema lê só o que você digitou
(células de fórmula são recalculadas por ele). Para só conhecer, use **Dados → Exemplo / limpar → Carregar exemplo**.

## Estrutura do projeto

```
orcamento_familiar_pro/
├── app.py                      # entrada (streamlit run app.py): navegação e seletor de mês
├── orcamento/
│   ├── modelos.py              # entidades (dataclasses) e configurações
│   ├── banco.py                # persistência SQLite + backup JSON
│   ├── motor.py                # projeção de 36 meses (cálculo puro)
│   ├── analises/               # controle, cortes, reserva, futuros, dívidas, extras, histórico, investimentos
│   ├── importador.py           # lê a planilha Excel
│   ├── exportador.py           # relatório Excel
│   ├── relatorios.py           # folha de anotações em PDF (A4)
│   ├── demo.py                 # dados de exemplo
│   └── ui/                     # telas Streamlit (uma função render() por tela)
├── tests/                      # 62 testes (motor, análises, banco, importador, PDF/Excel, telas)
├── docs/                       # manual do usuário, arquitetura, regras de cálculo, mapa planilha→sistema
└── dados/                      # banco de dados local (não vai para o Git)
```

## Por dentro (resumo)

- **Camadas separadas:** a interface só chama `motor` e `analises`, que são funções puras sobre `Dados` — por isso
  são fáceis de testar e não dependem do Streamlit.
- **Banco gerado pelos modelos:** o esquema SQLite é derivado das dataclasses; acrescentar um campo é editar a classe.
- **Fidelidade à planilha:** `tests/test_paridade_planilha.py` compara os 36 meses × 10 indicadores com o Excel.
- Detalhes em [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md) e [`docs/REGRAS_DE_CALCULO.md`](docs/REGRAS_DE_CALCULO.md).

## Testes

```bash
pip install -r requirements-dev.txt
pytest -q                                         # 62 testes
PLANILHA_REAL=/caminho/Orcamento_Familiar_05.xlsx pytest tests/test_paridade_planilha.py   # compara com o Excel
```

## Privacidade e cópias de segurança

Nada sai do computador. Use **Dados → Backup** para baixar um JSON com tudo e restaurar quando quiser. Antes de cada
importação o sistema guarda uma cópia do banco anterior na pasta `dados/`.

## Avisos importantes

- Cálculos de juros e simulações são **estimativas** (valor presente das parcelas, rendimento informado por você).
  O valor real de quitação vem da loja ou do banco.
- Informações de investimento são gerais e não substituem orientação individual.

## Próximos passos (ideias)

Metas de futuro com valor e prazo, patrimônio líquido mês a mês, alertas por e-mail/WhatsApp, vários usuários.
