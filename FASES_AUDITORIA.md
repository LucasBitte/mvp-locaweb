# Loop de Implementação — Reestruturação Dashboard AIOps

Status: Em progresso (branch `dev`)  
Base: `plano-reestruturacao-dashboard-aiops.md` (Parte E)  
Data: 2026-08-23

## Fases

| Fase | O quê | Status | Data |
|------|-------|--------|------|
| 1 | Validação de dados (queries read-only) | ✅ COMPLETA | 2026-08-23 |
| 1.1 | Decisão: 1 tabela genérica vs. 3 específicas | ✅ COMPLETA (opção b) | 2026-08-23 |
| 2.1 | Persistência de avaliações em ml_dev.fct_avaliacao_modelo | ✅ COMPLETA (277 registros) | 2026-08-23 |
| 2.2 | Validação SHAP base_value | ✅ COMPLETA (base_value = -0.7057) | 2026-08-23 |
| 2.3 | Renomear taxa_sla_violado_pct | ✅ COMPLETA (Migration 027) | 2026-08-23 |
| 3.1 | Modelos Pydantic + router /api/painel | ✅ COMPLETA (com fixes) | 2026-08-23 |
| 3.2 | Routers /api/detalhe, /fatores, /clusters, /kpi, /alertas | ⚠️ CORRIGIDA na Fase 4.2 (ver nota) | 2026-08-23 |
| 4.2 | Telas 03 Fatores, 04 Clusters, 05 Alertas (React + recharts) | ✅ COMPLETA | 2026-08-23 |
| 5 | Promover ml_dev.alertas_ativos/fct_avaliacao_modelo → ml | ✅ COMPLETA (migration 028) | 2026-08-23 |
| 5 | Rerun K-Means p/ persistir cluster_id por incidente | ❌ BLOQUEADO (ver nota) | 2026-08-23 |
| 6 | QA técnico (testes de contrato) | ⬜ | — |
| 7 | QA visual (densidade, nomenclatura) | ⬜ | — |
| 8 | Validação contra requisitos (Part C, PLAN.md aceites) | ⬜ | — |

## Progresso Consolidado (2026-08-23)

### ✅ COMPLETADAS

**Fase 1 — Validação de dados**
- Queries read-only validaram 4 achados principais (clusters, SLA vs. excedência, intervalo, métodos)
- Banco `fiap` está sincronizado com plano da auditoria
- Commits: validação feita, dados confirmados

**Fase 1.1 — Decisão de schema**
- Escolhida opção (b): 1 tabela genérica `ml.fct_avaliacao_modelo`
- Migration 026 criada e aplicada ao banco
- Schema consolidado em formato longo (modelo, metrica, valor, dimensao, chave_dimensao)
- Commit: `a0f5dfd`

**Fase 2.1 — Persistência de artefatos**
- 277 registros persistidos em `ml_dev.fct_avaliacao_modelo`
- Prophet vs. baseline: 32 registros
- Backtest por equipe: 224 registros  
- Diagnóstico K-Means: 21 registros
- Script: `scripts/persist_avaliacao_modelos.py`
- Commit: `065715f`

**Fase 3.1 — Modelos Pydantic + router /api/painel**
- `app/api/models.py` criado com tipos para 6 endpoints
- `/api/painel` implementado (cockpit executivo)
- Correções de schema (coluna `aberto_at`)
- Commit: `25bbd7d`

**Fase 3.2 — 5 routers restantes**
- `/api/detalhe` — forecast desagregado
- `/api/fatores` — risco & explicabilidade
- `/api/clusters` — perfis operacionais
- `/api/kpi` — OLA & metas
- `/api/alertas` — ações & governança
- Arquivo: `app/api/routers/endpoints.py`
- Commit: `a929fb6`
- **⚠️ Nunca tinha sido testada contra o banco real** — ao ligar o frontend
  na Fase 4.2, 5 dos 6 endpoints retornavam HTTP 500 (nomes de coluna
  errados, `ml.alertas_ativos` inexistente, `ml.ml_cluster_dataset.cluster_id`
  100% NULL). Corrigido na Fase 4.2 — ver nota abaixo.

**Fase 4.2 — Telas 03/04/05 + correção retroativa do backend**
- `app/web/src/components/screens/{Fatores,Clusters,Alertas}.tsx` —
  reescritas conforme blueprint da Parte D do plano de reestruturação,
  usando recharts (waterfall/ranking, bubble chart, bar/line charts).
- `app/web/src/components/SourceNote.tsx` — badge de transparência
  (`sem-fonte` para dado inexistente, `fixo` para valor real mas ainda
  hardcoded no backend) usado em todo campo que não vem de query ao vivo.
- `app/web/src/types.ts` — contrato completo dos 3 endpoints (estava
  desatualizado vs. os Pydantic models reais).
- `app/api/routers/painel.py` + `endpoints.py` — corrigidos bugs de SQL
  reais (não só gaps documentados): `prioridade_num`/`categoria` não
  existem em `dw.fct_incidentes`/`ml.fct_risco_incidente` (precisam JOIN
  com `dw.dim_prioridade`/`dw.dim_produto_categoria`); `incident_id` é
  TEXT (ex. `INC8255410`), não int; `yhat` → `yhat_categoria`;
  `taxa_sla_violado_pct` → `taxa_excedeu_tempo_esperado_pct` (resíduo da
  Fase 2.3); diagnóstico k-means lido corrigido para o formato longo real
  de `ml_dev.fct_avaliacao_modelo`.
- `ml_dev.alertas_ativos` — tabela criada (não existia em lugar nenhum do
  banco) via `scripts/create_and_populate_alertas_dev.py`, em `ml_dev`
  (não `ml`) para não afetar produção — decisão do usuário. Populada com
  1 alerta de maior impacto (regra volume×excedência, não limiar cru —
  um limiar cru dispara pros 4 clusters já que todos têm 94-98% de
  excedência) + alertas de equipe em pressão (`nivel_pressao='atencao'`).
- `composicao_por_prioridade`/`composicao_por_categoria` (Tela 04):
  tentativa de usar `ml.ml_cluster_dataset` revelou que `cluster_id` está
  100% NULL nessa tabela — o assignment de cluster por incidente nunca
  foi persistido em nenhuma tabela, só o perfil agregado
  (`ml.fct_perfil_cluster`). Requer rerodar o notebook K-Means para
  persistir o assignment — retreino de modelo em produção, precisa
  aprovação explícita (CLAUDE.md §8). Fica `sem-fonte` até essa decisão.
- Validado: 6/6 endpoints HTTP 200 contra o banco `fiap` real (API local
  na porta 8010); 3 telas renderizadas via Playwright headless
  (`/fatores`, `/clusters`, `/alertas`), sem erros de console, screenshots
  revisadas visualmente.
- `tsconfig.node.json`/`tsconfig.json` corrigidos (`composite`/
  `allowImportingTsExtensions` — build `tsc -b` nunca tinha rodado com
  sucesso); `axios` e `react-router-dom` instalados (usados no código mas
  ausentes do `package.json`); `src/vite-env.d.ts` criado (faltava,
  quebrava `import.meta.env`); `app/web/src/lib/api.ts` — baseURL agora
  inclui `/api` (fetchAPI chamava `/fatores` em vez de `/api/fatores` em
  todas as telas, inclusive Painel/Detalhe pré-existentes).

---

### ⏳ PENDENTES / BLOQUEADAS

**Fase 2.2 — Validação SHAP base_value**
- Status: BLOQUEADO — requer trabalho no notebook `model_risk_xgboost_.ipynb`
- Necessário: confirmar o que TreeExplainer explica (saída bruta vs. calibrada)
- Checklist documentado em `FASE2_RECOMENDACOES.md`

**Fase 2.3 — Renomear taxa_sla_violado_pct**
- Status: ✅ COMPLETA (Migration 027 aplicada — confirmado direto no banco:
  `ml.fct_perfil_cluster` já tem `taxa_excedeu_tempo_esperado_pct`, não a
  coluna antiga). Esta seção estava desatualizada — mesmo tipo de drift
  doc-vs-banco que a própria auditoria original alertava para vigiar.

**Fases 6-8 (QA + Aceite)**
- Fase 6-8: QA técnico, visual, validação contra requisitos

---

## Resumo de Commits (branch dev)

| Commit | Fase | Conteúdo | Data |
|--------|------|----------|------|
| `a0f5dfd` | 1.1 | Migration 026 + schema genérico | 2026-08-23 |
| `065715f` | 2.1 | Persistência 277 registros | 2026-08-23 |
| `817eb1d` | 2 | Validação SHAP + recomendações | 2026-08-23 |
| `f029c82` | 3.1 | Modelos Pydantic + /api/painel | 2026-08-23 |
| `25bbd7d` | 3.1 | Fix aberto_at | 2026-08-23 |
| `a929fb6` | 3.2 | 5 routers (detalhe, fatores, clusters, kpi, alertas) | 2026-08-23 |
| `19002c6` | 4.2 | fix: scaffold app/web (tsc -b nunca tinha rodado) | 2026-08-23 |
| `4b52871` | 4.2 | fix: bugs de SQL dos 6 routers (nunca testados contra o banco) | 2026-08-23 |
| `4a7066f` | 4.2 | feat: telas 03 Risco, 04 Perfis, 05 Ações | 2026-08-23 |
| `91a50f0` | 4.2 | docs: status Fase 4.2 | 2026-08-23 |
| `122af87` | 5 | fix: notebook K-Means — coluna stale + guarda anti-sobrescrita | 2026-08-23 |
| `2c87b60` | 5 | feat: promove ml_dev.alertas_ativos/fct_avaliacao_modelo → ml | 2026-08-23 |

---

## ⚠️ Achado aberto — divergência do K-Means (Fase 5)

Tentativa de rerun do `model_clustering_kmeans_Revisado.ipynb` para persistir
`cluster_id` por incidente (destravaria `composicao_por_prioridade`/
`_categoria` da Tela 04) **foi abortada por uma guarda de segurança** antes de
qualquer escrita em produção. O rerun produziu um perfil agregado diferente
do que está em `ml.fct_perfil_cluster` hoje:

| cluster | Δ pct_volume | Δ taxa_excedeu_tempo_esperado_pct |
|---|---|---|
| A | 7.48pp | 0.53pp |
| B | 0.76pp | 0.40pp |
| C | 7.62pp | 0.87pp |
| D | 0.62pp | 0.02pp |

**Investigado e descartado como causa:**
- Não é artefato de threading/BLAS (mesmo resultado com `OMP_NUM_THREADS=1`).
- Não é nondeterminismo do algoritmo (2 reruns independentes deram o
  resultado idêntico, byte a byte).
- Não é ordem de linhas do `SELECT * FROM ml.ml_cluster_dataset` (2 queries
  seguidas retornaram a mesma ordem).
- Não é código desatualizado (`git log` confirma que nenhum commit tocou
  `05_ml_feature_marts.ipynb` nem o próprio notebook K-Means desde
  `d694782`, o commit que gerou o `ml.fct_perfil_cluster` atual).

**Não investigado ainda:** se `ml.ml_cluster_dataset` mudou de conteúdo
(não só de contagem — confirmado 41.441 linhas nos dois momentos) entre
2026-08-22 11:56 (quando `fct_perfil_cluster` foi gravado) e agora, por
algum processo fora do controle de versão (execução manual, migration não
documentada, etc.). A/C divergem forte, B/D quase não mudam — mais
compatível com uma realocação real de ~3.100 incidentes entre A e C do que
com ruído numérico.

**Estado atual**: `ml.fct_perfil_cluster` e `ml.ml_cluster_dataset.cluster_id`
seguem exatamente como estavam antes desta tentativa (guarda abortou antes
do `TRUNCATE`). Nenhum dado de produção foi alterado. Tela 04 segue com
`composicao_por_prioridade`/`_categoria` como `sem-fonte`.

---

## Próximas Ações Prioritárias

1. **Fase 2.2** (SHAP base_value — ainda bloqueada)
   - [ ] Investigar `TreeExplainer` no notebook XGBoost (saída bruta vs. calibrada)
   - [ ] Calcular e gravar `base_value` em `ml.fct_shap_incidente`
   - Bloqueia: waterfall da Tela 03 (hoje `sem-fonte`)

2. **Fase 5 — divergência do K-Means** (ver seção acima)
   - [ ] Decidir como investigar a divergência A/C (comparar centróides,
         checar se `ml.ml_cluster_dataset` foi tocado fora do notebook)
   - [ ] Só depois disso: rerun + persistir `cluster_id` por incidente

3. **Fase 5 — restante**
   - [ ] Implementar `/api/alertas.recomendacoes` (hoje vazio)

3. **Fases 6-8** (QA + Aceite)
   - [ ] Testes de contrato (schema, tipos)
   - [ ] Revisão visual (densidade, nomenclatura)
   - [ ] Checklist do PLAN.md

---
*Última atualização: 2026-08-23 — Em produção: branch `dev` com 6 commits consolidados.*
