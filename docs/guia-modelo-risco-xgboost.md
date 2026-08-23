# Guia educacional — Modelo de Risco XGBoost (OLA)

> Documento de apoio para ler e entender `notebooks/model_risk_xgboost_.ipynb`
> e a seção 13 ("Gráficos comentados") desse notebook — explica cada gráfico,
> cada métrica, o resultado real medido e o porquê por trás de cada escolha.
> Fecha com um glossário dos termos técnicos usados. Não substitui o
> notebook (fonte de verdade dos números) nem `docs/metricas-validacao.md`
> (números já consolidados) — é a camada de leitura para quem não trabalha
> com ML no dia a dia.

## 1. O que este modelo faz

O modelo é um **classificador binário** (XGBoost) que, para cada incidente,
estima a probabilidade de ele **exceder o tempo esperado de resolução da
sua prioridade** — coluna `target_excedeu_tempo` (duração real > threshold
de SLA da prioridade: P1=4h, P2=4h, P3=12h, P4=24h, P5=96h).

**Ponto que não pode virar mal-entendido**: esse alvo (`excedeu_tempo_esperado`)
**não é** o indicador oficial de violação de OLA (`kpi_status_int`), que é
ordens de grandeza mais raro (~0,6% dos incidentes, contra ~95% do alvo do
modelo). O modelo responde "este chamado vai levar mais tempo que o
esperado para a prioridade dele?", não "este chamado vai violar o contrato
oficial de SLA?". Essa distinção já gerou um ajuste de texto no dashboard
(tela Fatores) e é repetida aqui de propósito — é o erro mais fácil de
cometer ao explicar este modelo para alguém de fora do time técnico.

Saída do modelo por incidente (tabela `ml.fct_risco_incidente` /
`data/ml/xgboost/fct_ola_risk.parquet`): um **score calibrado** (0 a 1, lido
como probabilidade), uma **predição binária** (0/1, usando um threshold por
prioridade) e uma **explicação SHAP** (quais fatores empurraram o score
para cima ou para baixo naquele chamado específico).

## 2. Como o modelo foi validado (contexto necessário antes dos gráficos)

- **Partições**: treino (70%), validação (10%), teste (20%) — split
  temporal, não aleatório (dado que é uma série no tempo).
- **Calibração por prioridade**: cada prioridade tem uma taxa-base própria
  muito diferente (P2 ≈ 98%, P4 ≈ 89%) — uma única curva de calibração
  para todo mundo erraria nos dois estratos, então o modelo calibra um
  regressor isotônico **por prioridade**, com um calibrador global como
  fallback.
- **Threshold por prioridade, escolhido por custo**: em vez de um corte
  único de 0,5, o notebook testa qual threshold minimiza um custo
  `FP + k × FN` (um falso negativo vale `k` vezes um falso positivo) para
  `k ∈ {1,2,3,5,10}`, e adota `k=2` como política — errar pra menos (deixar
  passar uma violação real) custa duas vezes mais que alertar à toa.
- **Backtest temporal em 4 janelas**: em vez de validar só uma vez, o
  modelo é retreinado e testado em 4 janelas de tempo diferentes (seções
  50-70%, 60-80%, 70-90%, 80-100% da linha do tempo) para checar se o
  desempenho se mantém, ou se foi sorte de um único corte.

## 3. Os gráficos, um por um

Todos usam a **partição de teste** (3.330 incidentes, dados que o modelo
nunca viu durante o treino/calibração/escolha de threshold).

### Figura 1 — Discriminação e calibração

**Painel 1 — Curva ROC por estrato.** Mostra, para cada limiar de score
possível, a taxa de acerto (eixo Y) contra a taxa de alarme falso (eixo X).
Quanto mais a curva sobe rápido rumo ao canto superior esquerdo, melhor o
modelo separa as duas classes.

- **Resultado real**: agregado AUC=0,797, mas **P2 isolado AUC=0,658 e P4
  isolado AUC=0,670** — bem mais baixos.
- **Porquê isso importa**: é o **Paradoxo de Simpson** na prática — o
  agregado parece muito melhor porque prioridades diferentes têm taxas-base
  bem diferentes (P2≈98% vs. P4≈89%), e essa diferença ENTRE grupos infla a
  separação medida no conjunto todo. O número que diz se o modelo
  discrimina bem risco alto de risco baixo **dentro** de uma prioridade é o
  AUC do estrato, não o agregado.

**Painel 2 — Curva Precision-Recall por estrato, com linha de base.** Mostra
precisão (dos que o modelo marcou como risco, quantos realmente eram) contra
recall (dos que realmente eram risco, quantos o modelo pegou). A linha
pontilhada horizontal é a **linha de base** — o que um classificador trivial
("chuta risco pra todo mundo") já alcançaria de graça.

- **Resultado real**: P2 PR-AUC=0,989 com base_rate=0,983; P4
  PR-AUC=0,938 com base_rate=0,893 — a curva do modelo fica bem perto da
  própria linha de base nos dois estratos.
- **Porquê isso importa**: com **classe majoritária** (a maioria dos
  chamados excede o tempo esperado), PR-AUC sozinho engana — um número alto
  pode vir quase todo da base rate, não do modelo. A distância vertical
  entre a curva e a linha pontilhada é o que o modelo realmente agrega.

**Painel 3 — Diagrama de confiabilidade (calibração).** Cada ponto é uma
faixa de score previsto (eixo X) contra a frequência real observada naquela
faixa (eixo Y); o tamanho do ponto é o volume de chamados na faixa. Pontos
sobre a diagonal = calibração perfeita (quando o modelo diz "80% de
chance", 80% dos casos realmente acontecem).

- **Resultado real**: Brier=0,0457 (teste), pontos próximos da diagonal nas
  faixas de maior volume (n=2.405 na faixa 0,9-1,0).
- **Porquê isso importa**: a operação lê o score como probabilidade real
  ("62% de chance de estourar o prazo") — esse gráfico é a prova visual de
  que essa leitura faz sentido.

### Figura 2 — Estabilidade temporal e erro

**Painel 4 — AUC-ROC por janela de backtest.** Uma barra por partição:
validação, teste, e as 4 janelas de backtest temporal, com uma linha
horizontal na meta declarada do projeto (0,85).

- **Resultado real**: validação=0,846 → teste=0,797 → backtest (4 janelas:
  0,716 / 0,787 / 0,765 / 0,787, média 0,764±0,033) — **nenhuma partição
  atinge a meta**.
- **Porquê isso importa**: a queda de validação para teste já avisa que o
  número de validação era otimista; o backtest confirma que não foi um
  acaso do corte de teste — em janelas de tempo diferentes, mais recentes,
  o modelo segue abaixo da meta de forma consistente.

**Painel 5 — Matriz de confusão.** 4 células: quantos incidentes reais
"OK"/"risco" o modelo classificou corretamente ou errou, usando os
thresholds por prioridade adotados.

- **Resultado real**: TP=3.165, FP=164, FN=0, TN=1 — o modelo prevê
  "risco" para praticamente todo mundo (3.329 de 3.330).
- **Porquê isso importa**: não é um bug — é a consequência direta do
  threshold escolhido na política de custo (Painel 8), que ficou muito
  baixo (≈0,02) porque um falso negativo custa caro. É a decisão de
  negócio "prefiro alertar demais a deixar passar uma violação", visível no
  formato da matriz.

### Figura 3 — Explicabilidade

**Painel 6 — Importância por conceito de negócio.** Agrupa as 20 colunas
originais em 7 conceitos que a operação reconhece (ex.: várias colunas de
horário viram "Momento do dia") e soma a contribuição SHAP de cada grupo.

- **Resultado real**: Prioridade do chamado (32,1%) e Categoria e triagem
  (28,6%) dominam; Carga operacional do time (17,4%); os 4 restantes somam
  ~22%.
- **Porquê isso importa**: SHAP por coluna crua engana quando várias
  colunas codificam a mesma ideia (ex.: hora em seno/cosseno) — agrupar por
  conceito é a leitura que vai para quem não olha código.

**Painel 7 — Waterfall SHAP de um incidente.** Para o chamado de maior
score do lote de exemplo, mostra a contribuição (em log-odds) de cada
conceito — barras vermelhas empurram o score para cima, verdes para baixo.

- **Resultado real** (`INC8620225`, score=100%, mediana da própria
  prioridade=92%): "Categoria e triagem" (+1,05) e "Time responsável"
  (+0,78) empurram o risco para cima; "Prioridade do chamado" (-0,27) puxa
  para baixo.
- **Porquê isso importa**: é a explicação **por chamado**, não geral — o
  formato que vira a frase pronta de alerta operacional ("risco X%,
  sinais associados: categoria Y, time Z").

### Figura 4 — Decisão operacional

**Painel 8 — Curva de custo/threshold.** Como Precision, Recall e %
alertado mudam conforme o peso `k` atribuído a um falso negativo.

- **Resultado real**: as 5 políticas testadas (k=1,2,3,5,10) convergem
  **no mesmo threshold** ({P2: 0,02; P4: 0,02}) e nas mesmas métricas
  (Precision=0,9512, Recall=0,9984, 99,8% alertado).
- **Porquê isso importa**: não é erro de implementação — mostra que, nesse
  intervalo de `k`, a escolha do threshold é dominada pelo desbalanceamento
  de classe, não pelo peso do erro. Mudar o quanto um falso negativo "custa
  mais" não muda a política adotada.

**Painel 9 — Curva de ganho acumulado (lift).** Ordena os chamados de
teste por score (do maior para o menor) e mostra: revisando os X% de maior
score, que % das violações reais já foi capturado. A diagonal é o
"aleatório" (sem ordenar por score).

- **Resultado real**: a curva do modelo fica muito perto da diagonal
  aleatória na visão geral; o zoom nos primeiros 30% mostra uma vantagem
  real, porém pequena.
- **Porquê isso importa**: como a política adotada já alerta ~100% dos
  casos, sobra pouco espaço para a ordenação por score mostrar vantagem —
  esse gráfico é o mais honesto sobre "quanto vale a pena revisar por
  ordem de risco" com a política atual, e é um gráfico novo (não existia
  antes desta seção).

## 4. As métricas, uma por uma

| Métrica | O que mede | Validação | Teste | Leitura |
|---|---|---|---|---|
| **AUC-ROC** | Capacidade de separar as duas classes em qualquer threshold | 0,8458 | 0,7965 | Métrica principal declarada do projeto; meta 0,85 não atingida em nenhuma partição |
| **PR-AUC** | Área sob a curva Precision-Recall | 0,9899 | 0,9836 | Alto, mas parte disso é a base rate (0,95) — comparar com a linha de base do Painel 2 |
| **Brier Score** | Erro quadrático médio entre score previsto e resultado real (0 a 1, menor é melhor) | 0,0373 | 0,0457 | Mede calibração; 0,25 seria "chutar sempre 50%" |
| **F1** | Média harmônica de Precision e Recall | 0,9779 | 0,9743 | Alto, mas estruturalmente inflado pela classe majoritária — ver MCC abaixo |
| **Precision** | Dos marcados como risco, quantos eram risco de fato | 0,9567 | 0,9512 | Já é próximo da base rate — um "chuta tudo" teria Precision≈base_rate |
| **Recall** | Dos que eram risco de fato, quantos o modelo pegou | 1,0000 | 0,9984 | Quase 100% porque o threshold é muito baixo (política de custo) |
| **MCC** *(adicionado neste guia)* | Correlação entre predição e realidade usando as 4 células da matriz de confusão, simétrica | — | **0,076** | Perto de 0 = quase classificador trivial; não é inflado por classe majoritária como F1 — é o número mais honesto do conjunto |
| **Log Loss** *(adicionado neste guia)* | Penaliza probabilidades erradas, com mais peso quando o modelo erra com confiança alta | — | **0,197** | Complementa o Brier dando mais peso a erros "confiantes" |

**Por que MCC e Log Loss foram adicionados**: com `base_rate ≈ 0,95`, um
classificador que responde "risco" para todo mundo, sem olhar nenhuma
feature, já teria Precision≈0,95, Recall=1,0 e F1≈0,97 — os mesmos números
que este modelo real reporta. MCC não tem esse problema (fica em 0 para um
classificador que não aprendeu nada, e o valor medido aqui — 0,076 — está
bem perto disso). É o contraste mais direto entre "os números parecem bons"
(F1=0,97) e "o modelo aprendeu pouco de fato" (MCC=0,08) — e é exatamente
o que as Figuras 1 e 4 já mostram visualmente, só que em um número só.

## 5. Glossário

- **AUC-ROC**: área sob a curva ROC; 0,5 = aleatório, 1,0 = separação
  perfeita entre as classes.
- **Backtest**: validar o modelo em várias janelas de tempo diferentes (não
  só um corte), para checar estabilidade ao longo do tempo.
- **Base rate**: proporção da classe positiva no total — aqui, % de
  incidentes que de fato excedem o tempo esperado.
- **Brier Score**: erro quadrático médio entre a probabilidade prevista e o
  resultado real (0/1); versão numérica da calibração.
- **Calibração**: o quanto o score previsto corresponde à frequência real
  observada — um score de 70% é bem calibrado se, entre todos os chamados
  com esse score, ~70% de fato acontecem.
- **Classe majoritária / minoritária**: em classificação binária, a classe
  com mais (majoritária) ou menos (minoritária) exemplos no dado. Aqui a
  classe positiva (excedeu tempo esperado) é a majoritária — incomum, a
  maioria dos problemas de classificação trata o evento raro como alvo.
- **Confusion matrix (matriz de confusão)**: tabela 2×2 com verdadeiro
  positivo (TP), falso positivo (FP), falso negativo (FN) e verdadeiro
  negativo (TN).
- **F1-score**: média harmônica entre Precision e Recall; resume os dois
  num número só, mas some informação sobre qual dos dois está puxando o
  resultado.
- **Falso negativo (FN)**: o modelo previu "OK", mas o incidente realmente
  excedeu o tempo esperado — o erro mais caro neste contexto (violação
  passou despercebida).
- **Falso positivo (FP)**: o modelo previu "risco", mas o incidente ficou
  dentro do esperado — alarme falso.
- **Lift / Cumulative Gains (curva de ganho acumulado)**: mostra quanto
  vale a pena revisar os casos em ordem de score, em vez de aleatoriamente
  — "revisando os X% de maior score, capturo Y% dos casos reais".
- **Log Loss**: métrica de erro de probabilidade que penaliza mais os erros
  "confiantes" (score próximo de 0 ou 1 quando deveria ser o oposto) do que
  o Brier Score.
- **MCC (Matthews Correlation Coefficient)**: métrica de -1 a 1 que resume
  a matriz de confusão inteira de forma simétrica; 0 = classificador
  trivial, 1 = predição perfeita, -1 = predição sempre invertida. Não é
  distorcida por classe desbalanceada como F1/accuracy.
- **Paradoxo de Simpson**: quando uma tendência aparece num grupo de dados
  combinado mas desaparece (ou some) quando o grupo é separado em
  subgrupos — aqui, o AUC agregado parece melhor que o AUC de qualquer
  prioridade isolada.
- **PR-AUC (Precision-Recall AUC)**: área sob a curva Precision-Recall;
  mais informativa que AUC-ROC quando há desbalanceamento de classe forte.
- **Precision (precisão)**: dos casos que o modelo marcou como positivos,
  qual fração realmente era positiva.
- **Recall (revocação/sensibilidade)**: dos casos que realmente eram
  positivos, qual fração o modelo conseguiu identificar.
- **Regressor isotônico**: técnica de calibração que ajusta o score bruto
  do modelo para que ele corresponda à frequência real observada, sem
  assumir uma forma específica de curva (só que seja crescente).
- **SHAP (SHapley Additive exPlanations)**: técnica que atribui a cada
  feature uma contribuição numérica para a predição de um modelo, baseada
  em teoria dos jogos — permite explicar tanto o modelo como um todo
  (importância global) quanto uma predição específica (importância local).
- **Threshold**: o corte de score acima do qual a predição vira "1"
  (risco). Pode ser único para todo o modelo ou, como aqui, um por
  prioridade.
- **Waterfall (SHAP)**: gráfico que mostra, para um caso específico, as
  contribuições de cada feature empilhadas — visualiza como o score final
  foi "construído" a partir do valor base.
