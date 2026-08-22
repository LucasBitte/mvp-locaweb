# MVP Locaweb — Estado Atual do Projeto

> Snapshot do que existe hoje no repositório. Para o raciocínio por trás de
> cada decisão, ver os documentos específicos linkados ao longo do texto.

## 1. O que é

Pipeline de dados de ponta a ponta para um dashboard de AIOps de incidentes
de TI: tabela bruta no Postgres → modelo dimensional (star schema) → saídas
de três modelos de ML (previsão de volume, clustering, risco de SLA) →
dashboard (React + FastAPI, ainda não construído).

Repositório: **[LucasBitte/mvp-locaweb](https://github.com/LucasBitte/mvp-locaweb)**
(branch `main` protegida, exige PR). Local em `/home/fiap/mvp-locaweb`.
Dashboard-alvo: [`docs/design/aiops_dashboard_redesign.html`](design/aiops_dashboard_redesign.html)
("AIOps — Locaweb"), 6 telas — Painel, Detalhe, KPI, Fatores, Clusters, Alertas.

## 2. Arquitetura de dados

```
public.incidentes              (bronze — 122.543 linhas, 2023-2025)
        │
        ▼  notebook 03
staging.incidentes_silver      (silver — 41.441 linhas, pós-2025, esforço real)
        │
        ├──▶ notebook 04 ──▶ dw.*        (star schema)
        │
        └──▶ notebook 05 ──▶ ml.ml_*     (marts de features)
                                   │
                                   ▼  forecast / clustering / xgboost
                              ml.fct_*   (saídas dos modelos)
```

4 schemas no banco `fiap`:

| Schema | Papel |
|---|---|
| `public` | Fonte bruta (`incidentes`) |
| `staging` | Camada Silver (`incidentes_silver`) |
| `dw` | Star schema — modelo dimensional para BI/API |
| `ml` | Marts de features + saídas dos modelos de ML |

Documentação coluna-a-coluna de todas as tabelas:
[`docs/dicionario-dados.md`](dicionario-dados.md). Raciocínio do modelo
dimensional: [`docs/modelo-dimensional.md`](modelo-dimensional.md).

## 3. `dw` — modelo dimensional

6 dimensões (`dim_produto_categoria`, `dim_grupo`, `dim_tempo`,
`dim_status`, `dim_prioridade`, `dim_abertura`) + `dw.fct_incidentes`, grão
**1 linha = 1 incidente** (41.441 linhas), filtrado a
`status <> 'Sem Intervenção'` e `aberto >= 2025-01-01`.

## 4. `ml` — marts de features

4 tabelas no grão de incidente/dia, construídas a partir de
`staging.incidentes_silver`: `ml.ml_base_features` (1 linha/incidente, 40
colunas), `ml.ml_cluster_dataset`, `ml.ml_sla_classification_dataset`
(ambas 1 linha/incidente, leakage-free) e `ml.ml_forecast_dataset` (1
linha/dia, 365 linhas).

## 5. `ml` — saídas dos modelos de ML

| Modelo | Lê de | Grava em | Cobertura |
|---|---|---|---|
| Prophet (forecast) | `ml.ml_forecast_dataset` | `ml.fct_previsao_diaria_total/_prioridade/_categoria` | D+1..D+7, append por execução |
| K-Means (clusters) | `ml.ml_cluster_dataset` | `ml.dim_cluster` (4 clusters, seed manual) + `ml.fct_perfil_cluster` | 41.441 incidentes clusterizados |
| XGBoost + SHAP (risco) | `ml.ml_sla_classification_dataset` + `ml.ml_base_features` | `ml.fct_importancia_feature`, `ml.fct_risco_incidente`, `ml.fct_shap_incidente` | 41.441 incidentes com score; SHAP nos 30 de maior risco |

Notas de escopo que valem saber ao consumir estas tabelas:
- Forecast por prioridade/categoria é **proporção histórica** sobre o total
  previsto, não um modelo treinado por corte.
- `ml.fct_shap_incidente` explica os incidentes de maior risco, não o
  volume previsto do dia seguinte.
- Metas de OLA usadas na tela KPI (`dw.ref_meta_sla_anual` — a criar na
  Etapa 5) ainda não têm fonte real; ficarão com os números do mockup como
  placeholder.

## 6. Estrutura do repositório

```
mvp-locaweb/
├── db/migrations/     # DDL versionado (022 migrations)
├── etl/                # db.py (conexão via .env), transform.py (bronze -> dw, standalone)
├── notebooks/          # 01-05 (pipeline) + os 3 modelos de ML + conexao_banco_fiap.ipynb
├── app/api/             # FastAPI (esqueleto — ainda não construído)
├── app/web/              # React + Vite + Tailwind + Recharts (esqueleto)
├── docs/                # Documentação
├── tests/                # pytest
└── data/                 # parquets locais (data/raw, data/ml/<modelo>/), gitignored
```

`main` protegida (exige PR, sem push direto), branches `feature/<descrição>`,
squash-merge.

## 7. Status por etapa

| Etapa | O quê | Status |
|---|---|---|
| 0-1 | Setup do repo + inspeção do schema bruto | ✅ |
| 2 | Modelo dimensional (`dw.*`) | ✅ |
| 3 | Marts de features (`ml.ml_*`) | ✅ |
| 4 | Modelos de ML rodando contra o banco + output real (`ml.fct_*`) | ✅ |
| 5 | API FastAPI servindo as 6 telas do mockup | ⬜ próximo passo |
| 6 | Dashboard React consumindo a API | ⬜ |

## 8. Como rodar

```bash
# 1. Credenciais (não versionadas)
cp .env.example .env   # preencher FIAP_DB_*

# 2. Ambiente Python
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
./venv/bin/pip install -r requirements-notebooks.txt   # p/ rodar os notebooks

# 3. Pipeline, em ordem (migrations já aplicadas no banco fiap)
jupyter nbconvert --to notebook --execute --inplace notebooks/03_bronze_silver_transformacao.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/04_dw_star_schema.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/05_ml_feature_marts.ipynb
python notebooks/forecast_incidentes_revisado.py --fonte sql
jupyter nbconvert --to notebook --execute --inplace notebooks/model_clustering_kmeans_Revisado.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/model_risk_xgboost_.ipynb

# 4. Testes
./venv/bin/pytest tests/
```
