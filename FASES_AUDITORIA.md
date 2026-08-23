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

## Progresso

### Fase 1: Validação de dados ✅
- Queries read-only confirmaram 4 achados principais
- Banco está sincronizado com plano da auditoria
- Pronto para prosseguir

### Fase 1.1: Decisão de schema (INÍCIO)
- Opção (b) — 1 tabela genérica `ml.fct_avaliacao_modelo`
- Formato longo: `(modelo, modelo_versao, data_execucao, dimensao, chave_dimensao, metrica, valor, is_baseline, baseline_nome)`
- Cobrirá: Prophet-vs-baseline (#5), backtest por equipe (#14), diagnóstico k (#9)

Próximos passos:
1. Criar migration para `ml.fct_avaliacao_modelo`
2. Atualizar scripts de persistência (Prophet, K-Means)
3. Commit + push para `dev`

---
*Atualizar esta tabela após cada fase.*
