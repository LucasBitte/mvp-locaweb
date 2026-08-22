# Schema do banco `fiap` e cobertura do mockup

Este documento tem dois objetivos:

1. **Catálogo do schema** — visão executiva de todas as tabelas do banco `fiap`
   (schema, grão, volumetria, chave). Para a lista coluna-a-coluna completa, ver
   [`docs/dicionario-dados.md`](dicionario-dados.md) (verificado contra o banco
   real em 2026-08-21 — 100% de aderência, nenhuma tabela ou coluna divergente).
2. **Comparativo mockup vs dados reais** — para cada elemento visual das 6 telas
   de [`docs/design/aiops_dashboard_redesign.html`](design/aiops_dashboard_redesign.html),
   mapeia se já existe fonte de dado real, se precisa de cálculo na API, ou se
   ainda falta uma decisão/tabela. Construído consultando o banco `fiap` ao vivo
   (contagens e amostras abaixo são reais, não estimadas).

---

## Parte 1 — Catálogo de schema

### `public` (bronze)

| Tabela | Grão | Linhas | Chave |
|---|---|---|---|
| `incidentes` | 1 chamado | 122.543 | `numero` |

### `staging` (silver)

| Tabela | Grão | Linhas | Chave |
|---|---|---|---|
| `incidentes_silver` | 1 chamado (filtrado, pós-2025) | 41.441 | `Número` |

### `dw` (star schema)

| Tabela | Grão | Linhas | Chave |
|---|---|---|---|
| `dim_produto_categoria` | (produto, categoria, subcategoria) | 921 | `dim_produto_categoria_sk` |
| `dim_grupo` | equipe | 16 | `dim_grupo_sk` |
| `dim_tempo` | dia de calendário | 365 | `dim_tempo_sk` |
| `dim_status` | (status, código fechamento) | 35 | `dim_status_sk` |
| `dim_prioridade` | nível de prioridade | 5 | `dim_prioridade_sk` |
| `dim_abertura` | timestamp de abertura | 41.364 | `dim_abertura_sk` |
| `fct_incidentes` | 1 incidente | 41.441 | `incident_sk` |

### `ml` (features + saídas de modelo)

| Tabela | Grão | Linhas | Chave | Papel |
|---|---|---|---|---|
| `ml_base_features` | 1 incidente | 41.441 | `incident_id` | mart larga (40 colunas), fonte das demais |
| `ml_cluster_dataset` | 1 incidente | 41.441 | `incident_id` | entrada do K-Means |
| `ml_sla_classification_dataset` | 1 incidente | 41.441 | `incident_id` | entrada do XGBoost (leakage-free) |
| `ml_forecast_dataset` | 1 dia | 365 | `data_abertura` | entrada do Prophet |
| `fct_previsao_diaria_total` | (origem, dia previsto) | 7 | `previsao_total_sk` | saída Prophet — volume total |
| `fct_previsao_prioridade` | (origem, dia, prioridade) | 35 | `previsao_prioridade_sk` | saída Prophet — split por prioridade |
| `fct_previsao_categoria` | (origem, dia, categoria) | 987 | `previsao_categoria_sk` | saída Prophet — split por categoria |
| `dim_cluster` | cluster | 4 | `cluster_id` | catálogo curado A-D (seed manual) |
| `fct_perfil_cluster` | (cluster, execução) | 4 | `perfil_cluster_sk` | saída K-Means — perfil agregado |
| `fct_importancia_feature` | (feature, execução) | 20 | `importancia_sk` | saída XGBoost/SHAP — importância por coluna |
| `fct_importancia_conceito` | (conceito, execução) | 7 | `importancia_conceito_sk` | saída XGBoost/SHAP — importância por conceito de negócio |
| `fct_risco_incidente` | 1 incidente | 41.441 | `incident_sk` | saída XGBoost — score de risco calibrado |
| `fct_shap_incidente` | (incidente top-risco, feature) | 210 | `shap_sk` | saída SHAP — só os 30 incidentes de maior risco |

**Ainda não existe**: `dw.ref_meta_sla_anual` (metas de OLA por prioridade, usadas
na tela KPI) — ver gap #1 na Parte 2.

---

## Parte 2 — Comparativo: mockup vs dados reais

Legenda: ✅ dado real disponível · ⚠️ dado real existe mas precisa de cálculo/regra
na API (não é uma coluna pronta) · ❌ sem fonte de dado hoje (falta tabela ou é
gap estrutural).

### Ecrã 1 — Painel

| Elemento visual | Fonte real | Status | Observação |
|---|---|---|---|
| KPI "Previsão D+1" | `ml.fct_previsao_diaria_total` (`horizonte='D+1'`, `yhat`) | ✅ | populado (origem `2025-12-31`, `yhat`≈124,5) |
| KPI "Previsão D+7 (média/dia)" | `ml.fct_previsao_diaria_total` (média de `yhat` de D+1 a D+7) | ⚠️ | é uma agregação a fazer na API, não uma coluna pronta |
| Badge "+12% vs média" | `yhat` previsto vs média histórica de `ml.ml_forecast_dataset.total_chamados` | ⚠️ | comparação a calcular na API; não existe coluna/tabela com esse % |
| "Risco de OLA: Médio" + "Atenção a P2" | `ml.fct_risco_incidente` (distribuição de `faixa_risco`) ou `ml.fct_previsao_prioridade` | ⚠️ | é um rótulo agregado por regra de negócio (limiar), não está armazenado em lugar nenhum |
| Gráfico "histórico vs previsão" | histórico: `dw.fct_incidentes`/`dw.dim_tempo` · previsão: `ml.fct_previsao_diaria_total` | ✅ | as duas pontas existem, só juntar na API |

### Ecrã 2 — Detalhe

| Elemento visual | Fonte real | Status | Observação |
|---|---|---|---|
| Card P2 "previstos amanhã" | `ml.fct_previsao_prioridade` (`prioridade_num=2`, D+1) | ✅ | |
| Card P2 "SLA 4h" | `dw.dim_prioridade.threshold_sla_horas` | ⚠️ **divergência** | valor real de P2 é **8h**, não 4h — a Etapa 2 corrigiu essa heurística explicitamente (ver `docs/modelo-dimensional.md`). O mockup usa o valor antigo/errado. |
| Card P2 "72% do limite mensal" | `dw.ref_meta_sla_anual` | ❌ | tabela não existe; além disso a meta do mockup é **anual** (31/ano), não mensal — precisa decidir como derivar um % mensal a partir de uma meta anual |
| Card P3 "SLA 12h" | `dw.dim_prioridade.threshold_sla_horas` | ⚠️ **divergência** | valor real de P3 é **24h**, não 12h |
| "Top 5 categorias — volume previsto amanhã" | `ml.fct_previsao_categoria` (D+1, top 5 por `yhat_categoria`) | ✅ | 987 linhas já populadas, cobre várias categorias/dias |

### Ecrã 3 — KPI

| Elemento visual | Fonte real | Status | Observação |
|---|---|---|---|
| "Dias decorridos / restantes" (do mês) | nenhuma — é calendário puro | ✅ (computado) | lógica de data, não precisa de tabela |
| "OLA Quebrados" (mês) | `dw.fct_incidentes` (`target_risco_sla`/`kpi_status_int`) agregado por `dw.dim_tempo` | ✅ | mas a base é histórica (até 2025-12-31), não um fluxo de chamados ao vivo — "mês" precisa vir como parâmetro de referência, não "hoje" real |
| "Meta: máx 31/201 quebras por ano" | `dw.ref_meta_sla_anual` | ❌ | **tabela não existe** — já sinalizado no plano da Etapa 5 como placeholder do mockup |
| "% OLA quebrado (mês)" / "% volume tratado (mês)" | idem, depende da meta | ❌ | bloqueado pela mesma tabela ausente |
| "Probabilidade de atingir meta anual" | nenhuma — nem modelo, nem tabela | ❌ | não é saída de ML hoje; o plano da Etapa 5 já prevê isso como heurística (projeção linear + Poisson) a implementar na API, com aviso explícito de que não é ML |

### Ecrã 4 — Fatores

| Elemento visual | Fonte real | Status | Observação |
|---|---|---|---|
| Feature Importance (barras) | `ml.fct_importancia_conceito` | ⚠️ **conteúdo diverge do mockup** | a tabela existe e está populada (7 conceitos reais), mas os 5 fatores do mockup não batem com o modelo real: mockup lidera com "Dia da semana" (92%) — no modelo real, **"Dia da semana" é o último colocado (1,23%)**. O líder real é "Prioridade do chamado" (30,76%), seguido de "Carga operacional do time" (19,59%) e "Categoria e triagem" (19,44%). "Volume D-7 (lag)" e "Item de configuração", citados no mockup, **não existem como feature** no dataset de risco (`ml.ml_sla_classification_dataset` não tem essas colunas) |
| "Valores SHAP" — waterfall "Amanhã" | `ml.fct_shap_incidente` | ❌ **mismatch semântico** | o SHAP real explica o **risco de incidentes individuais** (XGBoost, só os 30 de maior risco), não a previsão de volume do dia seguinte — o Prophet (que gera a previsão de amanhã) não produz SHAP. Já documentado como reinterpretação necessária em `docs/modelo-dimensional.md`; a tela precisa ser adaptada para "por que este incidente é de alto risco", não "por que amanhã terá X incidentes" |
| Heatmap categoria × dia da semana | `dw.fct_incidentes` + `dw.dim_produto_categoria` + `dw.dim_tempo` | ✅ | calculado on-the-fly na API, sem tabela dedicada (como já previsto no plano da Etapa 5) |

### Ecrã 5 — Clusters

| Elemento visual | Fonte real | Status | Observação |
|---|---|---|---|
| Gráfico de bolhas (duração×risco×volume) | `ml.fct_perfil_cluster` + `ml.dim_cluster` | ✅ **estrutura pronta, valores divergem** | os 4 clusters existem com métricas reais, mas os números são bem diferentes dos ilustrativos do mockup — ex.: cluster B real tem duração média de **~198h** (vs 1,8h no mockup) e volume de 32,9% (vs implícito ~9% "menor"). O mockup era 100% fictício; ao construir o gráfico real, a escala do eixo X precisa refletir essa amplitude |
| Cards por cluster (nome, tags) | `ml.dim_cluster` | ✅ | nomes e tags foram semeados manualmente a partir do próprio mockup (migration 018) — coincidem por construção |
| Métricas dos cards (volume/duração/quebra OLA) | `ml.fct_perfil_cluster` | ✅ | dado real, mas valores diferentes dos exemplos do mockup (esperado) |

### Ecrã 6 — Alertas

| Elemento visual | Fonte real | Status | Observação |
|---|---|---|---|
| Alertas (crítico/moderado/estável) | combinação de `ml.fct_previsao_diaria_total` + `ml.fct_previsao_categoria` + histórico | ❌ | sem tabela dedicada — regra de negócio a implementar na API (por desenho, conforme plano da Etapa 5) |
| "Item de configuração XYZ recorrente" | `item_configuracao` existe em `public.incidentes` e `ml.ml_base_features`, mas **não está em `dw.fct_incidentes`** | ❌ **gap estrutural** | o star schema não carrega granularidade de CI hoje; o mockup pede algo mais fino do que o `dw` entrega — ficaria aproximado por categoria/subcategoria, ou exigiria uma nova dimensão |
| Recomendações prescritivas (texto numerado) | nenhuma tabela — texto gerado por regra/template | ❌ | por desenho, não é saída de ML — lógica de negócio a implementar na API |

---

## Resumo — gaps que precisam de decisão antes/durante a Etapa 5

1. **`dw.ref_meta_sla_anual` não existe.** Bloqueia parte do Ecrã 2 (% do limite
   mensal) e do Ecrã 3 (meta anual, % quebrado, % tratado, probabilidade). Migration
   ainda por criar, com os números do mockup como placeholder explicitamente
   sinalizado na UI (não como dado real).
2. **Thresholds de SLA do mockup (P2=4h, P3=12h) divergem dos valores reais e já
   corrigidos no banco (P2=8h, P3=24h).** Decisão necessária: a API usa
   `dw.dim_prioridade.threshold_sla_horas` (recomendado — é o valor certo) ou
   mantém os números do mockup como estavam (errado, mas visualmente "igual" à
   referência)?
3. **O painel "Fatores" do mockup não corresponde à realidade do modelo treinado.**
   "Dia da semana" é ilustrado como fator dominante (92%) mas é o último no modelo
   real (1,23%); "Volume D-7 (lag)" e "Item de configuração" não são features do
   classificador de risco. Decisão: a tela é construída 100% com os conceitos e
   pesos reais de `ml.fct_importancia_conceito` (recomendado), ou mantém a
   composição do mockup como estilo/ilustração?
4. **SHAP "Amanhã" do mockup não existe como tal** — SHAP real explica incidentes
   individuais de alto risco, não o volume do dia seguinte. A tela precisa ser
   reinterpretada (já registrado em `docs/modelo-dimensional.md`).
5. **Granularidade de item de configuração (CI)** usada nos Alertas do mockup não
   está no `dw` — aproximar por categoria/subcategoria, ou avaliar se vale a pena
   adicionar uma dimensão de CI numa iteração futura.
6. **"Risco de OLA: Médio"**, **badges de variação (+12% vs média)** e
   **probabilidade de atingir a meta anual** não são saídas de nenhum modelo —
   são heurísticas/regras a implementar na camada de API, e devem ser
   apresentadas como tal (não como resultado de ML), consistente com a diretriz
   já registrada em `CLAUDE.md` (seção 4).
