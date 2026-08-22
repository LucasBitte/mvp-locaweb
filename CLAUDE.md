# CLAUDE.md

> Lido automaticamente pelo Claude Code no início de cada sessão neste repositório.
> Mantido denso de propósito — atualize a seção 10 sempre que um erro por falta de
> contexto acontecer, e a seção 9 sempre que uma etapa mudar de status.

## 1. O que é este projeto

Pipeline de dados fim a fim para um dashboard de **AIOps de incidentes de TI**
(Desafio Locaweb/FIAP). Fluxo: tabela bruta no Postgres → camada Silver →
modelo dimensional (star schema) → feature marts → 3 modelos de ML (previsão
de volume, clustering, risco de SLA) → API FastAPI → dashboard React.

- Repo: [LucasBitte/mvp-locaweb](https://github.com/LucasBitte/mvp-locaweb) — branch `main` protegida, exige PR.
- Local: `/home/fiap/mvp-locaweb`
- Dashboard-alvo (mockup de referência): `docs/design/aiops_dashboard_redesign.html` — 6 telas: Painel, Detalhe, KPI, Fatores, Clusters, Alertas.
- Banco: Postgres, database `fiap`, credenciais via `.env` (não versionado).

## 2. Comandos essenciais

```bash
# setup
cp .env.example .env                                   # preencher FIAP_DB_*
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
./venv/bin/pip install -r requirements-notebooks.txt

# pipeline completo, NESTA ORDEM (migrations já aplicadas no banco fiap)
jupyter nbconvert --to notebook --execute --inplace notebooks/03_bronze_silver_transformacao.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/04_dw_star_schema.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/05_ml_feature_marts.ipynb
python notebooks/forecast_incidentes_revisado.py --fonte sql
python notebooks/forecast_equipe.py --fonte sql       # depende do passo anterior (mesma origem)
jupyter nbconvert --to notebook --execute --inplace notebooks/model_clustering_kmeans_Revisado.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/model_risk_xgboost_.ipynb

# testes
./venv/bin/pytest tests/
```

## 3. Arquitetura de dados (mapa mental)

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

4 schemas no banco `fiap`: `public` (bronze), `staging` (silver),
`dw` (star schema p/ BI/API), `ml` (features + saídas de modelo).

- `dw.fct_incidentes`: grão **1 linha = 1 incidente** (41.441 linhas), filtrado a `status <> 'Sem Intervenção'` e `aberto >= 2025-01-01`. 6 dimensões: produto_categoria, grupo, tempo, status, prioridade, abertura.
- `ml.ml_base_features`: 1 linha/incidente, 40 colunas.
- `ml.ml_cluster_dataset` e `ml.ml_sla_classification_dataset`: 1 linha/incidente, **leakage-free**.
- `ml.ml_forecast_dataset`: 1 linha/dia, 365 linhas.

Documentação completa: [`docs/dicionario-dados.md`](docs/dicionario-dados.md) (coluna a coluna) e [`docs/modelo-dimensional.md`](docs/modelo-dimensional.md) (raciocínio do star schema).

## 4. Os 3 modelos de ML — o que cada um faz

| Modelo | Lê de | Grava em | Cobertura |
|---|---|---|---|
| Prophet (forecast) | `ml.ml_forecast_dataset` | `ml.fct_previsao_diaria_total/_prioridade/_categoria` | D+1..D+7, append por execução |
| Prophet por equipe (forecast) | `ml.ml_base_features` (roda depois do forecast total, mesma origem) | `ml.fct_previsao_grupo` | D+1..D+7, 16 equipes, append por execução — arquitetura híbrida A/B/C, ver `docs/modelo-dimensional.md` |
| K-Means (clusters) | `ml.ml_cluster_dataset` | `ml.dim_cluster` (4 clusters, seed manual) + `ml.fct_perfil_cluster` | 41.441 incidentes clusterizados |
| XGBoost + SHAP (risco) | `ml.ml_sla_classification_dataset` + `ml.ml_base_features` | `ml.fct_importancia_feature`, `ml.fct_risco_incidente`, `ml.fct_shap_incidente` | 41.441 incidentes com score; SHAP nos 30 de maior risco |

**Limitações de escopo que não podem virar mal-entendido em código futuro:**
- Forecast por prioridade/categoria é **proporção histórica** sobre o total previsto — não é um modelo treinado por corte. Não tratar como se fosse.
- `ml.fct_shap_incidente` explica os incidentes de maior risco individualmente, **não** o volume previsto do dia seguinte — não confundir as duas explicabilidades ao construir a tela "Fatores".
- Metas de OLA da tela KPI (`dw.ref_meta_sla_anual`, a criar na Etapa 5) **ainda não têm fonte real** — usar os números do mockup como placeholder explícito, sinalizado como tal na UI, não como dado real.

## 5. Estrutura do repositório

```
mvp-locaweb/
├── db/migrations/     # DDL versionado (022 migrations já aplicadas)
├── etl/                # db.py (conexão via .env), transform.py (bronze -> dw, standalone)
├── notebooks/          # 01-05 (pipeline) + os 3 modelos de ML + conexao_banco_fiap.ipynb
├── app/api/             # FastAPI — esqueleto, ainda não construído (Etapa 5)
├── app/web/              # React + Vite + Tailwind + Recharts — esqueleto (Etapa 6)
├── docs/                # Documentação (dicionário de dados, modelo dimensional, design)
├── tests/                # pytest
└── data/                 # parquets locais (bronze/ml), gitignored
```

## 6. Convenções

- `main` protegida — nunca push direto, sempre PR.
- Branches: `feature/<descrição>`.
- Merge: squash-merge.
- Migrations: sempre versionadas em `db/migrations/`, nunca alterar uma já aplicada — criar nova.
- Conexão com banco sempre via `etl/db.py`, nunca hardcodar credencial em notebook.

## 7. O que o Claude Code PODE fazer sem perguntar

- Rodar notebooks do pipeline (na ordem da seção 2) e os scripts de modelo.
- Rodar `pytest tests/`.
- Criar branch `feature/<descrição>`.
- Editar dentro de `app/api/`, `app/web/`, `tests/`, `docs/`.

## 8. O que NUNCA fazer sem confirmação explícita

- `git push --force` ou push direto em `main`.
- Editar uma migration já aplicada (das 022 existentes) — sempre criar uma nova.
- Alterar `.env` ou qualquer credencial do banco `fiap`.
- Rodar `DROP`/`TRUNCATE` ou qualquer operação destrutiva contra o banco `fiap` (é o banco real do projeto, não há banco de "teste" separado documentado).
- Apresentar os placeholders de OLA (seção 4) como se fossem dados reais em qualquer entregável.

## 9. Status por etapa (fonte de verdade — atualizar aqui, não em conversa)

| Etapa | O quê | Status |
|---|---|---|
| 0-1 | Setup do repo + inspeção do schema bruto | ✅ |
| 2 | Modelo dimensional (`dw.*`) | ✅ |
| 3 | Marts de features (`ml.ml_*`) | ✅ |
| 4 | Modelos de ML rodando contra o banco + output real (`ml.fct_*`) | ✅ |
| 5 | API FastAPI servindo as 6 telas do mockup | ⬜ **próximo passo** |
| 6 | Dashboard React consumindo a API | ⬜ |

## 10. Erros recorrentes já corrigidos (adicionar aqui sempre que acontecer de novo)

- **Detector de "quebra de patamar" (`validar_serie`, `notebooks/forecast_incidentes_revisado.py`) pode apontar o último dia da série.** Em séries mais curtas/ruidosas que o total (ex.: forecast por equipe), a razão de medianas móveis de 28 dias pode disparar bem perto do fim da série. Se usada sem checagem, `inicio_treino` fica tão perto do fim que não sobra runway para a 1ª origem do backtest (45 dias) + horizonte (7 dias) → backtest vazio → `AttributeError: 'DataFrame' object has no attribute 'yhat'`. Corrigido em `notebooks/forecast_equipe.py` (`RUNWAY_MINIMO_DIAS`): só aplica a quebra detectada se sobrar pelo menos 52 dias até o fim da série; senão ignora e usa o histórico completo. Qualquer novo uso de `validar_serie`/`quebras_de_patamar_detectadas` num script novo precisa da mesma guarda.

## 11. Onde procurar mais contexto

- Dicionário de dados: `docs/dicionario-dados.md`
- Raciocínio do modelo dimensional: `docs/modelo-dimensional.md`
- Forecast por equipe (`ml.fct_previsao_grupo`, arquitetura A/B/C): `docs/forecast-por-equipe.md`
- Mockup do dashboard-alvo: `docs/design/aiops_dashboard_redesign.html`

## 12. Operações aprovadas e proibidas (todos os modos)

Vale para qualquer modo de permissão ativo (`default`, `acceptEdits` ou
`auto`) — não é uma relaxação específica de modo automático, é a rotina
esperada do projeto.

### Operações de rotina — não precisam de confirmação extra

- Criar/editar notebooks em `notebooks/`, seguindo a convenção de numeração
  já estabelecida (`0X_nome.ipynb` ou scripts `.py` paralelos, ex.
  `forecast_equipe.py`).
- Criar migrations em `db/migrations/`, seguindo a numeração sequencial e o
  estilo das migrations existentes (`015`-`021` etc.).
- Atualizar `docs/dicionario-dados.md` e `docs/modelo-dimensional.md` com
  novas seções, desde que sigam o estilo já usado (parágrafo + bullets,
  seções datadas quando aplicável).
- Rodar notebooks/scripts do pipeline já existentes contra o banco `fiap`
  em modo leitura ou append (ex. `python notebooks/forecast_*.py --fonte
  sql`), incluindo escrita em tabelas `ml.*` que já seguem o padrão
  append/DELETE-por-origem documentado.
- Criar branch de feature e abrir PR.
- Rodar linters, testes existentes, `git status`, `git diff`, `git log`.

### Sempre exige confirmação explícita, em qualquer modo

- Qualquer `DROP`, `TRUNCATE` ou `DELETE` sem cláusula `WHERE`/`origem`
  restritiva em tabelas dos schemas `dw` ou `ml`.
- Qualquer alteração em `dw.dim_prioridade`, `dw.fct_incidentes` ou
  qualquer coluna derivada de threshold de SLA — essa área já teve uma
  correção sensível em andamento (ver `docs/modelo-dimensional.md`,
  histórico de thresholds) e mudanças aqui não devem ser silenciosas.
- Push direto ou merge na branch `main` — protegida, só entra por PR com
  squash-merge, sempre.
- Qualquer comando que apague arquivos fora de `notebooks/`,
  `db/migrations/` ou `docs/` (ex. limpeza de diretórios, `rm -rf`, mesmo
  que pareça "arquivo temporário").
- Alterar credenciais, variáveis de ambiente, string de conexão do banco,
  ou qualquer arquivo de configuração de infraestrutura.
- Retreinar um modelo de ML já em produção (Prophet, K-Means, XGBoost) sem
  reportar antes o motivo e aguardar aprovação — mesmo que a mudança pareça
  decorrente de uma correção já aprovada (ex. correção de threshold pode
  ou não exigir retreino; isso é decisão a reportar, não a tomar sozinho).
- Misturar mais de uma mudança de escopo (ex. correção de bug + feature
  nova) no mesmo commit ou PR.

### Notas de contexto para o classificador (modo `auto`)

- Este é um projeto de desafio acadêmico (AIOps FIAP) com dado real de
  produção conectado — tratar o banco `fiap` com o mesmo cuidado de um
  ambiente produtivo, não como sandbox descartável.
- Toda tarefa relevante já chega com um prompt detalhado (arquivo `.md`
  separado, gerado previamente) contendo escopo, critérios de aceite e o
  que não fazer — seguir esse escopo à risca é a rotina esperada; sair dele
  é a exceção que deve gerar pergunta.

---
*Última atualização: 2026-08-22.*
