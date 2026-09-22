# notebooks/ — pipeline de dados e modelos

Os arquivos `etapaNN_` rodam **nesta ordem**: cada um assume que os anteriores
já rodaram contra o banco `fiap`. Os prefixos `exploracao_` e `apoio_` são
análises de apoio — não fazem parte do pipeline e podem ser abertos em
qualquer momento.

## Pipeline (ordem de execução)

| # | Arquivo | O que faz | Lê de | Grava em |
|---|---|---|---|---|
| 01 | `etapa01_bronze_para_silver.ipynb` | Filtra esforço real (exclui "Sem Intervenção", mantém 2025+) e cria 6 features derivadas | `public.incidentes` (122.543) | `staging.incidentes_silver` (41.441) |
| 02 | `etapa02_star_schema_dw.ipynb` | Monta o modelo dimensional: 6 dimensões + tabela fato | `staging.incidentes_silver` | `dw.dim_*`, `dw.fct_incidentes` |
| 03 | `etapa03_feature_marts_ml.ipynb` | Constrói as marts de features de ML (sem vazamento de alvo) | `dw.*` | `ml.ml_base_features`, `ml.ml_forecast_dataset`, `ml.ml_cluster_dataset`, `ml.ml_sla_classification_dataset` |
| 04 | `etapa04_forecast_volume_total.py` | Prophet do volume diário total, D+1 a D+7, com backtest contra 6 baselines | `ml.ml_forecast_dataset` | `ml.fct_previsao_diaria_total` + splits `_prioridade`/`_categoria` |
| 05 | `etapa05_forecast_por_equipe.py` | Forecast por equipe, arquitetura híbrida A/B/C (Prophet individual, semanal ou split proporcional) | `ml.ml_base_features`, `ml.fct_previsao_diaria_total` | `ml.fct_previsao_grupo` |
| 06 | `etapa06_pressao_por_equipe.py` | Pressão relativa: previsto vs. média histórica **da própria equipe** | `ml.fct_previsao_grupo` | `ml.fct_pressao_equipe` |
| 07 | `etapa07_forecast_por_produto.py` | Split do total previsto por produto, via proporção histórica (regra, não modelo) | `ml.fct_previsao_diaria_total`, `ml.ml_base_features` | `ml.fct_previsao_produto` |
| 08 | `etapa08_recorrencia_operacional.py` | Recorrência por janela móvel de 30 dias vs. os 30 anteriores | `dw.fct_incidentes` | `dw.fct_recorrencia_operacional` |
| 09 | `etapa09_clusters_kmeans.ipynb` | K-Means (k=4) sobre features de causa; perfis operacionais | `ml.ml_cluster_dataset` | `ml.dim_cluster`, `ml.fct_perfil_cluster` |
| 10 | `etapa10_risco_sla_xgboost.ipynb` | XGBoost + SHAP: risco de exceder o tempo esperado da prioridade | `ml.ml_sla_classification_dataset` | `ml.fct_risco_incidente`, `ml.fct_shap_incidente`, `ml.fct_importancia_*` |
| 11 | `etapa11_diagnostico_k_kmeans.py` | Diagnóstico comparativo de `k=2..8` — **read-only**, não altera nada no banco | `ml.ml_cluster_dataset` | nada (só CSV local) |

### Dependências que não são óbvias pela numeração

- **05 depende de 04** na mesma origem: o Grupo C lê o `yhat` já persistido
  em `ml.fct_previsao_diaria_total`.
- **06 depende de 05**: lê `ml.fct_previsao_grupo`.
- **07 depende de 04**: distribui o total já previsto.
- **08 é independente**: lê direto de `dw.fct_incidentes`, pode rodar a
  qualquer momento depois da etapa 02.
- **11 depende de 03** (a mart de cluster), não da etapa 09 — é um
  diagnóstico paralelo, não uma etapa posterior ao treino.

Os scripts 05, 06 e 07 importam funções do 04 (`Config`, `prever_prophet`,
`backtest`, `metricas_gerais`, `BASELINES`) em vez de duplicar a metodologia —
por isso os nomes de arquivo não começam com número: módulo Python não pode
começar com dígito.

## Análises de apoio (fora do pipeline)

| Arquivo | O que é |
|---|---|
| `exploracao_eda_silver.ipynb` | EDA completa da camada Silver, em 6 fases — base do `docs/eda-consolidada.md` |
| `exploracao_viabilidade_equipe.ipynb` | Estudo que definiu o corte A/B/C do forecast por equipe (quais equipes têm volume para um modelo próprio) |
| `apoio_conexao_banco.ipynb` | Teste rápido de conexão com o banco `fiap` |

## Como rodar

```bash
# da raiz do repositório
jupyter nbconvert --to notebook --execute --inplace notebooks/etapa01_bronze_para_silver.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/etapa02_star_schema_dw.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/etapa03_feature_marts_ml.ipynb

python notebooks/etapa04_forecast_volume_total.py --fonte sql
python notebooks/etapa05_forecast_por_equipe.py --fonte sql
python notebooks/etapa06_pressao_por_equipe.py
python notebooks/etapa07_forecast_por_produto.py
python notebooks/etapa08_recorrencia_operacional.py

jupyter nbconvert --to notebook --execute --inplace notebooks/etapa09_clusters_kmeans.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/etapa10_risco_sla_xgboost.ipynb

python notebooks/etapa11_diagnostico_k_kmeans.py   # read-only
```

Conexão sempre via `etl/db.py` (credenciais em `.env`) — nenhum notebook
abre conexão própria nem tem credencial embutida.

## Arquivos locais não versionados

`mlflow.db`, `mlruns/` e `__pycache__/` são gerados pela execução e estão no
`.gitignore` — não fazem parte do repositório.
