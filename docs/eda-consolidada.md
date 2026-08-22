# EDA consolidada — PLAN.md Fase 12

> Consolida em formato Achado/Impacto/Decisão as evidências já levantadas em
> `notebooks/02_exploratory_data_analysis_silver.ipynb` (EDA completa da
> camada Silver, 6 fases próprias) mais consultas de confirmação rodadas
> direto contra `dw.fct_incidentes` em 2026-08-22 (41.441 linhas, grão já
> filtrado — ver `docs/modelo-dimensional.md`). Números desta página são
> reais, extraídos ao vivo do banco `fiap`, não estimados.

## 1. Evolução temporal — volume mensal estável no grão filtrado

**Achado**: no grão de `dw.fct_incidentes` (pós-filtro `status <> 'Sem
Intervenção'` + `aberto >= 2025-01-01`), o volume mensal de 2025 é
relativamente estável: 2.343 a 4.053 chamados/mês, sem o salto de regime de
~21-27 mil/mês descrito em `docs/schema-fonte-incidentes.md` — esse salto
existe na tabela bruta `public.incidentes` (122.543 linhas, inclui ruído de
monitoramento autorresolvido), não no grão de esforço real.

**Impacto**: o corte de regime que o Prophet detecta e usa para restringir o
treino (`quebras_de_patamar_detectadas`, ver `CLAUDE.md` §10) opera sobre
`ml.ml_forecast_dataset` — mesma linhagem filtrada de `ml.ml_base_features` —
não sobre o volume bruto. Confundir os dois levaria a esperar uma quebra de
patamar que não existe nesse grão.

**Decisão**: manter a distinção clara nos documentos — "salto de regime" é um
fenômeno da fonte bruta (ruído de monitoramento crescendo), não do volume de
esforço real usado para previsão.

## 2. Prioridade — concentração em P3, quase nenhum P1

**Achado**: `P3 - Moderada` = 56,2% (23.294), `P2 - Alta` = 22,6% (9.383),
`P4 - Baixa` = 20,4% (8.439), `Não Classificada` = 0,8% (324),
`P1 - Crítica` = 1 incidente (0,0%). P2+P3 juntos = 78,9%.

**Impacto**: confirma que o foco P2/P3 do desafio (PLAN.md Fase 2) cobre a
grande maioria do volume operacional — e que P1 tem volume estatisticamente
insignificante para qualquer modelo dedicado.

**Decisão**: manter P1 fora de qualquer forecast/classificação dedicada
(dado insuficiente); P2+P3 como filtro padrão nas telas, conforme já
registrado em `CLAUDE.md`.

## 3. Equipe — concentração extrema em Team14/Team11/Team05

**Achado**: `Team14` = 41,3% (17.107), `Team11` = 23,4% (9.688), `Team05` =
18,0% (7.439) — as 3 maiores equipes somam 82,7% do volume. As 13 equipes
restantes dividem os 17,3% restantes.

**Impacto**: justifica diretamente o corte de viabilidade A/B/C do forecast
por equipe (`docs/forecast-por-equipe.md`) — só as equipes de maior volume
sustentam um Prophet individual; a cauda longa exige split proporcional.

**Decisão**: nenhuma — arquitetura híbrida já reflete corretamente essa
concentração.

## 4. Duração — outliers extremos, mediana muito abaixo da média

**Achado**: média de duração = 5.756,1h (~240 dias), mediana = 87,9h (~3,7
dias), p95 = 17.088,2h (~2 anos), máximo = 436.529,2h (~50 anos).

**Impacto**: a mediana (87,9h) já excede sozinha o threshold de SLA de P2
(4h) e P3 (12h) — isso explica por que a taxa de `target_excedeu_tempo`
(rótulo de treino do XGBoost) é tão alta (~95% de base rate, ver
`docs/metricas-validacao.md`): não é um desbalanceamento artificial, é
reflexo direto da distribuição real de duração. Usar média simples de
duração em qualquer painel (ex.: tela Clusters) infla o número por causa dos
outliers de cauda longa.

**Decisão**: usar sempre mediana (ou filtro de outlier) para duração em
painéis — já era a orientação registrada em `docs/modelo-dimensional.md`,
esta seção só quantifica com números reais.

## 5. Violação de SLA — evento raro dentro do subconjunto elegível

**Achado**: `kpi_status_int`: -1 (isento/desconhecido) = 39,3% (16.285), 0
(dentro do prazo) = 60,1% (24.918), 1 (violou) = 0,6% (238 incidentes).

**Impacto**: violação de SLA propriamente dita (`kpi_status_int=1`) é
extremamente rara (238 em 41.441) — bem diferente do rótulo
`target_excedeu_tempo` do XGBoost (que mede duração > threshold bruto, sem o
filtro de elegibilidade de KPI). São dois conceitos de "risco" distintos,
não podem ser usados como sinônimos em nenhuma tela.

**Decisão**: documentar explicitamente essa diferença na tela KPI (só
`kpi_status_int`/OLA oficial) vs. tela Fatores/XGBoost (`target_excedeu_tempo`,
mais amplo) — reforça a regra já existente de não misturar as duas métricas.

## 6. Sazonalidade semanal — pico quinta-feira, queda no fim de semana

**Achado**: volume por dia da semana (2025 completo): Domingo 2.482, Segunda
6.502, Terça 6.869, Quarta 7.279, Quinta 7.954 (pico), Sexta 6.420, Sábado
3.935. Dias úteis somam ~85% do volume.

**Impacto**: confirma a sazonalidade semanal que o Prophet já modela
(`weekly_seasonality=True`) e justifica alertas do tipo "D+7 cai num fim de
semana" (PLAN.md Fase 11) como um sinal real, não arbitrário.

**Decisão**: nenhuma — comportamento já capturado pelo modelo.

## 7. Nulos de produto/categoria — já tratados na camada `dw`

**Achado**: 33 combinações distintas em `dw.dim_produto_categoria` usam o
valor `"Não Classificado"` — confirma que o tratamento de nulo (63,6%/63,4%
de nulos na fonte bruta, ver `docs/schema-fonte-incidentes.md`) já está
resolvido na carga do `dw`, não é uma lacuna aberta.

**Impacto**: qualquer agrupamento por produto/categoria nas telas precisa
tratar `"Não Classificado"` como uma categoria legítima (aparece inclusive
no split de `ml.fct_previsao_produto`, Fase 4 — 5,2% de share histórico),
não como erro de dado.

**Decisão**: manter `"Não Classificado"` visível nas telas, não filtrar
silenciosamente.

## 8. Outliers pontuais — "storm days" por incidente-pai

**Achado**: já documentado em `docs/forecast-por-equipe.md` §4 — 22 dias
distintos de 2025 têm um único incidente-pai respondendo por ≥40% do volume
diário de uma equipe (ex.: `Team05`, 2025-06-26, `INC8445074` = 84% do
volume do dia). Padrão operacional real e recorrente, não bug de atribuição.

**Impacto**: sem tratamento, esses dias distorceriam a tendência/changepoints
do Prophet nas equipes afetadas (Grupo A/B).

**Decisão**: já tratado — `holidays` pontuais no Prophet (`lower_window=0`/
`upper_window=0`, sem projeção futura). Nenhuma ação nova necessária.

---

Fonte completa e detalhada da EDA original (6 fases, hipóteses de negócio
validadas): `notebooks/02_exploratory_data_analysis_silver.ipynb`. Esta
página é o resumo executivo para a Sprint 3 (PLAN.md Fase 16), não substitui
o notebook.
