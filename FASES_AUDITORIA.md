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
| 2.2 | Validação SHAP base_value | ⏳ BLOQUEADO (requer notebook) | — |
| 2.3 | Renomear taxa_sla_violado_pct | ⏳ PENDENTE | — |
| 3.1 | Modelos Pydantic + router /api/painel | ✅ COMPLETA (com fixes) | 2026-08-23 |
| 3.2 | Routers /api/detalhe, /fatores, /clusters, /kpi, /alertas | ⏳ EM PROGRESSO | — |
| 4 | Nova arquitetura visual (6 telas redesenhadas) | ⬜ | — |
| 5 | Integração (religar as 6 telas às APIs) | ⬜ | — |
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

---

### ⏳ PENDENTES / BLOQUEADAS

**Fase 2.2 — Validação SHAP base_value**
- Status: BLOQUEADO — requer trabalho no notebook `model_risk_xgboost_.ipynb`
- Necessário: confirmar o que TreeExplainer explica (saída bruta vs. calibrada)
- Checklist documentado em `FASE2_RECOMENDACOES.md`

**Fase 2.3 — Renomear taxa_sla_violado_pct**
- Status: PENDENTE
- Necessário: migration + grep de scripts que referem a coluna
- Alvo: eliminar ambiguidade semântica (excedência vs. OLA)

**Fases 4-8 (Frontend + QA)**
- Fase 4: Nova arquitetura visual (6 telas React)
- Fase 5: Integração (religar UI à API)
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

---

## Próximas Ações Prioritárias

1. **Fase 2.2+2.3** (antes de Fase 4)
   - [ ] Revisar notebook XGBoost (base_value)
   - [ ] Criar migration para renomear coluna
   - [ ] Grep + update de scripts referentes

2. **Fase 4** (Frontend — pode rodar em paralelo)
   - [ ] Implementar 6 telas React (Sobre, Visão Estratégica, Forecast, Risco, Perfis, Ações)
   - [ ] Consumir endpoints da API via cliente TypeScript

3. **Fase 5** (Integração)
   - [ ] Migrar dados de `ml_dev.*` para `ml.*` (produção)
   - [ ] Validação ponta-a-ponta

4. **Fases 6-8** (QA + Aceite)
   - [ ] Testes de contrato (schema, tipos)
   - [ ] Revisão visual (densidade, nomenclatura)
   - [ ] Checklist do PLAN.md

---
*Última atualização: 2026-08-23 — Em produção: branch `dev` com 6 commits consolidados.*
