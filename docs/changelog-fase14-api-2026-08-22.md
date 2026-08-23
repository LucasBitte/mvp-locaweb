# Changelog — Fase 14 (FastAPI), 2026-08-22

> Implementação do `PLAN.md` Fase 14 (API), cobrindo a lógica de dados das
> Fases 6-9/11 (Painel, Detalhe, KPI, Fatores, Alertas — Clusters não tinha
> lacuna material). Contrato de dados completo, endpoint a endpoint, em
> `docs/prds/etapa5-api.md` (reescrito por inteiro nesta rodada); este
> documento é o resumo do que mudou no código e o que foi encontrado
> auditando o banco `fiap` durante a implementação. **Nenhuma tabela,
> migration ou modelo de ML foi alterado/retreinado** — só código novo em
> `app/api/` e `tests/`.

## 1. O que foi construído

| Arquivo | Conteúdo |
|---|---|
| `app/api/deps.py` | `get_db_engine()` — engine cacheada (`lru_cache`) sobre `etl.db.get_engine()`, injetada via `Depends`. Única via de conexão, nenhum router abre engine própria. |
| `app/api/routers/painel.py` | `GET /api/painel` |
| `app/api/routers/detalhe.py` | `GET /api/detalhe` |
| `app/api/routers/kpi.py` | `GET /api/kpi` |
| `app/api/routers/fatores.py` | `GET /api/fatores` |
| `app/api/routers/clusters.py` | `GET /api/clusters` |
| `app/api/routers/alertas.py` | `GET /api/alertas` |
| `app/api/main.py` | Registra os 6 routers (`include_router`), mantém `GET /health` |
| `tests/test_api_<tela>.py` | 25 testes de contrato novos (+ 13 já existentes = 38 no total), rodam contra o banco `fiap` real, só `SELECT` |

Convenções seguidas (mesmas de `docs/prds/etapa5-api.md`): SQL raw via
`sqlalchemy.text()`, sem ORM; um `pydantic.BaseModel` por endpoint como
`response_model`; toda tabela `ml.fct_*`/`dw.fct_recorrencia_operacional` é
lida filtrando sempre pela execução mais recente (`MAX(origem)` ou
`MAX(data_execucao)`), nunca misturando execuções.

## 2. Endpoints — resumo

| Endpoint | Fonte principal | Ponto de atenção |
|---|---|---|
| `GET /api/painel` | `ml.fct_previsao_diaria_total`/`_prioridade` + `ml.fct_pressao_equipe` | `pressao_equipes` (pressão por equipe, Fase 3) não existia no PRD original — adicionado nesta rodada |
| `GET /api/detalhe` | `ml.fct_previsao_prioridade` + `ml.fct_previsao_categoria`/`_produto` + `dw.fct_recorrencia_operacional` | Novo query param `agrupamento` (`categoria`\|`produto`, Fase 4); bloco `recorrencia` novo (Fase 5) |
| `GET /api/kpi` | `dw.ref_meta_sla_anual` + `etl.ref_meta_sla.faixa_meta_sla()` | Reescrito do zero — a tabela é real (24 linhas, faixas), não mais o placeholder de 2 linhas do PRD original; **só retorna P2/P3**, nunca P1/P4 |
| `GET /api/fatores` | `ml.fct_importancia_conceito` (fallback `_feature`) + `ml.fct_shap_incidente` | Sem mudança de contrato — um bug de implementação foi corrigido (ver §4) |
| `GET /api/clusters` | `ml.fct_perfil_cluster` join `ml.dim_cluster` | Campo `taxa_sla_violado_pct` renomeado para `taxa_excedeu_tempo_esperado_pct` + `nota_metrica_sla` no payload (ver §3) |
| `GET /api/alertas` | Combina painel/detalhe/clusters | Catálogo de 5 regras (Fase 11); `pico_volume_d1`/`concentracao_categoria` sempre presentes (baseline informativo); as outras 3 só aparecem quando a condição é satisfeita |

Contrato completo (JSON de exemplo, critérios de aceite, query params) por
endpoint: `docs/prds/etapa5-api.md` §4.1-§4.6.

## 3. Achados de auditoria (checkpoint humano, nada alterado no banco)

Dois achados apareceram ao verificar os dados reais ao vivo durante a
implementação — nenhum é um bug introduzido nesta rodada, ambos já existiam
nos dados/artefatos; só não estavam documentados.

### 3.1 Métrica de "violação" do cluster tinha dois significados diferentes

`ml.fct_perfil_cluster.taxa_sla_violado_pct` é calculada em
`model_clustering_kmeans_Revisado.ipynb` a partir de `excedeu_tempo_esperado`
(duração > threshold da prioridade) — **94-98% em todos os 4 clusters** no
banco real. O indicador oficial de SLA (`kpi_status_int=1`, o mesmo usado
corretamente na tela KPI) dá **0,95%** no banco inteiro — duas definições de
"violação" com ordens de grandeza de distância. Se a API expusesse o nome
`taxa_sla_violado_pct` sem qualificação, a tela Clusters contradiria
diretamente a tela KPI.

**Decisão (aprovada pelo usuário durante esta sessão)**: expor o campo como
está, sem retreinar nem alterar `ml.fct_perfil_cluster`, mas renomeado no
payload da API para `taxa_excedeu_tempo_esperado_pct` + uma nota fixa
(`nota_metrica_sla`) explicando a diferença em toda resposta de
`/api/clusters`.

### 3.2 Taxonomia curada de `ml.dim_cluster` diverge das métricas reais

`ml.dim_cluster` (nomes/descrições/tags, curados manualmente na migration
`018`, não recalculados a cada execução do K-Means) contradiz as métricas
reais de `ml.fct_perfil_cluster` em pelo menos 2 dos 4 clusters:

- **Cluster B** — rotulado `"Recorrentes rápidos"` / `"Alta frequência ·
  Curta duração"`, mas tem a **maior** `duracao_media_horas` real dos
  quatro clusters (198,3h).
- **Cluster D** — rotulado `"Baixo impacto"` / `"Curta duração · Rotineiros
  · Sem violações"`, mas tem a **maior** `taxa_excedeu_tempo_esperado_pct`
  (98,0%) e a 2ª maior duração (93,8h) — a descrição diz literalmente "sem
  violações" para o cluster com mais excesso de tempo esperado dos quatro.

Não é um bug de código — é conteúdo curado que ficou desatualizado (a
migration registra que veio do mockup original e nunca foi revisada após
retreinos do K-Means). **Não corrigido nesta etapa**: reescrever
`nome_perfil`/`descricao_curta`/`tags` é decisão de conteúdo/produto, fora
do escopo de uma implementação de API. Registrado como novo item do
`PLAN.md` Anexo A.3/A.4 — checkpoint humano pendente antes de a tela
Clusters ir ao ar com dado real.

## 4. Bug encontrado e corrigido durante os testes

`GET /api/fatores` aplicava `LIMIT 30` **por linha** na query de
`ml.fct_shap_incidente`, mas essa tabela já tem grão incidente×feature
(~7 linhas por incidente — a seleção do top-30 já acontece na origem, a
tabela só é populada com esses incidentes). O `LIMIT 30` por linha cortava
no meio de um incidente e devolvia só ~4 incidentes distintos em vez de 30.
Corrigido: o filtro é só por `data_execucao` (sem `LIMIT`), confirmado por
teste (`tests/test_api_fatores.py`) que os 210 registros = 30 incidentes
distintos × 7 features.

## 5. O que NÃO mudou

- Nenhuma tabela, migration ou modelo de ML foi alterado ou retreinado.
- `ml.dim_cluster`, `ml.fct_perfil_cluster` e demais saídas de modelo:
  intocadas (achados de §3 são só documentados, não corrigidos no banco).
- `app/web/` (React): continua consumindo `dashboardData.ts` estático —
  religar as 6 telas aos endpoints novos é o próximo passo, não feito nesta
  rodada.
- `requirements.txt`/`requirements-notebooks.txt`: intocados (pin de versão
  continua pendente, Anexo A/ML-3).

## 6. Como rodar

```bash
cd app/api && ../../venv/bin/uvicorn app.api.main:app --reload   # a partir da raiz do repo
# ou, a partir da raiz do repo:
./venv/bin/uvicorn app.api.main:app --reload --app-dir .

./venv/bin/python3 -m pytest tests/ -q   # 38 testes, inclui os 6 novos test_api_<tela>.py
```
