# Métricas de validação consolidadas — PLAN.md Fase 13

> Nenhum número nesta página foi inventado ou estimado — todos vêm de
> artefatos já gerados pelos notebooks/scripts de modelo (`data/ml/prophet/`,
> `data/ml/xgboost/`, `data/ml/kmeans/`) ou do diagnóstico read-only novo
> desta rodada (`notebooks/diagnostico_kmeans_k.py`). Reaproveitado, não
> reconstruído — conforme Anexo A do `PLAN.md`.

## 1. Prophet — forecast total (`ml.fct_previsao_diaria_total`)

Fonte: `data/ml/prophet/metricas_avaliacao_final.parquet` (backtest de origem
móvel, 847 previsões de teste, horizonte D+1..D+7).

| Modelo | MAE | RMSE | WAPE% | Viés | MASE | Cobertura% |
|---|---|---|---|---|---|---|
| **prophet_regime** (produção) | 35,73 | 50,25 | 32,54 | 10,83 | 0,97 | 78,63 |
| prophet_hist_completo | 35,73 | 50,25 | 32,54 | 10,83 | 0,97 | 79,22 |
| mediana_dow_4sem (melhor baseline) | 31,24 | 49,74 | 28,45 | 0,84 | 0,85 | — |
| ma7 | 43,64 | 61,14 | 39,74 | 5,42 | 1,18 | — |
| ma28 | 42,08 | 59,69 | 38,33 | 8,71 | 1,14 | — |
| snaive_lag7 | 39,49 | 60,39 | 35,96 | 5,42 | 1,07 | — |
| naive_ultimo | 57,28 | 80,09 | 52,16 | 4,44 | 1,55 | — |
| ens_ma7_ma28 | 41,85 | 59,61 | 38,12 | 7,06 | 1,14 | — |

**Interpretação**: `prophet_regime` (o modelo em produção) **não supera** o
melhor baseline simples (`mediana_dow_4sem`) em MAE/WAPE/MASE — MASE=0,97
está acima de 1 seria "pior que naive sazonal", aqui fica levemente abaixo
de 1 mas perde para a mediana por dia-da-semana. O Prophet ganha em
cobertura de intervalo (78,6%, perto do nominal 80%) — o baseline de mediana
não produz intervalo de incerteza nenhum. Decisão de manter Prophet em
produção já é conhecida do time e documentada nos notebooks — este documento
só consolida o número, não é uma recomendação nova de troca de modelo.

**Por horizonte** (`data/ml/prophet/diagnostico_por_horizonte.parquet`): MAE
sobe de 34,58 (D+1) a 37,53 (D+7), cobertura cai de 80,2% (D+1) a 76,0%
(D+7) — degradação esperada e monotônica conforme o horizonte aumenta, sem
salto abrupto que indique instabilidade.

## 2. XGBoost — risco de SLA (`ml.fct_risco_incidente`)

Fonte: `data/ml/xgboost/fct_model_metrics.parquet` (modelo
`ola_risk_xgboost`, versão `v3_auditado`, `data_metrica=2026-08-22`).

| Partição | AUC-ROC | PR-AUC | Brier | F1 | Precision | Recall | n |
|---|---|---|---|---|---|---|---|
| Validação | 0,8458 | 0,9899 | 0,0373 | 0,9779 | 0,9567 | 1,0000 | 1.665 |
| Teste | 0,7965 | 0,9836 | 0,0457 | 0,9743 | 0,9512 | 0,9984 | 3.330 |
| Backtest (média) | 0,7637 (± 0,0332) | — | — | — | — | — | — |
| Backtest (janela recente) | 0,7865 | — | — | — | — | — | — |

**Meta registrada no artefato**: `auc_roc = 0,85` — **não atingida** em
nenhuma partição (`atingiu_meta=False` em validação/teste/backtest). Gap de
validação→teste (0,846→0,797, -4,9 p.p.) e queda adicional no backtest
temporal (0,764) — sinal de alguma perda de capacidade preditiva em dados
mais recentes/fora da amostra de treino, coerente com backtest temporal
sendo mais rigoroso que split aleatório.

**Base rate = 0,9505 (validação) / 0,9505 (teste)** — a classe positiva
(`target_excedeu_tempo` = duração > threshold de SLA da prioridade) é
majoritária, não minoritária. Isso é consistente com a EDA (seção 4 e 5 de
`docs/eda-consolidada.md`): a mediana de duração real (87,9h) já excede os
thresholds de SLA (4-96h conforme prioridade), então a maior parte dos
incidentes "excede o tempo esperado" por construção do rótulo — não é o
mesmo conceito de `kpi_status_int=1` (violação oficial de OLA, só 0,6% dos
incidentes). Recall muito alto (99,8-100%) e precision alta (95-96%) neste
cenário de classe majoritária não indicam necessariamente um classificador
forte para o evento raro de fato relevante ao negócio (violação de OLA) —
**recomendação para a Sprint 3**: deixar explícito, na apresentação da
métrica, que o alvo do XGBoost é "excedeu tempo esperado" (mais amplo),
não "violou OLA oficial" (mais raro e mais relevante para o KPI).

## 3. K-Means — clusters (`ml.fct_perfil_cluster`)

Fonte: `data/ml/kmeans/fct_model_metrics.parquet` (produção, `k=4`) +
`data/ml/kmeans/diagnostico_k_2_a_8.parquet` (diagnóstico novo desta rodada,
read-only, `notebooks/diagnostico_kmeans_k.py`).

| k | Silhouette | Davies-Bouldin | Inertia |
|---|---|---|---|
| 2 | **0,3814** (máximo) | 1,1502 | 177.913 |
| 3 | 0,3251 | 1,1563 | 138.174 |
| **4 (produção)** | 0,3413 | 0,9876 | 110.218 |
| 5 | 0,3258 | 1,0717 | 91.905 |
| 6 | 0,3297 | 1,0353 | 77.115 |
| 7 | 0,3400 | 0,9726 | 67.025 |
| 8 | 0,3543 | **0,8961** (mínimo) | 57.680 |

**Diagnóstico** (checkpoint humano, sem retreino): não há um vencedor único
e claro — silhouette é maximizado em `k=2` (0,3814), Davies-Bouldin é
minimizado em `k=8` (0,8961), sem "cotovelo" nítido na curva de inertia
(queda suave e contínua de k=2 a k=8, sem quebra clara). `k=4` (produção)
não é o melhor em nenhuma das duas métricas, mas também não é o pior —
fica em posição intermediária, e é o único valor testado com uma
justificativa de negócio já documentada (4 perfis operacionais
interpretáveis, mapeados manualmente em `ml.dim_cluster`). **Não há
evidência estatística forte o suficiente neste diagnóstico para forçar uma
troca de `k`** — mas também não há uma defesa estatística de que `k=4` seja
ótimo. Decisão de manter ou trocar `k` é checkpoint humano (PLAN.md Anexo A,
ML-2), não decidida automaticamente aqui.

**PCA**: `PCA(n_components=3)` (produção) explica **39,95%** da variância —
divergente do comentário do notebook ("95% variância", ver `CLAUDE.md` §4 e
`PLAN.md` Anexo A.3). Isso reduz a informação disponível para o clustering
mais do que a documentação original sugeria; não foi alterado nesta rodada
(mudar `n_components` muda o resultado do modelo em produção — checkpoint
humano).

---

## Resumo de status vs. meta

| Modelo | Meta registrada | Resultado real | Status |
|---|---|---|---|
| Prophet (forecast total) | superar baseline em MAE | **Não supera** `mediana_dow_4sem` em MAE/WAPE/MASE | ⚠️ |
| XGBoost (risco de SLA) | AUC-ROC ≥ 0,85 | 0,80 (teste) / 0,76 (backtest) | ⚠️ não atingida |
| K-Means (clusters) | k=4 definido a priori | Nenhum k domina nas 3 métricas; k=4 é intermediário | ⚠️ sem defesa estatística forte, sem evidência para trocar |

Nenhum destes três "⚠️" implica ação automática — todos exigem decisão
humana (retreinar Prophet com outra configuração? relaxar meta de AUC-ROC
do XGBoost? manter k=4 por justificativa de negócio apesar do diagnóstico?).
Registrado aqui para a Sprint 3 e para não repetir a alegação de "métricas
já validadas" sem essa ressalva.
