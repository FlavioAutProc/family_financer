# Mapa: planilha → sistema

| Aba da planilha | Tela do sistema | Observação |
|---|---|---|
| INÍCIO | Início | Seletor de mês vira a barra lateral |
| Lançamentos | Lançamentos | Formulário + tabela do mês; `Envelope` “(sem envelope)” vira vazio |
| Folha de anotações | Folha de anotações | PDF A4 de 4 páginas gerado com ReportLab |
| CONTROLE | Controle | Mesmas 8 verificações |
| CORTES | Cortes | Percentuais editáveis |
| Gastos futuro | Gastos futuros | 3 cenários + gráfico |
| Dívidas | Dívidas | Taxa editável por parcelado (guardada no próprio parcelado) |
| Extras e provisões | Extras e provisões | Regra de destino + cofrinho |
| RESERVA | Reserva | Movimentos em tabela |
| INVESTIMENTOS | Investimentos | Carteira + simulador |
| Histórico | Histórico e poupança | Com gráficos |
| Dashboard / Resumo / Envelopes | Início / Controle | Gráficos e tabelas distribuídos |
| Fixas / Parcelados / Projeção (linha 6) / Premissas | Cadastros / Configurações | Rendas viram uma lista livre |
| Listas | (constantes em `config.py`) | |

**O que o importador lê:** só células de entrada (constantes). Fórmulas são ignoradas porque o sistema recalcula.
Um campo em branco onde a planilha tinha fórmula (ex.: “variáveis projetados”) fica como **automático**.
