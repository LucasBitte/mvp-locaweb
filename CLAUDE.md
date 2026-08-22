# CLAUDE.md

> Lido automaticamente pelo Claude Code no início de cada sessão neste repositório.
> Mantido denso de propósito — atualize a seção 10 sempre que um erro por falta de
> contexto acontecer, e a seção 9 sempre que uma etapa mudar de status.

## 1. O que é este projeto

Pipeline de dados fim a fim para um dashboard de **AIOps de incidentes de TI**
(Desafio Locaweb/FIAP). Fluxo: tabela bruta no Postgres → camada Silver →
modelo dimensional (star schema) → feature marts → 4 modelos de ML (previsão
de volume total e por equipe, clustering, risco de SLA) → API FastAPI →
dashboard React.

- Repo: [LucasBitte/mvp-locaweb](https://github.com/LucasBitte/mvp-locaweb) — branch `main` protegida, exige PR.
- Local: `/home/fiap/mvp-locaweb`
- Dashboard-alvo: 6 telas — Painel, Detalhe, KPI, Fatores, Clusters, Alertas — já implementadas como React real em `app/web/src/components/screens/` (2026-08-22), com dado estático/exemplo (mesmos números reais das Fases 1-13) até a Etapa 5 (API) existir. O mockup original (`docs/design/aiops_dashboard_redesign.html`) foi removido do repo; a referência de design agora é o projeto Claude Design "AIOps Dashboard.dc.html" (`claude.ai/design/p/63defcd6-35eb-4d1e-983f-a73f61be15d2`), importado via `DesignSync`/`/design-login`.
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
python notebooks/pressao_equipe.py                    # depende do passo anterior (le ml.fct_previsao_grupo)
python notebooks/forecast_produto.py                  # depende de forecast_incidentes_revisado.py (le ml.fct_previsao_diaria_total)
python notebooks/recorrencia.py                       # independente — le direto de dw.fct_incidentes
jupyter nbconvert --to notebook --execute --inplace notebooks/model_clustering_kmeans_Revisado.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/model_risk_xgboost_.ipynb
python notebooks/diagnostico_kmeans_k.py               # read-only, nao altera ml.dim_cluster/fct_perfil_cluster

# testes
./venv/bin/pytest tests/

# dashboard React (app/web/) — 6 telas já implementadas, dado estático por enquanto
cd app/web && npm install && npm run dev     # http://localhost:5173
cd app/web && npm run build                  # tsc -b && vite build
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
                                   ▼  forecast / forecast por equipe / clustering / xgboost
                              ml.fct_*   (saídas dos modelos)
```

4 schemas no banco `fiap`: `public` (bronze), `staging` (silver),
`dw` (star schema p/ BI/API), `ml` (features + saídas de modelo).

- `dw.fct_incidentes`: grão **1 linha = 1 incidente** (41.441 linhas), filtrado a `status <> 'Sem Intervenção'` e `aberto >= 2025-01-01`. 6 dimensões: produto_categoria, grupo, tempo, status, prioridade, abertura.
- `ml.ml_base_features`: 1 linha/incidente, 40 colunas.
- `ml.ml_cluster_dataset` e `ml.ml_sla_classification_dataset`: 1 linha/incidente, **leakage-free**.
- `ml.ml_forecast_dataset`: 1 linha/dia, 365 linhas.

Documentação completa: [`docs/dicionario-dados.md`](docs/dicionario-dados.md) (coluna a coluna) e [`docs/modelo-dimensional.md`](docs/modelo-dimensional.md) (raciocínio do star schema).

## 4. Os 4 modelos de ML — o que cada um faz

| Modelo | Lê de | Grava em | Cobertura |
|---|---|---|---|
| Prophet (forecast) | `ml.ml_forecast_dataset` | `ml.fct_previsao_diaria_total/_prioridade/_categoria` | D+1..D+7, append por execução |
| Prophet por equipe (forecast) | `ml.ml_base_features` (roda depois do forecast total, mesma origem) | `ml.fct_previsao_grupo` | D+1..D+7, 16 equipes, append por execução — arquitetura híbrida A/B/C, ver `docs/modelo-dimensional.md` |
| K-Means (clusters) | `ml.ml_cluster_dataset` | `ml.dim_cluster` (4 clusters, seed manual) + `ml.fct_perfil_cluster` | 41.441 incidentes clusterizados |
| XGBoost + SHAP (risco) | `ml.ml_sla_classification_dataset` + `ml.ml_base_features` | `ml.fct_importancia_feature`, `ml.fct_risco_incidente`, `ml.fct_shap_incidente` | 41.441 incidentes com score; SHAP nos 30 de maior risco |

**Limitações de escopo que não podem virar mal-entendido em código futuro:**
- Forecast por prioridade/categoria é **proporção histórica** sobre o total previsto — não é um modelo treinado por corte. Não tratar como se fosse.
- `ml.fct_shap_incidente` explica os incidentes de maior risco individualmente, **não** o volume previsto do dia seguinte — não confundir as duas explicabilidades ao construir a tela "Fatores".
- Metas de OLA da tela KPI: `dw.ref_meta_sla_anual` **já existe e tem dado real** (Dicionário de Dados oficial do desafio, não placeholder do mockup) — 24 linhas, faixas por prioridade/indicador. Lookup em `etl/ref_meta_sla.py::faixa_meta_sla()`.

**Lacunas fechadas em 2026-08-22 (PLAN.md Fases 1-5/10/12/13 — detalhes lá):**
- Default analítico das telas Painel/Detalhe/Alertas = **P2 + P3** (78,9% do volume real, validado). Threshold de SLA sempre de `dw.dim_prioridade.threshold_sla_horas` (P2=4h/P3=12h, corrigido em 2026-08-21).
- Pressão operacional por equipe: `ml.fct_pressao_equipe` (migration 026, script `notebooks/pressao_equipe.py`) — `pressao_relativa_pct = ((yhat_previsto - media_historica_diaria) / media_historica_diaria) * 100` contra o próprio histórico da equipe. **Nunca** é capacidade real, headcount ou saturação contratual.
- Split por produto: `ml.fct_previsao_produto` (migration 027, script `notebooks/forecast_produto.py`) — mesma técnica de proporção histórica de `fct_previsao_categoria`.
- Recorrência: `dw.fct_recorrencia_operacional` (migration 028, script `notebooks/recorrencia.py`) — janela móvel 30d vs. 30d anteriores, 4 granularidades (produto/categoria/produto+categoria/categoria+subcategoria); classificação combina volume com regularidade (`cobertura_dias_atual_pct`), não é só "volume alto".
- K-Means: diagnóstico `k=2..8` executado (read-only, `notebooks/diagnostico_kmeans_k.py`) — **sem vencedor claro** (silhouette máximo em k=2, Davies-Bouldin mínimo em k=8); `k=4` em produção fica em posição intermediária, sem defesa estatística forte nem motivo para trocar. PCA(n_components=3) confirmado explicando só **39,95%** de variância (comentário do notebook dizia "95%") — não corrigido (mudaria o modelo em produção; checkpoint humano). Ver `docs/metricas-validacao.md`.
- EDA formal: `docs/eda-consolidada.md`. Métricas de validação consolidadas (Prophet/XGBoost/K-Means, com 3 achados que exigem decisão humana — Prophet não bate o baseline simples, XGBoost não atinge a meta de AUC-ROC 0,85, K-Means sem k ótimo claro): `docs/metricas-validacao.md`.

**Dashboard React implementado (2026-08-22, fora da numeração de fases do PLAN.md — adiantado a pedido):**
- As 6 telas (`app/web/src/components/screens/`) foram portadas 1:1 do projeto Claude Design
  "AIOps Dashboard.dc.html" (`claude.ai/design/p/63defcd6-35eb-4d1e-983f-a73f61be15d2`), importado via
  `DesignSync`/`/design-login`. Fidelidade visual confirmada rodando os 6 tabs num Chromium headless
  (Playwright) — zero erros de console, `tsc -b` e `npm run build` limpos.
- Dado ainda **estático** (`src/data/dashboardData.ts`) — mesmos números reais das Fases 1-13 desta
  sessão (pressão por equipe, recorrência, splits P2/P3 e produto, faixas de meta, SHAP, clusters),
  não fabricados, mas fixos até a Etapa 5 existir. Selo do header diz "DADOS DE EXEMPLO · FASE 15",
  nunca "mockup"/dado real — não remover esse selo antes de existir uma API de verdade por trás.
- Cada tela chama funções `computeXxx()` puras em `dashboardData.ts` — quando a Etapa 5 (API) existir,
  a troca é só essas chamadas por `fetch`/hooks; o JSX das telas não muda.

**API FastAPI implementada (2026-08-22, PLAN.md Fases 6-9/11/14):**
- 6 endpoints reais em `app/api/routers/` (`painel`, `detalhe`, `kpi`, `fatores`, `clusters`,
  `alertas`), registrados em `app/api/main.py`, lendo do banco `fiap` via `etl.db.get_engine()`
  (`app/api/deps.py`). Contrato de dados completo, endpoint a endpoint: `docs/prds/etapa5-api.md`.
  Testes de contrato em `tests/test_api_<tela>.py` (rodam contra o banco real, só `SELECT`,
  mesmo padrão de `tests/test_api.py`) — `./venv/bin/python3 -m pytest tests/` (38 testes, ✅).
- **Ainda não religado ao frontend** — `app/web/` continua consumindo `dashboardData.ts`
  estático; a troca é substituir as chamadas `computeXxx()` por `fetch` nas 6 telas (Fase 15
  do `PLAN.md`, não feita nesta rodada).
- **2 achados de auditoria confirmados ao vivo contra o banco, documentados em
  `docs/prds/etapa5-api.md` §4.5** (checkpoint humano, nada retreinado/alterado no banco):
  1. `ml.fct_perfil_cluster.taxa_sla_violado_pct` usa `excedeu_tempo_esperado` (94-98% no
     banco todo), não o indicador oficial de SLA (`kpi_status_int`, 0,95% no banco todo) —
     campo exposto pela API como `taxa_excedeu_tempo_esperado_pct` com nota explicativa no
     payload, nunca como "SLA" sem qualificação.
  2. `ml.dim_cluster` (taxonomia curada manualmente) diverge das métricas reais de pelo
     menos 2 dos 4 clusters (cluster B rotulado "curta duração" mas com a maior
     `duracao_media_horas` real; cluster D rotulado "sem violações" mas com a maior
     `taxa_excedeu_tempo_esperado_pct`) — não corrigido (decisão de conteúdo, não de
     código); candidato a novo item do `PLAN.md` Anexo A.

**Pin de versões:**
- Pin de versões em `requirements.txt`/`requirements-notebooks.txt` (checkpoint humano, Anexo A/ML-3) — ainda em aberto.

## 5. Estrutura do repositório

```
mvp-locaweb/
├── db/migrations/     # DDL versionado (025 migrations já aplicadas)
├── etl/                # db.py (conexão via .env), transform.py (bronze -> dw, standalone), ref_meta_sla.py (lookup de faixa de meta)
├── notebooks/          # 01-06 (pipeline) + os 4 modelos de ML + conexao_banco_fiap.ipynb
├── app/api/             # FastAPI — esqueleto, ainda não construído (Etapa 5)
├── app/web/              # React + Vite + Tailwind — 6 telas implementadas (dado estático, Etapa 6 parcial)
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
- Editar uma migration já aplicada (das 025 existentes) — sempre criar uma nova.
- Alterar `.env` ou qualquer credencial do banco `fiap`.
- Rodar `DROP`/`TRUNCATE` ou qualquer operação destrutiva contra o banco `fiap` (é o banco real do projeto, não há banco de "teste" separado documentado).

## 9. Status por etapa (fonte de verdade — atualizar aqui, não em conversa)

| Etapa | O quê | Status |
|---|---|---|
| 0-1 | Setup do repo + inspeção do schema bruto | ✅ |
| 2 | Modelo dimensional (`dw.*`) | ✅ |
| 3 | Marts de features (`ml.ml_*`) | ✅ |
| 4 | Modelos de ML rodando contra o banco + output real (`ml.fct_*`) | ✅ |
| 5 | API FastAPI — 6 endpoints implementados e testados contra o banco real (`app/api/routers/`) | 🟡 (falta religar o frontend) |
| 6 | Dashboard React — 6 telas implementadas, consumindo dado estático (aguarda religar na Etapa 5 para dado real) | 🟡 |

> Antes de iniciar a Etapa 5, ver `PLAN.md` — plano de fechamento de lacunas
> frente ao desafio (P2/P3 default, pressão por equipe, recorrência, EDA
> formal, métricas de validação consolidadas, diagnóstico de k do K-Means)
> mais o anexo de governança/QA de ML (Agent Skills).

## 10. Erros recorrentes já corrigidos (adicionar aqui sempre que acontecer de novo)

- **Detector de "quebra de patamar" (`validar_serie`, `notebooks/forecast_incidentes_revisado.py`) pode apontar o último dia da série.** Em séries mais curtas/ruidosas que o total (ex.: forecast por equipe), a razão de medianas móveis de 28 dias pode disparar bem perto do fim da série. Se usada sem checagem, `inicio_treino` fica tão perto do fim que não sobra runway para a 1ª origem do backtest (45 dias) + horizonte (7 dias) → backtest vazio → `AttributeError: 'DataFrame' object has no attribute 'yhat'`. Corrigido em `notebooks/forecast_equipe.py` (`RUNWAY_MINIMO_DIAS`): só aplica a quebra detectada se sobrar pelo menos 52 dias até o fim da série; senão ignora e usa o histórico completo. Qualquer novo uso de `validar_serie`/`quebras_de_patamar_detectadas` num script novo precisa da mesma guarda.

## 11. Onde procurar mais contexto

- Dicionário de dados: `docs/dicionario-dados.md`
- Raciocínio do modelo dimensional: `docs/modelo-dimensional.md`
- Forecast por equipe (`ml.fct_previsao_grupo`, arquitetura A/B/C): `docs/forecast-por-equipe.md`
- Plano de fechamento de lacunas do desafio (fases, matriz das 6 telas, anexo de governança de ML): `PLAN.md`
- EDA consolidada (8 evidências, Achado/Impacto/Decisão): `docs/eda-consolidada.md`
- Métricas de validação consolidadas (Prophet/XGBoost/K-Means, com achados que exigem decisão humana): `docs/metricas-validacao.md`
- Changelog das Fases 1-5/10/12/13 (tabelas novas, resultados reais): `docs/changelog-fechamento-lacunas-2026-08-22.md`
- Changelog da Fase 14 (API FastAPI — endpoints, achados de auditoria, bug do SHAP corrigido): `docs/changelog-fase14-api-2026-08-22.md`
- Dashboard React (6 telas, dado estático): `app/web/src/components/screens/` — dados em `app/web/src/data/dashboardData.ts`; design de origem no projeto Claude Design "AIOps Dashboard.dc.html" (`claude.ai/design/p/63defcd6-35eb-4d1e-983f-a73f61be15d2`)
- API FastAPI (6 endpoints, dado real): `app/api/routers/` + contrato completo em `docs/prds/etapa5-api.md`; testes em `tests/test_api_*.py`

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
*Última atualização: 2026-08-22 (dashboard React das 6 telas implementado).*
