# Roteiro de narração — vídeo de 2 minutos

> Apresentação do dashboard **Incidentes de TI — Observabilidade preditiva**
> (Desafio AIOps Locaweb/FIAP). ~330 palavras, ritmo de fala normal.
> Cada bloco abre com a pergunta que a tela responde — a mesma que aparece na
> faixa no topo de cada aba — e fecha com o número que a responde.
> Números conferidos contra a API em 2026-09-21 (origem `2025-12-31`).

---

## 0:00 – 0:12 · Abertura
**Tela:** Painel (aba inicial), visão geral da página

> "Este é o dashboard de observabilidade preditiva de incidentes de TI do
> desafio Locaweb. Cada tela deixa explícito que pergunta responde e de onde
> vem cada número: modelo, regra ou histórico."

---

## 0:12 – 0:35 · Painel
**Tela:** Painel · destacar os 4 KPIs, depois o gráfico de previsão e a pressão por equipe

> "Quanto trabalho vem por aí, e a operação está sob risco? O Prophet prevê
> **125 incidentes para D+1** e média de **84 por dia na semana seguinte**.
> O risco de OLA está em **1,76%**, faixa média. E a previsão desce até o
> time: **Team02, 29% acima da própria média histórica**."

---

## 0:35 – 0:52 · Detalhe
**Tela:** Detalhe · banner P2+P3, depois top categorias e produtos

> "Onde esse volume vai bater? O foco padrão são **P2 e P3, que concentram
> 79% do volume real**. Daí o total previsto é distribuído por categoria e
> produto pela proporção histórica — rotulado como regra, não como modelo.
> Essa distinção o painel nunca esconde."

---

## 0:52 – 1:08 · KPI
**Tela:** KPI · os 4 cards e a matriz de faixas de meta

> "Vamos fechar o ano dentro da meta de OLA? No ano fechado, **238 OLAs
> quebrados** entre P2 e P3. A matriz mostra em que faixa estamos, e o status
> geral é **crítico**, puxado pelo volume tratado de P2. A projeção é
> aritmética, não estatística — e o selo diz isso."

---

## 1:08 – 1:28 · Fatores
**Tela:** Fatores · importância global, depois o SHAP com a legenda de cor

> "Por que um incidente é classificado como arriscado? No geral, o que mais
> pesa é a **prioridade do chamado, com 32%**. E dá para descer ao caso
> individual: aqui, **categoria e triagem empurram o risco para cima em
> 1,13** — a barra vermelha — enquanto a prioridade puxa para baixo, em
> verde. É o XGBoost explicado com SHAP."

---

## 1:28 – 1:45 · Clusters
**Tela:** Clusters · os 4 cards de perfil, depois o bubble chart

> "Que perfis existem e qual trava mais a operação? O K-Means separou os 41
> mil incidentes em quatro perfis. O **perfil B é o gargalo: 198 horas de
> duração média com 33% do volume**. O **perfil D tem a pior taxa de tempo
> excedido, 98%**, mas só 10% do volume — duas leituras de prioridade."

---

## 1:45 – 2:00 · Alertas e fecho
**Tela:** Alertas · lista de alertas, depois recomendações

> "O que fazer agora? **Cinco alertas ativos**, cada um com a regra que o
> disparou visível, e as recomendações — como reforçar o Team02 em D+1. Nada
> aqui é gerado por IA: são regras sobre a saída dos modelos. Previsão, risco
> e perfil viram decisão, com a origem de cada número na tela."

---

## Notas para a gravação

- **Ordem das abas** = ordem do roteiro: Painel → Detalhe → KPI → Fatores → Clusters → Alertas.
- Em Fatores, dar um beat na legenda vermelho/verde antes de falar do SHAP — é o ponto onde o espectador precisa da chave de leitura.
- Em Clusters, o contraste B × D é o gancho mais forte da tela; não correr.
- Os selos `MODELO`, `REGRA`, `HISTÓRICO` e `CALCULADO` são o fio condutor de governança — vale apontá-los ao menos duas vezes ao longo do vídeo.
- Se a origem dos dados mudar, reconferir os números com `curl` nos endpoints `/api/painel`, `/api/kpi`, `/api/fatores` e `/api/alertas` antes de gravar.
