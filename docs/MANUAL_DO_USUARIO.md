# Manual do Usuário — Orçamento Familiar Pro

*Escrito de forma simples, para qualquer pessoa da família usar.*

## 1. A ideia em 30 segundos

Pense no dinheiro do mês como **uma mesada grande**. O sistema faz três perguntas por você:

1. **Quanto entra?** (salários e outras rendas)
2. **O que já tem dono?** (aluguel, escola, parcelas… tudo que você *precisa* pagar)
3. **Quanto sobra para gastar no dia a dia?** Esse é o **teto**. Passou do teto, o sistema avisa.

E ainda guarda uma parte para o futuro: a **reserva de emergência** e as **provisões** (contas que só aparecem uma vez por ano).

## 2. Abrindo o sistema

- **Windows:** dois cliques em `Iniciar.bat`. Uma janela preta abre (deixe aberta) e o sistema aparece no navegador.
- **Para fechar:** feche a janela preta.

No menu da esquerda você escolhe a tela. Em cima do menu fica o **mês**: tudo que você vê é daquele mês.

## 3. O que fazer no dia a dia (2 minutos)

1. Abra **Lançamentos**.
2. Em **➕ Anotar um gasto**, escreva *o que foi*, escolha a *categoria*, o *envelope* e o *valor*. Clique **Anotar**.
3. Pronto! Volte ao **Início**: a faixa muda de cor se algo estiver errado.

> **Fatura de cartão?** Escolha *Bloco = Fatura*. **Compra do dia a dia?** *Bloco = Variável*.

## 4. As cores

| Cor | Significa | O que fazer |
|---|---|---|
| 🟢 Verde / OK | Tudo certo | Nada |
| 🟡 Amarelo / ATENÇÃO | Cuidado, está chegando perto | Reduzir gastos que não são essenciais |
| 🔴 Vermelho / PERIGO | Passou do limite | Abrir **Cortes** e agir |

## 5. Todo semana

- Abra **Controle**. Se tudo estiver verde, ótimo. Se algo ficar vermelho, abra **Cortes**: o sistema mostra **onde dá para economizar** e quanto falta.
- Quer conferir no papel? **Folha de anotações → Gerar PDF → imprimir em A4**.

## 6. Todo mês

- **Reserva:** anote o depósito do mês.
- **Investimentos:** atualize o “Valor atual” de cada aplicação.
- **Cadastros → Parcelados:** confira se as parcelas estão certas.
- **Histórico e poupança:** veja se você cumpriu o plano.

## 7. Para pensar no futuro

### Gastos futuros 🔮
Pode acontecer algo (conserto, dentista) mas **não é certo**? Anote em **Gastos futuros** com o valor, o mês e a **chance** (baixa, média, alta). Isso **não muda suas contas de verdade**. O sistema só mostra 3 cenários:
- **Confirmado:** só o que já é certo;
- **Esperado:** cada gasto × sua chance;
- **Pior caso:** tudo acontece.

### Dívidas 💳
Digite a **taxa de juros ao mês** de cada parcelamento (está no contrato ou no aplicativo da loja). O sistema mostra quanto de juros ainda falta pagar e **qual dívida quitar primeiro** (a de juros mais alto). Sem taxa, ele não consegue calcular.

### Extras e provisões 🎁
- **Extras** (13º, férias, restituição): digite o valor e o mês. O sistema divide pela sua regra (ex.: 50% reserva, 30% dívidas, 20% livre). **Esse dinheiro não aumenta o teto do mês**: ele vai para as metas.
- **Provisões** (IPVA, material escolar, Natal): digite o valor e o mês do próximo vencimento. O sistema calcula quanto guardar por mês e mostra se o “cofrinho” vai faltar.

### Reserva 🛟
Metas em degraus: **1º colchão → 1 mês → 3 meses → 6 meses** de contas essenciais. Guarde em conta separada, de fácil resgate e baixo risco.

### Investimentos 🌱
O sistema só diz **“LIBERADO”** quando a reserva atinge o mínimo e o mês fecha no azul. Antes disso, o dinheiro vai para a reserva. O **simulador** mostra uma estimativa — **não é promessa**.

## 8. Importar a planilha antiga

**Dados → Importar planilha →** escolha o arquivo `.xlsx` → confira o resumo → marque “Entendi” → **Importar agora**.
O sistema guarda uma cópia dos dados anteriores na pasta `dados/`.

## 9. Cópia de segurança

**Dados → Backup → Baixar backup (JSON).** Guarde o arquivo no e-mail ou na nuvem. Para voltar atrás: **Restaurar backup**.

## 10. Perguntas rápidas

**Apaguei sem querer.** Selecione a linha e Delete só vale depois de clicar em **Salvar**. Se já salvou, restaure o backup.
**Troquei o mês e sumiu tudo.** Nada sumiu: cada mês mostra só os seus lançamentos. Volte pelo seletor.
**Dá para usar no celular?** Sim, se o computador estiver ligado na mesma rede (veja `docs/ARQUITETURA.md`, seção “Acesso pela rede”).
