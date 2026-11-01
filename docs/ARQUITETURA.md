# Arquitetura

## Visão geral

```
        ┌─────────────────────────── ui/ (Streamlit) ───────────────────────────┐
        │ p_inicio · p_lancamentos · p_controle · p_cortes · p_futuros · ...     │
        └───────────────┬───────────────────────────────┬───────────────────────┘
                        │ lê/grava                       │ calcula
                 ┌──────▼──────┐                 ┌───────▼────────┐
                 │  banco.py   │                 │ analises/ + motor.py │   (funções puras)
                 │  SQLite     │◄── Dados ──────►│  projeção 36 meses   │
                 └──────┬──────┘                 └───────────────────────┘
                        │
        importador.py (xlsx → Dados) · exportador.py (Dados → xlsx/json) · relatorios.py (PDF A4)
```

**Regra de ouro:** `motor` e `analises` **não importam** Streamlit nem SQLite. Recebem um objeto `Dados` e devolvem
dataclasses. Por isso são testados sem interface e poderiam alimentar uma API ou um aplicativo móvel.

## Módulos

| Módulo | Responsabilidade |
|---|---|
| `modelos.py` | Entidades (`Fixa`, `Parcelado`, `Lancamento`…), `Configuracoes` e o agregado `Dados`. Funções de data (`somar_meses`). |
| `banco.py` | Esquema SQLite **derivado das dataclasses** (via `get_type_hints`), CRUD genérico, `sincronizar` (upsert/delete por escopo), config chave/valor em JSON, backup. |
| `motor.py` | `projetar(dados)` → 36 `MesProj`; parcelados (ativo/rótulo/restantes); `envelopes_do_mes`. |
| `analises/` | Um módulo por assunto: `controle`, `cortes`, `reserva`, `futuros`, `dividas`, `extras`, `historico`, `investimentos`. |
| `importador.py` | Lê as **células de entrada** da planilha (ignora fórmulas) e devolve `Dados` + relatório. |
| `exportador.py` / `relatorios.py` | Excel de relatório, JSON de backup, PDF A4 de 4 páginas (ReportLab). |
| `ui/` | `contexto.py` (sessão), `componentes.py` (cartões, semáforo, **editor genérico**), uma tela por arquivo `p_*.py`. |

## Modelo de dados

Tabelas (todas com `id INTEGER PK`): `rendas`, `fixas`, `parcelados`, `lancamentos`, `envelopes`, `ajustes_receita`,
`gastos_futuros`, `outras_dividas`, `extras`, `provisoes`, `mov_reserva`, `investimentos`, mais `config(chave, valor)`.

- Datas em texto ISO; “mês” sempre guarda o **dia 1**.
- Migração simples: ao abrir o banco, colunas novas das dataclasses são adicionadas com `ALTER TABLE`.
- `Parcelado` guarda `n_atual` + `mes_ref` (“a parcela 4 é a de nov/26”) e `total`; primeira e última parcela são **derivadas**.

## Decisões de projeto

1. **Streamlit** para a interface: baixo atrito para uma família sem perfil técnico (abre no navegador, sem instalar app).
   O custo é rerodar o script a cada interação; com dados pequenos isso é imperceptível.
2. **SQLite local** em vez de servidor: zero configuração, um arquivo fácil de copiar.
3. **Funções puras** para o cálculo: previsibilidade e testes rápidos (62 testes em ~14 s).
4. **Editor genérico** (`editor_tabela`): converte registros ↔ `DataFrame` ↔ registros, **preservando campos que não estão na
   tabela** (ex.: a taxa de juros dos parcelados não é apagada ao salvar a aba Parcelados).
5. **Paridade com a planilha** como critério de aceite: `test_paridade_planilha.py`.
6. **Extras fora do orçamento mensal:** dinheiro extra não infla o teto de gastos, só alimenta metas.

## Acesso pela rede (opcional)

```bash
streamlit run app.py --server.address 0.0.0.0
```
Depois, em outro aparelho da mesma rede: `http://IP-DO-COMPUTADOR:8501`. **Não exponha à internet**: não há login.

## Como estender

- **Novo campo:** acrescente-o à dataclass; a coluna é criada sozinha. Inclua-o em `colunas` do editor da tela.
- **Nova tela:** crie `ui/p_nova.py` com `render()` e registre em `app.py`.
- **Nova análise:** função pura em `analises/` + teste em `tests/test_analises.py`.
