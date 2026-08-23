# Fase 2.2 e 2.3 — Recomendações e TODOs

Base: Plano de auditoria, Parte E (Fases 2-3)  
Status: Em progresso  
Data: 2026-08-23

## Fase 2.2 — Validação de SHAP base_value ⏳

### Achado #7 (Parte B, linha 108)
**Status**: ❌ Bloqueado — requer trabalho no notebook XGBoost

**O que precisa ser feito:**
1. Abrir `notebooks/model_risk_xgboost_.ipynb`
2. Na seção de SHAP, confirmar EXATAMENTE o que `TreeExplainer` explica:
   - É a saída **bruta** do XGBoost (log-odds pré-calibração)?
   - Ou já é a probabilidade **calibrada**?
3. Calcular `base_value` referente a essa MESMA saída (bruta ou calibrada)
4. Validar matematicamente: `base_value + Σshap_value == saída_bruta` (ou calibrada, conforme confirmado)
5. Gravar `base_value` em nova coluna de `ml.fct_shap_incidente`

**Por que é importante:**
- O waterfall da Tela 03 (Risco & Explicabilidade) depende dessa validação
- Risco de erro matemático ao mostrar a decomposição SHAP ao usuário
- Calibração deve ser visualizada como etapa **separada**, não embutida nas contribuições

**Próximas ações:**
- [ ] Investigar `TreeExplainer(model).shap_values()` no notebook
- [ ] Confirmar se usa `model.predict()` (saída bruta) ou `model.predict_proba()` (probabilidade)
- [ ] Calcular base_value em uma célula do notebook
- [ ] Validar com amostra: `suma(shap_value) + base_value == expected_output`
- [ ] Gravar em `ml_dev.fct_shap_incidente.base_value` (coluna a adicionar via migration)
- [ ] Reexecutar `scripts/validate_shap_base_value.py` para confirmar

---

## Fase 2.3 — Renomear/Esclarecer `taxa_sla_violado_pct` ⏳

### Achado #2 (Parte B, linha 103)
**Status**: ⚠️ Parcialmente corrigido

**O que já foi feito:**
- API renomeia a coluna no payload como `taxa_excedeu_tempo_esperado_pct`
- Frontend nunca usa a palavra "SLA" nesta tela

**O que ainda precisa:**
- Renomear a coluna **na origem** (banco) de `taxa_sla_violado_pct` → `taxa_excedeu_tempo_esperado_pct`
  - Atualmente em `ml.fct_perfil_cluster` (migration)
  - Motive: eliminar ambiguidade em qualquer camada (não só no payload)

- Atualizar scripts Python que leem a coluna:
  - `notebooks/alertas.py` ou similares (linha 103 diz que `alertas.py::cluster_alta_violacao` ainda lê a coluna crua)
  - Verificar qualquer outro script que ref `taxa_sla_violado_pct`

**Por que é importante:**
- Evitar confusão semântica ("violação de SLA" vs. "excedência de tempo esperado")
- SLA oficial está em `kpi_status_int` (0,95% do banco), não em `taxa_sla_violado_pct` (95%)
- Ambigüidade interna pode causar erro futuro ao fazer manutenção

**Próximas ações:**
- [ ] Criar migration que rename coluna em `ml.fct_perfil_cluster`
- [ ] Grep por `taxa_sla_violado_pct` em todo o código Python/notebooks
- [ ] Atualizar qualquer referência interna encontrada
- [ ] Verificar docstrings que mencionam "violação"
- [ ] Testar que a API ainda devolve o campo com nome correto (retrocompatibilidade)
- [ ] Commit desta mudança

---

## Resumo: O que foi concluído em Fase 2

✅ **Fase 2.1** — Persistência de 277 registros de avaliação em `ml_dev.fct_avaliacao_modelo`
  - Prophet vs. baseline: 32 registros
  - Backtest por equipe: 224 registros
  - Diagnóstico K-Means: 21 registros

⏳ **Fase 2.2** — Validação de SHAP (bloqueado — requer notebook)

⏳ **Fase 2.3** — Renomear `taxa_sla_violado_pct` (requer grep + migration)

---

## Próximo passo global

Após Fase 2 ser completada:
→ **Fase 3** — Camada de dados/API (estender contratos dos 6 endpoints)
