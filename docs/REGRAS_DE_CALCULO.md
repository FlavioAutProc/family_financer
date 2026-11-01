# Regras de cálculo

Todas as regras estão em `orcamento/motor.py` e `orcamento/analises/`. Mês = primeiro dia do mês.

## Projeção (36 meses)

```
receita      = soma das rendas + ajustes do mês
fixas        = Σ valor das fixas ativas no mês (início ≤ mês ≤ fim)
parcelas     = Σ valor dos parcelados ativos no mês
variáveis    = Σ lançamentos "Variável" do mês        (se houver lançamentos; senão, a projeção)
faturas      = Σ lançamentos "Fatura" do mês          (se houver; senão, a projeção)
total        = fixas + parcelas + variáveis (+ faturas, se "contar faturas")
saldo        = receita − total
aporte extra = máx(0, parcelas de referência − parcelas do mês)   [a partir do início do redirecionamento]
teto         = receita − fixas − parcelas − faturas − depósito da reserva − aporte extra − provisão mensal
reserva(t)   = reserva(t−1) + depósito + aporte extra
comprometimento = (parcelas + faturas) ÷ receita      → deve ser ≤ o do 1º mês (só pode cair)
```

- **Variáveis/faturas projetados:** se não informados, usam os lançamentos do **1º mês**.
- **Parcelas de referência:** parcelas do mês anterior ao início do redirecionamento.
- **Parcelado ativo:** `primeira = mês_ref − (n − 1) meses`; `última = primeira + (m − 1)`. Sem total (`m`), segue a opção
  “manter parcelados sem total”.

## Envelopes
`limite = % do envelope × teto` · `uso = gasto ÷ limite` · **ESTOUROU** (> 100%), **ATENÇÃO** (≥ 80%), **OK**.
“(sem envelope)” = variáveis lançados − soma dos envelopes → **DEFINIR ENVELOPE** se > 0.

## Controle (8 verificações)
1. Saldo × (reserva + provisão): PERIGO se saldo < 0; ATENÇÃO se saldo < meta; senão OK.
2. Variáveis × teto: PERIGO > 100% · ATENÇÃO ≥ 80%.
3. Ritmo: `gasto ÷ dias decorridos × dias do mês` (mês corrente ou passado): PERIGO > teto · ATENÇÃO ≥ 90% do teto.
4. Comprometimento acima do teto de comprometimento → PERIGO.
5. Envelopes estourados · 6. Gastos sem envelope · 7. Reserva × próxima meta · 8. Parcelados sem total.

## Reserva
`custo essencial = fixas essenciais (1º mês) + variáveis essenciais lançados (1º mês) + parcelas (opcional)`.
Etapas: meta 1 (configurável), 1×, 3× e 6× o custo essencial. Previsão = primeiro mês em que a reserva do plano atinge a meta.

## Gastos futuros
`peso = 0` (descartada/já lançado), `1` (confirmada) ou o da chance (baixa/média/alta, configurável).
`esperado = Σ valor × peso` · `pior caso = Σ valor`. Mês **OK** se o saldo no pior caso ≥ 0; **ATENÇÃO** se só o esperado fecha;
**PERIGO** caso contrário.

## Dívidas
`valor presente = P × (1 − (1 + i)^−n) ÷ i` (n parcelas restantes, i = taxa ao mês; se i = 0, P × n).
`juros restantes = P × n − valor presente`. Prioridade: maior taxa primeiro. Outras dívidas: `meses = −ln(1 − S·i ÷ pgto) ÷ ln(1 + i)`;
se `pgto ≤ S·i`, “nunca quita”.

## Extras e provisões
Extras: valor × (% reserva | dívidas | investir | livre). Provisão mensal = Σ valores ativos ÷ 12 (ou valor manual).
Cofrinho(t) = cofrinho(t−1) + provisão − vencimentos(t); a conta **se repete todo ano** a partir do 1º vencimento.
“Para nunca faltar” = máx sobre k de `(vencimentos acumulados − já guardado) ÷ k`.

## Histórico
`desvio = variáveis − teto` · resultado OK (≤ 0), ATENÇÃO (≤ 10% acima), PERIGO (> 10%).
`poupado = depósitos − retiradas da reserva no mês` · `taxa = poupado ÷ receita`.

## Investimentos
Liberado se `reserva real ≥ mínimo` (padrão: 1 mês de contas essenciais) **e** saldo do mês ≥ 0.
Simulador: taxa mensal equivalente `(1 + a)^(1/12) − 1`; valor = `inicial × (1 + a)^(n/12) + aporte × ((1 + a)^(n/12) − 1) ÷ i`.
