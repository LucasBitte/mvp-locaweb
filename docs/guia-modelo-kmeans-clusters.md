# Guia educacional — Modelo K-Means (Perfis Operacionais / Clusters)

> Documento de apoio para ler e entender `notebooks/model_clustering_kmeans_Revisado.ipynb`
> e as seções `[6c]` (Análise visual dos clusters) e `10` (Gráfico do
> cotovelo) desse notebook — explica cada gráfico, cada métrica, o
> resultado real medido e o porquê por trás de cada escolha. Fecha com um
> glossário. Não substitui o notebook (fonte de verdade dos números) nem
> `docs/metricas-validacao.md` §3 (números já consolidados).

## 1. O que este modelo faz

O K-Means é um algoritmo de **agrupamento não supervisionado**: recebe os
41.441 incidentes de 2025, cada um descrito por 14 características
"de causa" (prioridade, categoria, grupo responsável, horário, dia da
semana etc. — nunca duração ou taxa de resolução, que são "de efeito" e
ficariam de fora para não vazar informação do resultado para o
agrupamento), e agrupa os incidentes em **k=4 clusters** — grupos que se
parecem entre si nessas características, sem que ninguém diga ao algoritmo
o que cada grupo "significa".

Depois de treinado, cada cluster (A, B, C, D) recebe um **nome e descrição
curados manualmente** (`ml.dim_cluster`) interpretando o padrão observado
nas colunas "de efeito" (duração real, taxa de resolução, taxa que excedeu
o tempo esperado) — essa é a única parte do processo que não é automática:
o algoritmo agrupa, uma pessoa interpreta e nomeia.

## 2. Como o modelo foi construído

- **Features de causa** (14 colunas, codificadas em 17 colunas numéricas:
  hora/dia/mês em seno+cosseno para preservar a natureza cíclica do tempo,
  categóricas de alta cardinalidade por frequência).
- **Padronização** (`StandardScaler`) seguida de **PCA para 3 componentes**
  — reduz as 17 colunas para 3, explicando **39,95%** da variância (o
  comentário original do notebook dizia "95%"; não foi corrigido porque
  mudaria o resultado do modelo em produção — checkpoint humano, ver
  `CLAUDE.md` §4).
- **KMeans(k=4)** treinado no espaço reduzido pelo PCA.
- **Diagnóstico de k** (`notebooks/diagnostico_kmeans_k.py`, read-only,
  não altera o modelo em produção): testa k de 2 a 8 e mede 3 métricas de
  qualidade de clustering para cada k.

## 3. Os gráficos, um por um

### Seção 10 — Gráfico do cotovelo (por que k=4?)

**O gráfico**: 3 painéis lado a lado, um por métrica, todos com o mesmo
eixo X (k de 2 a 8) e uma linha vertical marcando `k=4` (produção).

- **Silhouette Score** (quanto maior, melhor separados e coesos estão os
  clusters; varia de -1 a 1). **Resultado real**: máximo em k=2 (0,381);
  k=4 fica em 0,341 — não é o melhor, mas é um **pico local** (melhor que
  k=3=0,325 e k=5=0,326, os vizinhos imediatos).
- **Davies-Bouldin Index** (quanto menor, melhor — mede o quão parecidos
  são os clusters entre si; clusters ideais têm índice baixo).
  **Resultado real**: mínimo em k=8 (0,896); k=4 fica em 0,988, também não
  é o melhor.
- **Inertia / método do cotovelo** (soma das distâncias ao quadrado de
  cada ponto ao centro do seu cluster; sempre cai conforme k sobe — a
  pergunta é onde a queda desacelera, formando um "cotovelo").
  **Resultado real**: queda suave e contínua de k=2 a k=8, **sem cotovelo
  nítido** em nenhum ponto.

**Porquê isso importa**: nenhuma das 3 métricas aponta k=4 como o melhor
valor possível — e é importante que o notebook mostre isso, em vez de
esconder. `k=4` foi escolhido por uma razão de **negócio** (4 perfis
operacionais interpretáveis, curados manualmente), não por uma métrica
estatística vencedora. O gráfico é a evidência visual dessa honestidade:
não há uma linha reta entre "estatística" e "k=4", a decisão é humana e
está documentada como tal.

**Registro de governança formal**: este achado fecha o checkpoint `ML-2`
do `PLAN.md` (Anexo A) — não é uma observação solta deste guia, é uma
decisão de projeto documentada e fechada, sem retreino nem alteração de
`ml.dim_cluster`/`ml.fct_perfil_cluster`.

### Seção [6c] — Análise visual do resultado treinado

**1. Tabela de resumo executivo**: contagem, média e mediana de 6 métricas
de efeito por cluster — a base numérica para todos os gráficos seguintes.

**2. Bubble chart** (duração mediana × % excedeu tempo esperado × volume):
cada bolha é um cluster; posição = onde ele fica nessas duas dimensões;
tamanho = fatia do volume total.

- **Resultado real**: A=30,8h/94,8%/32,1%, B=198,3h/95,2%/32,9%,
  C=20,8h/94,3%/24,6%, D=93,8h/98,0%/10,5%.
- **Porquê**: é a mesma leitura executiva que a tela "Clusters" do
  dashboard usa — conecta o notebook ao que a operação vê.

**3. Box/violin plots** (distribuição de duração e score de risco por
cluster, em escala logarítmica para duração — a cauda é extrema, p95 chega
a ~2 anos de duração aparente por corrupção de dado, ver
`docs/eda-consolidada.md` achado 4).

- **Porquê**: a tabela de resumo só mostra média/mediana; o violin plot
  mostra a **forma inteira** da distribuição — se um cluster é uniforme ou
  tem uma cauda longa escondida atrás da média.

**4. Radar chart** (assinatura normalizada 0-1 de 4 métricas por cluster).

- **Porquê**: compara os 4 clusters em várias dimensões ao mesmo tempo,
  em um único gráfico — mostra a "forma" de cada perfil de uma vez.

**5. PCA scatter + t-SNE** (separação espacial dos pontos no espaço
reduzido, coloridos por cluster).

- **Porquê**: verifica visualmente se os clusters realmente formam grupos
  separados no espaço em que foram treinados (PCA) e numa projeção não
  linear alternativa (t-SNE, mais fiel a vizinhanças locais que o PCA).

## 4. As métricas, uma por uma

| Métrica | O que mede | k=4 (produção) | Melhor valor testado (k) | Leitura |
|---|---|---|---|---|
| **Silhouette Score** | Coesão interna vs. separação entre clusters (-1 a 1, maior é melhor) | 0,3413 | 0,3814 (k=2) | k=4 não é o máximo, mas é razoável — valores acima de 0,3 já indicam alguma estrutura real |
| **Davies-Bouldin Index** | Similaridade média entre cada cluster e o mais parecido com ele (menor é melhor) | 0,9876 | 0,8961 (k=8) | k=4 fica no meio da faixa observada (0,90 a 1,16) |
| **Inertia** | Soma das distâncias² de cada ponto ao centro do seu cluster (sempre cai com k, usada para o "cotovelo") | 110.218 | — (cai monotonicamente) | Sem cotovelo nítido, não decide k sozinha |
| **PCA — variância explicada** | Quanta informação das 17 features originais sobrevive na redução a 3 componentes | 39,95% | — | Bem abaixo do que o comentário original do notebook (95%) sugeria — perda real de informação, não corrigida (mudaria o modelo em produção) |

**Por que nenhuma métrica "decide" k=4 sozinha**: as 3 métricas de
qualidade de clustering medem coisas ligeiramente diferentes (coesão,
separação entre clusters, compactação) e não concordam entre si sobre qual
k é melhor — isso é comum em dados reais sem estrutura de cluster
perfeitamente definida. Diferente do modelo XGBoost (onde AUC-ROC tem uma
meta clara e não atingida), aqui a decisão de manter k=4 é primariamente
de **negócio** (4 perfis operacionais que fazem sentido para a operação
interpretar e agir), com o diagnóstico estatístico documentado como
neutro — nem confirma nem refuta a escolha.

## 5. Glossário

- **Centróide**: o ponto médio (no espaço das features) de todos os
  incidentes de um cluster — o "representante" do grupo.
- **Clustering / agrupamento não supervisionado**: técnica que separa
  dados em grupos sem usar nenhum rótulo conhecido de antemão — diferente
  de classificação (como o XGBoost), onde o modelo aprende a prever um
  rótulo já existente.
- **Davies-Bouldin Index**: métrica de qualidade de clustering que compara
  cada cluster com o cluster mais parecido com ele; valores menores
  indicam clusters mais distintos entre si.
- **Feature de causa / feature de efeito**: causa é o que se sabe *antes*
  do incidente ser resolvido (prioridade, categoria, horário); efeito é o
  que só se sabe *depois* (duração real, se foi resolvido). Features de
  efeito ficam fora do treino do K-Means para não vazar o resultado para
  dentro do agrupamento.
- **Inertia (WCSS — Within-Cluster Sum of Squares)**: soma das distâncias
  ao quadrado entre cada ponto e o centróide do seu cluster; sempre
  diminui conforme k aumenta (com k = número de pontos, chega a zero).
- **k**: o número de clusters que o algoritmo deve formar — é um parâmetro
  escolhido antes de rodar o K-Means, não algo que o algoritmo descobre
  sozinho.
- **Método do cotovelo**: técnica informal de escolher k observando o
  gráfico de inertia por k e procurando o ponto onde a queda desacelera
  bruscamente (formando um "cotovelo") — quando essa desaceleração não é
  nítida (como aqui), o método não dá uma resposta clara.
- **PCA (Principal Component Analysis / Análise de Componentes
  Principais)**: técnica que reduz o número de colunas (dimensões) de um
  dado, combinando-as em um número menor de "componentes" que preservam o
  máximo de variância (informação) possível.
- **Silhouette Score**: métrica de qualidade de clustering que mede, para
  cada ponto, o quão mais perto ele está do seu próprio cluster do que do
  cluster vizinho mais próximo; varia de -1 (mal agrupado) a 1
  (perfeitamente agrupado).
- **t-SNE (t-distributed Stochastic Neighbor Embedding)**: técnica de
  redução de dimensionalidade para visualização, diferente do PCA — prioriza
  preservar vizinhanças locais (pontos próximos no espaço original ficam
  próximos na visualização), à custa de distorcer distâncias globais.
- **Variância explicada**: percentual da informação (variabilidade) do
  dado original que sobrevive depois de uma redução de dimensionalidade
  como o PCA — quanto maior, menos informação foi perdida no processo.
