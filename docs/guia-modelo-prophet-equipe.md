# Guia educacional — Modelo Prophet por Equipe (Pressão Operacional)

> Documento de apoio para ler e entender `notebooks/forecast_equipe.py` e
> os gráficos de `notebooks/forecast_equipe_graficos.py` (script novo, não
> faz parte do pipeline de produção — lê `ml.fct_previsao_grupo`/
> `ml.fct_pressao_equipe` direto do banco `fiap`, só `SELECT`, e plota) —
> explica cada gráfico, a arquitetura híbrida, e é honesto sobre uma
> lacuna real de métricas neste modelo específico. Fecha com um glossário.
> Fonte de verdade: `docs/forecast-por-equipe.md` (arquitetura completa).

## 1. O que este modelo faz

Prevê o volume de incidentes de D+1 a D+7 **por equipe** (16 grupos
designados), não só o total agregado. A saída alimenta `ml.fct_pressao_equipe`
— usada na tela Painel do dashboard ("Pressão por equipe") — que compara o
previsto contra a própria média histórica de cada equipe.

**A diferença chave em relação ao Prophet total**: prever volume por
equipe individual é muito mais difícil, porque a maioria das equipes tem
volume baixo (menos de 1 incidente/dia em 8 das 16 equipes) — séries assim
são ruidosas demais para um modelo de série temporal aprender um padrão
confiável sozinho. Por isso o modelo não usa uma única técnica para todas
as equipes — usa **três**, escolhidas conforme o volume de cada uma.

## 2. A arquitetura híbrida A/B/C

O critério é a **média diária histórica de incidentes** de cada equipe
(calendário completo de 2025, contando também os dias sem nenhum
incidente):

| Faixa de volume | Método tentado | O que faz |
|---|---|---|
| ≥ 5/dia | **Prophet individual** (A) | Treina um Prophet só para aquela equipe — volume suficiente para o modelo aprender um padrão próprio |
| 1 a 5/dia | **Prophet individual, com fallback semanal** (B) | Tenta o mesmo Prophet diário; se ele perder do melhor baseline por mais de 5% de MAE, cai para um Prophet agregado por semana (menos ruidoso) |
| < 1/dia | **Split proporcional** (C) | Não treina nenhum modelo próprio — pega a previsão do **total agregado** (Prophet total) e distribui pela participação histórica de cada equipe |

**Resultado real** (16 equipes, origem mais recente): 7 equipes em
Prophet individual (Team14, Team11, Team05, Team09, Team12, Team17,
Team02), 1 em Prophet semanal (Team03), 8 em split proporcional (Team10,
Team16, Team01, Team15, Team07, Team08, Team04, Team06).

**Detalhe importante que o Painel 2 mostra**: Team12, Team17 e Team02 têm
volume na faixa "B" (1 a 5/dia) mas **na prática rodaram Prophet
individual**, não semanal — só Team03 de fato caiu para o fallback. O
rótulo do grupo (A/B/C) é sobre *viabilidade de tentativa*; o método
efetivamente gravado no banco é o que realmente rodou depois do veredito
de cada equipe.

## 3. Os gráficos, um por um

### Figura 1 — Arquitetura híbrida: distribuição e critério

**Painel 1 — Distribuição do método.** Quantas das 16 equipes caem em cada
um dos 3 métodos.

- **Porquê importa**: mostra de cara que a maioria das equipes (8 de 16)
  não tem modelo próprio — dependem inteiramente da previsão do total.

**Painel 2 — Volume médio por equipe, com os limiares marcados.** Barra
horizontal por equipe, ordenada por volume, colorida pelo método, com
linhas verticais nos limiares de 1 e 5 incidentes/dia.

- **Porquê importa**: é a prova visual do critério — dá para ver
  exatamente onde cada equipe caiu e por quê, incluindo o caso de
  Team12/Team17/Team02 (na faixa B mas rodando A).

### Figura 2 — Pressão operacional e formato da previsão

**Painel 3 — Pressão relativa por equipe (D+1).** Barra horizontal com o
desvio percentual do previsto frente à **própria** média histórica de cada
equipe (não volume absoluto) — verde/âmbar/vermelho conforme o nível.

- **Porquê importa**: essa é a métrica que a tela Painel realmente mostra.
  Usar o desvio relativo (não absoluto) é deliberado — uma equipe pequena
  que dobra de volume pesa igual, proporcionalmente, a uma grande equipe
  que sobe 10%; comparar em volume absoluto esconderia isso.

**Painel 4 — Curvas de previsão D+1..D+7 para 3 equipes, uma por método.**

- **Resultado real**: Team14 (Prophet individual, alto volume) tem uma
  curva com forma própria, oscilando dia a dia; Team03 (Prophet semanal) é
  mais suave; Team06 (split proporcional, volume quase zero) segue
  fielmente a forma da previsão do total, sem nenhuma característica
  própria.
- **Porquê importa**: mostra visualmente a consequência prática da
  arquitetura híbrida — equipes pequenas não têm uma previsão "sua", têm
  uma fatia proporcional da previsão do total.

## 4. As métricas — e uma lacuna real que precisa ficar registrada

Diferente dos outros 3 modelos deste projeto (Prophet total, XGBoost,
K-Means), **`forecast_equipe.py` não persiste nenhuma métrica de acurácia
por equipe em parquet ou tabela do banco** — o backtest roda, o veredito
("SUPERA"/"EMPATA"/"PERDE PARA" o melhor baseline) é calculado, mas só
aparece no `print()` da execução, sem gravação. Os únicos números
versionados vêm de `docs/forecast-por-equipe.md` §4 (copiados manualmente
do stdout de uma execução):

| Equipe | MAE (Prophet) | WAPE% | Veredito vs. melhor baseline |
|---|---|---|---|
| Team14 | 16,89 | 32,6% | Empata (+0,6%) |
| Team11 | 5,72 | 29,1% | Empata (-1,2%) |
| Team05 | 11,11 | 62,8% | Empata (-4,2%) |
| Team09 | 2,83 | 42,3% | Supera (-5,7%) |

**Leitura honesta**: nenhuma das 4 equipes do Grupo A supera o melhor
baseline por margem folgada (só Team09 supera, por 5,7 pontos) — as
outras 3 empatam. Isso é esperado (volume por equipe é mais ruidoso que o
total agregado, ver o guia do Prophet total) e não invalida o modelo: o
Prophet ganha em cobertura de intervalo (76-92%, varia por equipe) e é a
única técnica que produz `yhat_lower`/`yhat_upper` — os baselines de
comparação não produzem intervalo algum.

**Por que isso é registrado aqui como lacuna, não preenchido com número
aproximado**: seguindo o mesmo princípio já aplicado no resto deste
projeto (nunca fabricar dado) — recalcular o backtest por equipe para
gerar um parquet reproduzível exigiria re-treinar Prophet 16 vezes (ou
mais, por semente), o que está fora do escopo de "ler o que já existe e
plotar". Fica registrado como uma melhoria futura possível: persistir
`metricas_backtest_equipe.parquet` em `forecast_equipe.py`, no mesmo
padrão que `forecast_incidentes_revisado.py` já usa para o total.

## 5. Glossário

- **Arquitetura híbrida**: usar mais de uma técnica de modelagem no mesmo
  pipeline, escolhida por um critério explícito (aqui, volume histórico),
  em vez de forçar uma única técnica para todos os casos.
- **Fallback**: método alternativo usado quando o método preferido falha
  ou tem desempenho ruim — aqui, cair de Prophet diário para Prophet
  semanal quando o diário perde do baseline.
- **MAE, WAPE, cobertura**: ver `docs/guia-modelo-prophet-forecast.md` §5
  — as mesmas métricas, aplicadas por equipe em vez de ao total agregado.
- **Pressão relativa**: desvio percentual entre o volume previsto e a
  média histórica da mesma equipe — nunca é comparada entre equipes
  diferentes, cada uma é seu próprio ponto de referência.
- **Split proporcional**: técnica que não treina nenhum modelo — distribui
  uma previsão já existente (aqui, do total agregado) entre subgrupos
  conforme a participação histórica de cada um.
- **Veredito (SUPERA/EMPATA/PERDE PARA)**: comparação entre o MAE do
  Prophet e o MAE do melhor baseline simples, com margem de ±5% definindo
  "empate" — mesma lógica usada no modelo Prophet total.
