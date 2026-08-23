# PLAN — Fechamento de Lacunas do Desafio AIOps

> Este plano é aditivo ao que já está decidido em `CLAUDE.md`,
> `docs/dicionario-dados.md`, `docs/modelo-dimensional.md`,
> `docs/forecast-por-equipe.md`, `docs/prds/etapa5-api.md`,
> `docs/schema-e-cobertura-mockup.md` e `docs/resumo-projeto.md` — esse corpo
> de documentação já mergeada é a fonte de verdade funcional (escopo, 6 telas,
> P2/P3, forecast por equipe, KPI/OLA, SHAP, Clusters, EDA, métricas, FastAPI,
> React). Nenhuma decisão registrada nesses documentos é removida, substituída
> ou enfraquecida aqui. O **Anexo A** (governança/QA de ML via Agent Skills) é
> um complemento técnico — não redefine produto, telas ou regras de negócio.
>
> Ordem de precedência em caso de conflito: (1) migrations/código/documentação
> já mergeados, (2) `CLAUDE.md`, (3) este plano funcional, (4) Anexo A
> (Agent Skills), (5) mockups/documentos históricos.

## 1. Objetivo

Fechar as lacunas que ainda separam o pipeline atual (Etapas 0-4 concluídas)
dos requisitos explícitos do desafio AIOps Locaweb/FIAP — foco P2/P3, pressão
operacional por equipe, análise por produto/categoria, recorrência, EDA
formal, métricas de validação consolidadas — e deixar tudo isso rastreável
antes de iniciar a Etapa 5 (API) e a Etapa 6 (React). O plano é só
documentação/planejamento: nenhuma fase aqui implica código, migration,
retreino, commit, merge ou push nesta tarefa.

## 2. Estado atual

```
public.incidentes              (bronze — 122.543 linhas, 2023-2025)
        │
        ▼  notebook 03
staging.incidentes_silver      (silver — 41.441 linhas, pós-2025)
        │
        ├──▶ notebook 04 ──▶ dw.*        (star schema)
        │
        └──▶ notebook 05 ──▶ ml.ml_*     (marts de features)
                                   │
                                   ▼
                    forecast total / forecast por equipe / clustering / xgboost
                                   │
                              ml.fct_*   (saídas dos modelos)
                                   │
                                   ▼
                              FastAPI (Etapa 5, ⬜) ──▶ React (Etapa 6, ⬜)
```

- **Etapas 0-4: ✅ concluídas.** 4 modelos de ML rodando contra o banco `fiap`
  real, saídas em `ml.fct_*`: Prophet total (`fct_previsao_diaria_total` +
  splits `_prioridade`/`_categoria`), Prophet por equipe
  (`fct_previsao_grupo`, migration 025, arquitetura híbrida A/B/C — ver
  `docs/forecast-por-equipe.md`), K-Means (`dim_cluster` + `fct_perfil_cluster`),
  XGBoost+SHAP (`fct_importancia_feature`/`_conceito`, `fct_risco_incidente`,
  `fct_shap_incidente`).
- **KPI oficial já existe**: `dw.ref_meta_sla_anual` (migration 024, 24
  linhas reais do Dicionário de Dados oficial do desafio, não placeholder) +
  lookup `etl/ref_meta_sla.py::faixa_meta_sla()`, 8 testes em
  `tests/test_ref_meta_sla.py`.
- **Threshold de SLA corrigido** (2026-08-21): `dw.dim_prioridade.threshold_sla_horas`
  = {1:4, 2:4, 3:12, 4:24, 5:96}h, valores oficiais, propagados a
  `dw.fct_incidentes` e retreino do XGBoost já feito com o rótulo corrigido.
- **Etapa 5 (`app/api/`) e Etapa 6 (`app/web/src/`): ⬜ esqueleto apenas.**
  `app/api/main.py` só tem `GET /health`; `app/web/src/` só tem
  `App.tsx`/`main.tsx`/`index.css` do template Vite.
- **Lacunas confirmadas nesta auditoria** (sem fonte/cálculo hoje): default
  P2/P3 nas telas, pressão operacional por equipe, recorrência
  produto/categoria, EDA formal consolidada, métricas de validação
  consolidadas em documento único, diagnóstico `k=2..8` do K-Means, pin de
  versões em `requirements*.txt`.

## 3. Matriz desafio × solução

| Pergunta do desafio | Fonte de dado | Status |
|---|---|---|
| O que vai acontecer? (D+1..D+7) | `ml.fct_previsao_diaria_total` | ✅ dado pronto — falta API/tela |
| Onde vai acontecer? (prioridade/categoria/equipe) | `ml.fct_previsao_prioridade` / `_categoria` / `_grupo` | ✅ dado pronto — falta API/tela |
| P2/P3 estão sob risco? | `dw.dim_prioridade` + `ml.fct_risco_incidente` | ⚠️ falta default P2/P3 nas consultas/telas |
| Qual equipe estará sob maior pressão? | `ml.fct_previsao_grupo` | ⚠️ falta cálculo de pressão relativa (Fase 3) |
| Qual produto/categoria exige atenção? | `ml.fct_previsao_categoria` + `dw.dim_produto_categoria` | ⚠️ hoje só quebra por categoria; falta suportar `produto` também (Fase 4) |
| Por que existe risco? | `ml.fct_importancia_conceito`/`_feature` + `ml.fct_shap_incidente` | ✅ dado pronto — falta API/tela |
| Quais padrões existem? | `ml.dim_cluster` + `ml.fct_perfil_cluster` | ✅ dado pronto — falta API/tela + diagnóstico de `k` |
| Sazonalidade / recorrência | `ml.ml_forecast_dataset` (sazonalidade já no Prophet) / recorrência ❌ | ⚠️ recorrência não existe (Fase 5) |
| O que fazer? (recomendações) | regras prescritivas sobre os dados acima | ❌ não implementado (Fase 11) |

## 4. Matriz obrigatória das 6 telas

Nomes técnicos canônicos = os já usados no mockup mergeado
(`docs/design/aiops_dashboard_redesign.html`, nav `go(0)..go(5)`) e em
`CLAUDE.md` §1/§9. Entre parênteses, o rótulo de apresentação/storytelling
(Sprint 3) — **não** é uma renomeação da tela, é só um nome mais descritivo
para a narrativa final; nenhum artefato mergeado usa esses nomes hoje.

| Tela (nome canônico) | Fonte | Pergunta que responde |
|---|---|---|
| **Painel** | `ml.fct_previsao_diaria_total` (Prophet total) | O que vai acontecer? |
| **Detalhe** (rótulo: "Operação") | `ml.fct_previsao_prioridade`/`_categoria`/`_grupo` + `dw.dim_prioridade`/`dim_produto_categoria`/`dim_grupo` | Onde vai estar concentrado? P2/P3 sob risco? Qual equipe exige atenção? |
| **KPI** (rótulo: "OLA & Metas") | `dw` + `dw.ref_meta_sla_anual` | Como estamos contra as regras oficiais de SLA? |
| **Fatores** (rótulo: "Fatores de Risco") | `ml.fct_importancia_conceito`/`_feature` + `ml.fct_shap_incidente` | Por que existe risco? |
| **Clusters** (rótulo: "Perfis Operacionais") | `ml.dim_cluster` + `ml.fct_perfil_cluster` | Quais padrões existem? |
| **Alertas** (rótulo: "Alertas & Ações") | regras prescritivas sobre as 5 telas acima | O que fazer? |

Regra: nenhuma das 6 telas pode ficar sem fase/tarefa explícita abaixo —
cobertura: Painel → Fase 6; Detalhe → Fase 7; KPI → Fase 8; Fatores → Fase 9;
Clusters → Fase 10; Alertas → Fase 11.

---

## Fase 1 — Auditoria das fontes ✅ executada (2026-08-22)

**Resultado**: todas as tabelas abaixo conferidas ao vivo contra o banco
`fiap` — 100% de aderência com `docs/dicionario-dados.md` (41.441 linhas em
`dw.fct_incidentes`/`ml.ml_base_features`/`ml.ml_cluster_dataset`/
`ml.ml_sla_classification_dataset`; `ml.fct_previsao_diaria_total`=7,
`_prioridade`=35, `_categoria`=987, `_grupo`=112 linhas; `ml.dim_cluster`=4,
`ml.fct_perfil_cluster`=4; `ml.fct_importancia_feature`=20,
`_conceito`=7; `ml.fct_risco_incidente`=41.441, `ml.fct_shap_incidente`=210).
Referência temporal confirmada: `origem`/`data_abertura` mais recente em
todas as tabelas de forecast = **2025-12-31** — é o "hoje" efetivo do
pipeline, usado como âncora para as Fases 3/5 abaixo. Nenhuma escrita nesta
fase.

**Read-only.** Antes de qualquer implementação (Etapa 5), inspecionar e
registrar grão/colunas/volume/cobertura/última `data_execucao`/limitações de:

- `dw.dim_prioridade`, `dw.dim_produto_categoria`, `dw.dim_grupo`,
  `dw.dim_tempo`, `dw.fct_incidentes`, `dw.ref_meta_sla_anual`
- `ml.ml_base_features`, `ml.ml_forecast_dataset`, `ml.ml_cluster_dataset`,
  `ml.ml_sla_classification_dataset`
- `ml.fct_previsao_diaria_total`, `ml.fct_previsao_prioridade`,
  `ml.fct_previsao_categoria`, `ml.fct_previsao_grupo`
- `ml.dim_cluster`, `ml.fct_perfil_cluster`
- `ml.fct_importancia_feature`, `ml.fct_importancia_conceito`,
  `ml.fct_risco_incidente`, `ml.fct_shap_incidente`

Grão/colunas/relacionamentos de todas essas tabelas já estão documentados
coluna-a-coluna em `docs/dicionario-dados.md` (verificado contra o schema
real em 2026-08-21). O que falta nesta fase é uma checagem **viva** (volume
atual, `data_execucao` mais recente de cada `ml.fct_*`, se as 16 equipes/4
clusters/24 faixas de meta continuam consistentes) antes de a Etapa 5 começar
a consumir — consulta `SELECT COUNT(*), MAX(data_execucao) FROM ...`, sem
nenhuma escrita.

## Fase 2 — Foco P2/P3 ✅ validada (2026-08-22)

**Resultado**: `dw.dim_prioridade.threshold_sla_horas` confirmado correto
(1=4h, 2=4h, 3=12h, 4=24h, 5=96h). P2+P3 = **78,9%** de todo o volume de
`dw.fct_incidentes` (32.677 de 41.441) — confirma que o recorte é
representativo, não uma fatia pequena. `ml.fct_previsao_prioridade` já
cobre todas as 5 prioridades (nenhuma tabela nova necessária); o filtro
P2/P3 é uma convenção de consulta/API a aplicar na Etapa 5, não um artefato
de dado.

Default analítico das telas Painel/Detalhe/Alertas = **P2 + P3** (é o recorte
que o desafio pede foco). Outras prioridades (P1, P4, P5) continuam
acessíveis como filtro/contexto — nunca escondidas do usuário, só não são o
recorte padrão ao carregar a tela.

Threshold de SLA usado em qualquer regra (alerta, KPI, badge) vem sempre de
`dw.dim_prioridade.threshold_sla_horas` — nunca um valor hardcoded no
frontend ou em uma nova constante Python. P2=4h, P3=12h (valores oficiais já
corrigidos, ver `docs/modelo-dimensional.md`).

## Fase 3 — Forecast e pressão por equipe ✅ implementada (2026-08-22)

**Resultado**: `ml.fct_pressao_equipe` criada (migration
`026_ml_fct_pressao_equipe.sql`) e populada por `notebooks/pressao_equipe.py`
(112 linhas, origem=2025-12-31, mesmo padrão append/idempotente por origem
de `ml.fct_previsao_grupo`). D+1: `Team02` lidera com +29,4% (`atencao`),
seguido de `Team03` +17,0% e `Team17` +13,1% (ambos `atencao`); nenhuma
equipe cruzou o limiar `critico` (>30%) nesta execução. Todas as equipes de
Grupo A (maior volume) estão **abaixo** da própria média histórica em D+1.
Ver `docs/dicionario-dados.md` para o schema completo.

Fonte oficial: `ml.fct_previsao_grupo` (D+1..D+7, 16 equipes, `metodo` ∈
{`prophet_individual`, `prophet_semanal`, `split_proporcional`} — ver
`docs/forecast-por-equipe.md`).

Cálculo da **Pressão Operacional Prevista** por equipe:

```
pressao_relativa_pct = ((forecast_d1 - media_historica_equipe) / media_historica_equipe) * 100
```

`media_historica_equipe` = média diária histórica da própria equipe (mesma
fonte/janela de `ml.ml_base_features`/`ml.ml_forecast_dataset` usada na
investigação de `docs/forecast-por-equipe.md` §3). Nunca chamar isso de
capacidade real, headcount ou saturação contratual — é uma comparação de
volume previsto contra o próprio histórico da equipe, nada além disso.
Validar faixas (ex.: `<10%` normal, `10-30%` atenção, `>30%` crítico) antes
de consolidar — thresholds fixos e documentados no código, não “achismo” de
UI.

## Fase 4 — Produto e categoria ✅ implementada (2026-08-22)

**Resultado**: `ml.fct_previsao_produto` criada (migration
`027_ml_fct_previsao_produto.sql`) e populada por
`notebooks/forecast_produto.py` — mesma técnica de proporção histórica de
`fct_previsao_categoria` (`calcular_shares()` reaproveitada, mesmo recorte
de regime). 51 produtos, origem=2025-12-31. Top D+1: `lhco` (27,7% do
histórico, 34,5 previstos), `lsin` (14,5%), `lcem` (13,4%). Decisão
confirmada: técnica de split proporcional é adequada (mesma ressalva de
metodologia de categoria/prioridade se aplica — não é Prophet por corte).

Suportar as duas granularidades:

- `agrupamento=categoria` → `ml.fct_previsao_categoria` (já existe, 987
  linhas).
- `agrupamento=produto` → **não existe hoje** como split dedicado; avaliar
  na Etapa 5 se dá para reaproveitar a mesma técnica de proporção histórica
  (`share_historico` por `produto` sobre `ml.fct_previsao_diaria_total.yhat`,
  mesmo padrão de `fct_previsao_categoria`) ou se precisa de uma tabela nova
  — decisão de implementação da Etapa 5, não deste plano.

Sem simular CI (item de configuração): `item_configuracao` existe em
`public.incidentes`/`ml.ml_base_features`, mas **não está em
`dw.fct_incidentes`** (gap estrutural já registrado em
`docs/schema-e-cobertura-mockup.md` gap #5) — não fabricar esse dado.

## Fase 5 — Recorrência ✅ implementada (2026-08-22)

**Resultado**: `dw.fct_recorrencia_operacional` criada (migration
`028_dw_fct_recorrencia_operacional.sql`) e populada por
`notebooks/recorrencia.py` (649 linhas, janela_referencia=2025-12-31, janela
atual 2025-12-02..2025-12-31 vs. janela anterior 2025-11-02..2025-12-01).
Classificação combina `delta_pct` com `cobertura_dias_atual_pct` (não é só
volume alto — ver limiares documentados no script). Exemplo real de
`recorrente_crescente` em categoria: `cat94` (+466,7%, presente em 50% dos
dias), `cat35` (+100,0%, 60% dos dias). Distribuição de status por
granularidade disponível na tabela; maioria das combinações finas
(categoria+subcategoria) cai em `volume_insuficiente` (307 de 649 linhas) —
esperado, dado o grão fino.

**Não existe hoje.** Criar como consulta SQL/EDA simples (não é modelo de
ML): comparar janela dos últimos 30 dias vs. os 30 dias anteriores, por
entidade candidata:

- produto
- categoria
- produto + categoria
- categoria + subcategoria

Saída esperada por entidade: `volume_atual`, `volume_baseline`,
`delta_pct`, `status_recorrencia` (ex.: `estavel`/`crescente`/`recorrente`).
Recorrência **não é sinônimo de volume alto** — uma entidade pode ter volume
baixo mas recorrente (aparece toda semana) ou volume alto mas pontual
(um pico isolado); a regra de classificação precisa distinguir os dois casos
(ex.: comparar não só o total, mas o número de dias/semanas em que a
entidade aparece acima de um piso mínimo).

## Fase 6 — Painel

Responder: quanto teremos amanhã (D+1)? Quanto em D+7? Há pico (variação
D+1 vs. média histórica)? Qual o risco de OLA (faixa fixa sobre
`pct_violacao_sla` de `ml.ml_forecast_dataset`)? Qual equipe está sob maior
pressão (Fase 3)? Fonte: `ml.fct_previsao_diaria_total` + `ml.ml_forecast_dataset`
+ `ml.fct_previsao_grupo`. Contrato de dados completo: `docs/prds/etapa5-api.md` §4.1.

## Fase 7 — Operação

Responder: P2/P3 estão sob risco (Fase 2 + `ml.fct_risco_incidente`)? Qual
equipe exige atenção (Fase 3)? Qual categoria/produto lidera volume previsto
(Fase 4)? Fonte: `ml.fct_previsao_prioridade` + `ml.fct_previsao_categoria` +
`ml.fct_previsao_grupo` + `dw.dim_prioridade`. Contrato de dados completo (inclui
granularidade `produto` e recorrência): `docs/prds/etapa5-api.md` §4.2.

## Fase 8 — KPI / Metas oficiais

Obrigatório usar `dw.ref_meta_sla_anual` + `etl/ref_meta_sla.py::faixa_meta_sla()`
— **já existe, é dado real** (24 linhas, 2 indicadores × 2 prioridades × 6
faixas), não placeholder. Mostrar: valor observado (contagem acumulada no
ano, via `dw.fct_incidentes`), faixa correspondente, `pct_atingimento` da
faixa, `status` derivado.

Separar sempre de **projeção futura**: `probabilidade_atingir_meta_pct` =
projeção linear determinística (`(quebras_ate_agora / dias_decorridos) *
dias_totais_do_ano`, comparado à meta), com
`metodologia_probabilidade="projecao_linear"` sempre presente no payload —
decisão já tomada em `docs/modelo-dimensional.md` e `docs/prds/etapa5-api.md`
§4.3. **Nunca usar Poisson ou outro modelo estatístico** nesta etapa —
decisão registrada, não em aberto.

## Fase 9 — Fatores / XGBoost + SHAP

Importância global: `ml.fct_importancia_conceito` (primária, granularidade
de negócio — "Prioridade do chamado", "Categoria e triagem" etc.). Fallback
para `ml.fct_importancia_feature` (coluna crua) só quando o SHAP não rodou
naquela execução (fica vazia no fallback por gain do XGBoost).

SHAP: `ml.fct_shap_incidente` (top 30 por `score_calibrado`) + `ml.fct_risco_incidente`.
Pergunta correta: **"por que este incidente possui risco elevado?"** — nunca
"por que haverá mais chamados amanhã?". Regra semântica permanente:
Prophet → volume futuro; XGBoost → risco; SHAP → explicação individual do
risco do XGBoost. Nunca misturar as três. Contrato de dados completo:
`docs/prds/etapa5-api.md` §4.4.

## Fase 10 — Clusters / K-Means ✅ diagnóstico executado (2026-08-22)

**Resultado do diagnóstico `k=2..8`** (read-only,
`notebooks/diagnostico_kmeans_k.py`, resultado completo em
`docs/metricas-validacao.md` §3): silhouette maximizado em `k=2` (0,3814),
Davies-Bouldin minimizado em `k=8` (0,8961), sem cotovelo nítido na curva de
inertia. `k=4` (produção): silhouette=0,3413, Davies-Bouldin=0,9876 —
posição intermediária, nem o melhor nem o pior nas duas métricas. **Não há
evidência estatística forte para trocar `k`, nem para confirmá-lo** — fica
como checkpoint humano (Anexo A, ML-2): manter `k=4` pela justificativa de
negócio (4 perfis interpretáveis já em produção) é uma decisão defensável,
mas não uma decisão "provada" pelas métricas. Nenhuma tabela do banco
(`ml.dim_cluster`/`ml.fct_perfil_cluster`) foi alterada.

Fontes: `ml.dim_cluster` (4 clusters, A-D, taxonomia curada) +
`ml.fct_perfil_cluster` (métricas agregadas, recarregada por completo a cada
execução). Exibir os 4 perfis operacionais. Visual: eixo X = duração média
(`duracao_media_horas`), eixo Y = taxa de violação (`taxa_sla_violado_pct`),
tamanho da bolha = `pct_volume`. Interpretação de negócio obrigatória em
cada card (não só números).

**Diagnóstico pendente, confirmado nesta auditoria** (ver Anexo A/A.4):
`notebooks/model_clustering_kmeans_Revisado.ipynb` tem `k=4` hardcoded
(linha 531) e `PCA(n_components=3, random_state=42)` hardcoded (linha 479) —
o comentário do notebook diz "95% variância" mas a variância explicada real
impressa na execução é **39.95%**. `silhouette_score`/`davies_bouldin_score`
já são calculados, mas só para o `k=4` fixo, não em varredura. Diagnóstico
seguro a fazer: `k=2..8` com silhouette, Davies-Bouldin e inertia/elbow,
**read-only**, para verificar se `k=4` é defensável. Se não for: reportar,
checkpoint humano, decisão sobre retreino — nunca retreinar automaticamente
(ver Anexo A, ML-2).

## Fase 11 — Alertas

Regras candidatas (todas com `regra_origem` explícito, sem fallback de CI):

- `pico_volume_d1` — variação de `ml.fct_previsao_diaria_total` D+1 vs.
  média histórica acima de um limiar fixo.
- `pressao_operacional_equipe` — `pressao_relativa_pct` da Fase 3 acima de
  um limiar fixo.
- `cluster_alta_violacao` — cluster com `taxa_sla_violado_pct` acima de um
  limiar fixo (`ml.fct_perfil_cluster`).
- `concentracao_categoria` — categoria concentrando volume previsto acima de
  um limiar (`ml.fct_previsao_categoria`).
- `recorrencia_operacional` — entidade classificada como recorrente na
  Fase 5.

Toda recomendação prescritiva carrega `regra_origem` apontando para qual
regra a gerou — sem tabela nova, sem dado fora do que já é exposto pelas
demais telas, sem simular item de configuração (CI). Contrato de dados
completo (catálogo das 5 regras): `docs/prds/etapa5-api.md` §4.6.

## Fase 12 — EDA ✅ consolidada (2026-08-22)

**Resultado**: 8 evidências em formato Achado/Impacto/Decisão, com números
reais extraídos ao vivo de `dw.fct_incidentes` — documento completo em
`docs/eda-consolidada.md`. Achado mais relevante para corrigir um
mal-entendido antigo: o "salto de regime" citado em
`docs/schema-fonte-incidentes.md` existe na tabela bruta
`public.incidentes` (ruído de monitoramento), **não** no grão filtrado
`dw.fct_incidentes`/`ml.ml_forecast_dataset` (volume mensal estável,
2.343-4.053/mês em 2025) — a distinção evita esperar uma quebra de patamar
que não existe no dado que o Prophet realmente treina.

## Fase 13 — Métricas de validação ✅ consolidada (2026-08-22)

**Resultado**: tabela única Modelo/Métrica/Resultado/Baseline/Interpretação
em `docs/metricas-validacao.md`, reaproveitando os artefatos já gerados
(`data/ml/prophet/`, `data/ml/xgboost/`, `data/ml/kmeans/`) mais o
diagnóstico novo do K-Means (Fase 10). **3 achados que precisam de decisão
humana, não escondidos**: (1) Prophet em produção não supera o baseline
`mediana_dow_4sem` em MAE/WAPE/MASE; (2) XGBoost não atinge a meta de
AUC-ROC 0,85 registrada no próprio artefato (0,80 teste, 0,76 backtest); (3)
K-Means `k=4` sem defesa estatística clara nem evidência para trocar. Nenhum
desses três é uma falha silenciosa — todos já estavam nos artefatos, só não
consolidados num único lugar até agora.

**Não repetir trabalho já feito** — este projeto já tem avaliação real
implementada para Prophet e XGBoost (confirmado por leitura direta do
código nesta auditoria, não só pela referência das skills). Consolidar em
uma tabela única (Modelo | Métrica | Resultado | Baseline | Interpretação):

- **Prophet (total e por equipe)**: reutilizar o que já existe em
  `notebooks/forecast_incidentes_revisado.py` — backtest de origem móvel
  (`backtest()`), baselines (`naive_ultimo`, `snaive_lag7`,
  `mediana_dow_4sem`, médias móveis), MAE, RMSE, WAPE (não MAPE — decisão já
  tomada por causa de volume baixo em algumas séries), MASE (denominador =
  MAE do naive sazonal lag-7 dentro do treino), cobertura de intervalo
  (`cobertura%`), split temporal. **Diagnóstico de resíduos (ACF) já existe**
  (`acf_residuos()`, painel "ACF dos resíduos D+1") — não é gap, só
  consolidar o resultado já gerado.
- **XGBoost**: `notebooks/model_risk_xgboost_.ipynb` já calcula ROC-AUC
  (treino/validação/teste, com gap monitorado), PR-AUC, F1, precision,
  recall, Brier score (com e sem calibração, inclusive por estrato),
  threshold escolhido por validação (`argmax` de F1 em grade), backtest
  temporal por partição. Consolidar o que já existe — não reavaliar do
  zero.
- **K-Means**: gap real confirmado — `silhouette`/`davies_bouldin` só
  calculados para `k=4` fixo. Fazer diagnóstico novo `k=2..8` (Fase 10),
  read-only, reportando se `k=4` seria escolhido por um critério objetivo.

Não inventar valores — todo número desta fase vem de rodar o
notebook/script já existente (ou o diagnóstico novo do K-Means) e ler o
resultado, nunca de estimativa.

## Fase 14 — FastAPI ✅ implementada (2026-08-22)

**Resultado**: os 6 endpoints implementados em `app/api/routers/` (um
módulo por tela) e registrados em `app/api/main.py`, todos lendo o banco
`fiap` real via `etl.db.get_engine()` (`app/api/deps.py`), SQL raw via
`sqlalchemy.text()`, um `pydantic.BaseModel` por endpoint como
`response_model` — mesma convenção de `docs/prds/etapa5-api.md` (reescrito
por completo nesta rodada, descontando as partes desatualizadas do PRD
original). 38 testes de contrato em `tests/test_api_<tela>.py`, ✅ (rodam
contra o banco real, só `SELECT`). Dois achados de auditoria confirmados
durante a implementação, sem alterar nenhum dado/modelo — ver Anexo A.4
(métrica de SLA do cluster renomeada; taxonomia de `ml.dim_cluster`
divergente das métricas reais). **Ainda não religado ao frontend** — Etapa
6 (`app/web/`) continua consumindo `dashboardData.ts` estático.

```
/api/painel    /api/detalhe   /api/kpi
/api/fatores   /api/clusters  /api/alertas
```

Decisões tomadas em `docs/prds/etapa5-api.md` (conexão via
`etl.db.get_engine()`, SQL raw via `sqlalchemy.text()`, um
`pydantic.BaseModel` por endpoint como `response_model`) —
**descontando** as partes já desatualizadas do PRD original
(`meta_quebras_ano`/`is_placeholder_meta`/`fonte='placeholder_mockup'`,
que hoje é `dw.ref_meta_sla_anual` real com `pct_atingimento` por faixa,
já refletido na reescrita do PRD). Evitar endpoints extras sem
necessidade — os 6 endpoints acima cobrem as 6 telas.

## Fase 15 — React ✅ implementada e religada à API (2026-08-22)

**Resultado**: as 6 telas (nomes canônicos — ver Matriz da seção 4) existem
em `app/web/src/components/screens/` e consomem dado real de `app/api/`
via `src/lib/api.ts` (cliente tipado) + `src/lib/useApi.ts` (hook de
fetch/loading/erro) — nenhum dado estático. `src/data/dashboardData.ts`
virou só funções puras de apresentação (recebem a resposta da API,
devolvem geometria/texto prontos). Tela KPI foi redesenhada (não só
religada) para refletir o schema real de `dw.ref_meta_sla_anual` — só
P2/P3 têm meta, sem as faixas de P1/P4 que o design original mostrava sem
fonte real. Verificado com Chromium headless (Playwright) nos 6 tabs: zero
erros de console, zero requests falhas, `tsc -b`/`npm run build` limpos.
Rodar: API (`./venv/bin/python3 -m uvicorn app.api.main:app --reload`,
porta 8000) + `cd app/web && npm run dev` (porta 5173).

## Fase 16 — Sprint 3 / Storytelling

Cobrir: Contextualização, Gestão das Sprints, Arquitetura, EDA (Fase 12),
Modelos, Validação (Fase 13), MVP funcional (Etapas 5-6), Storytelling,
Conclusão. Rótulos de apresentação das telas (seção 4) podem ser usados
livremente aqui — é o único lugar onde a narrativa "Operação"/"OLA &
Metas"/"Fatores de Risco"/"Perfis Operacionais"/"Alertas & Ações" se aplica,
sem que isso renomeie a tela tecnicamente.

---

## Anexo A — Governança e Qualidade de ML via Agent Skills

Complemento técnico de QA/diagnóstico/reprodutibilidade/governança. **Não
redefine** nenhuma decisão funcional das Fases 1-16 ou de `CLAUDE.md`. Os
achados abaixo foram **verificados por leitura direta do código** nesta
auditoria (não apenas repetidos do texto genérico dos `SKILL.md`, que são
guias de referência não específicos deste projeto).

### A.1 reproducible-ml

- Seeds (`random_state=42`) já usados de forma consistente nos 3 modelos
  (`grep` conta 11 ocorrências entre os 3 notebooks/script).
- **Gap confirmado**: `requirements.txt` e `requirements-notebooks.txt` não
  têm nenhum pin de versão (`fastapi`, `pandas`, `prophet`, `scikit-learn`,
  `xgboost`, `shap` etc. — todos sem `==`). Ação: diagnosticar o ambiente
  atual (`pip freeze` no `venv/` existente) e propor pin — **checkpoint
  humano antes de alterar `requirements*.txt`** (regra já existente em
  `CLAUDE.md` §8, reforçada aqui).
- Observação a documentar: Prophet/cmdstanpy pode não ser 100% determinístico
  mesmo com seed fixo — limitação conhecida da biblioteca, não bug do
  projeto.

### A.2 algo-forecast-prophet

- **Já implementado** (confirmado em `notebooks/forecast_incidentes_revisado.py`):
  backtest de origem móvel, baselines (naive, sazonal naive lag-7, médias
  móveis, mediana por dia-da-semana), ensemble, MAE, RMSE, WAPE, MASE,
  cobertura de intervalo, split temporal.
- **Diagnóstico de autocorrelação de resíduos: já implementado**
  (`acf_residuos()`, linha 444, painel "ACF dos resíduos D+1" salvo em
  parquet) — corrige uma alegação de gap que não se sustenta mais nesta
  versão do código; não repetir como pendência.
- **Documentação de hiperparâmetros: já presente em comentário no código**
  (`changepoint_range=1.0`, `changepoint_prior_scale=0.05`,
  `seasonality_mode="additive"`, linhas 69-73 de
  `notebooks/forecast_incidentes_revisado.py`, com justificativa inline do
  porquê de `changepoint_range=1.0` em vez do default `0.8`).
- Regra permanece: qualquer diagnóstico aqui é read-only; não retreinar sem
  aprovação.

### A.3 sklearn-pipelines

- **Confirmado**: XGBoost e K-Means não usam `sklearn.Pipeline` formal —
  proteção contra leakage é manual (`ml.ml_sla_classification_dataset` já é
  construída leakage-free na origem, ver `docs/dicionario-dados.md`). Isso
  **não vira obrigação de refatorar os modelos atuais** — regra explícita do
  desafio: modelos atuais preservados, só modelos novos usam Pipeline desde
  o início.
- **Achado de auditoria confirmado**: PCA descrito em comentário como
  "REDUÇÃO DIMENSIONAL (95% variância)" mas o código fixa
  `n_components=3` e a variância explicada real impressa é **39.95%** —
  divergência real entre documentação inline e comportamento do código.
  Registrar como dívida técnica; **não corrigir automaticamente** (mudar
  `n_components` muda o resultado do clustering já em produção).
- **Achado sobre `OneHotEncoder`, revisado (2026-08-22)**: a primeira
  varredura (`grep -rn OneHotEncoder`) não encontrou nenhuma chamada
  literal `OneHotEncoder(...)` e por isso a alegação foi marcada como "não
  confirmada". Inspeção mais profunda da célula `[6a]` de
  `model_clustering_kmeans_Revisado.ipynb` (atribuição de cluster para
  outliers) encontrou o código morto de fato: as variáveis
  `low_cardinality_cols`/`high_cardinality_cols` e um bloco inteiro
  `if 'encoder' in locals(): ... encoder.transform(...)` (comentado "One-Hot
  Encoding com mesmo encoder") — mas **`encoder` nunca é instanciado em
  nenhum lugar do notebook** (o pipeline de produção usa só frequency
  encoding, célula `[4]`, título "SEM ONE-HOT ENCODING"). A condição é
  sempre `False`; o branch nunca executa; o fallback (`X_outliers_proc =
  X_outliers`) é o que sempre roda de fato. **Confirmado como dívida
  técnica real** — código vestigial de uma versão anterior do notebook, sem
  efeito no resultado (o fallback está correto), mas confuso para quem lê.
  Não corrigido automaticamente nesta rodada (é código de um notebook de
  modelo em produção) — candidato a limpeza de baixo risco numa próxima
  revisão do notebook, com checkpoint humano.

### A.4 model-evaluation

- **XGBoost — confirmado, avaliação já robusta**: ROC-AUC (treino/validação/
  teste, com gap monitorado para overfitting), PR-AUC, F1, precision,
  recall, Brier score (bruto e calibrado, inclusive por estrato de
  prioridade), threshold escolhido por grid search maximizando F1 na
  validação, backtest temporal por partição
  (treino/validação/teste/fora_do_escopo). Ação: **consolidar em uma tabela
  única (Fase 13), não reconstruir**.
- **K-Means — gap real confirmado**: `k=4` hardcoded (linha 531 do
  notebook), sem comparação sistemática. Diagnóstico seguro: `k=2..8` com
  silhouette, Davies-Bouldin, inertia/elbow (Fase 10). Objetivo: verificar
  se `k=4` é defensável. Se não for → reportar → checkpoint humano → decisão
  sobre retreino. **Nunca retreinar automaticamente.**
- **K-Means — 2 achados novos confirmados na implementação da Fase 14 (API,
  2026-08-22), verificados ao vivo contra o banco `fiap`, detalhados em
  `docs/prds/etapa5-api.md` §4.5:**
  1. `ml.fct_perfil_cluster.taxa_sla_violado_pct` é calculada a partir de
     `excedeu_tempo_esperado` (duração > threshold da prioridade), não do
     indicador oficial de SLA (`kpi_status_int`) — 94-98% nos 4 clusters
     contra 0,95% do indicador oficial no banco inteiro. Mitigado na API
     (`app/api/routers/clusters.py`): campo renomeado para
     `taxa_excedeu_tempo_esperado_pct` + nota explicativa fixa no payload.
     **Não corrigido na origem** (`ml.fct_perfil_cluster`/notebook) — mudar
     o que a tabela calcula é retreino/checkpoint humano, fora do escopo da
     API.
  2. `ml.dim_cluster` (taxonomia curada manualmente, migration `018`, não
     recalculada a cada execução do K-Means) diverge das métricas reais de
     `ml.fct_perfil_cluster` para pelo menos 2 dos 4 clusters: cluster B
     rotulado `"Recorrentes rápidos"` / `"Curta duração"` mas com a
     **maior** `duracao_media_horas` real (198,3h); cluster D rotulado
     `"Baixo impacto"` / `"Sem violações"` mas com a **maior**
     `taxa_excedeu_tempo_esperado_pct` (98,0%) e a 2ª maior duração (93,8h).
     **Não corrigido** — reescrever `nome_perfil`/`descricao_curta`/`tags`
     é decisão de conteúdo/produto, não algo para a API decidir sozinha.
     Checkpoint humano pendente: revisar a taxonomia de `ml.dim_cluster`
     contra as métricas reais antes da tela Clusters ir ao ar com dado real
     (Etapa 6 religada à Etapa 5).

### A.5 shap

- **Confirmado uso correto**: `TreeExplainer`, top 30 incidentes por
  `score_calibrado`, dados de teste, agrupamento por conceito de negócio em
  `ml.fct_importancia_conceito`.
- Ação complementar possível (documental, sem alterar tabelas/modelo):
  visualizações exploratórias adicionais — beeswarm global, waterfall de um
  incidente de exemplo — para a Sprint 3 (Fase 16).
- Regra semântica (reforça Fase 9): SHAP → risco individual. **Nunca**
  SHAP → forecast D+1/D+7.

### Matriz fase principal × skill complementar

| Fase | Skill complementar |
|---|---|
| Fase 6 (Painel — forecast total) | `algo-forecast-prophet` + `model-evaluation` |
| Fase 3 (forecast por equipe) | `algo-forecast-prophet` |
| Fase 7/9 (XGBoost) | `model-evaluation` + `sklearn-pipelines` |
| Fase 9 (SHAP) | `shap` + `model-evaluation` |
| Fase 10 (Clusters) | `model-evaluation` + `sklearn-pipelines` |
| Fase 14 (API) | skill conforme o dado exposto |
| Release/ambiente | `reproducible-ml` |
| Fase 16 (Sprint 3) | `model-evaluation` + `algo-forecast-prophet` + `shap` |

### Checkpoints adicionais de ML

- **ML-1 (Prophet)**: diagnóstico de resíduos e documentação de
  hiperparâmetros — já feito (A.2); qualquer alteração futura de modelo
  passa por checkpoint antes de retreinar.
- **ML-2 (K-Means)** ✅ fechado (2026-08-22): diagnóstico comparativo
  `k=2..8` rodado (Fase 10/13, `notebooks/diagnostico_kmeans_k.py`,
  read-only). Resultado: silhouette maximizado em `k=2` (0,3814),
  Davies-Bouldin minimizado em `k=8` (0,8961), sem cotovelo nítido na
  inertia — `k=4` (produção) fica em posição intermediária, não é o
  melhor nem o pior em nenhuma das 3 métricas. **Decisão**: manter `k=4`
  por justificativa de negócio (4 perfis interpretáveis já em produção,
  taxonomia curada em `ml.dim_cluster`), não por vencer as métricas —
  decisão defensável, não "provada" estatisticamente. Nenhuma tabela do
  banco alterada, nenhum retreino. Ver `docs/metricas-validacao.md` §3 e
  `docs/guia-modelo-kmeans-clusters.md` (gráfico do cotovelo).
- **ML-3 (Reprodutibilidade)**: avaliar pin de dependências antes do PR
  final de qualquer etapa futura; alterar `requirements*.txt` só após
  aprovação humana explícita.
- **ML-4 (XGBoost)**: não reavaliar do zero — consolidar o que já existe
  (Fase 13).
- **ML-5 (SHAP)**: validar que a leitura fica restrita a top 30 + risco
  individual, sem associação ao Prophet.

### Correção conceitual importante

Não associar métricas de avaliação do XGBoost (ROC-AUC, PR-AUC, Brier) à
tela **KPI**. KPI é sempre sobre metas/faixas oficiais
(`dw.ref_meta_sla_anual`), atingimento e projeção linear — nunca sobre
performance de modelo. Métricas de modelo (Fase 13) aparecem em documentação
técnica e na Sprint 3 (Fase 16), nunca na tela KPI do dashboard.

---

## Critérios finais de aceite

- [ ] `CLAUDE.md` preservado em todas as seções não relacionadas às lacunas
      (1, 2, 3, 5, 6, 7, 8, 10, 12) — só seções 4/9/11 ganharam adições.
- [ ] 6 telas explícitas na seção 4 deste plano, cada uma com fase própria
      (Fases 6-11).
- [ ] Tela Clusters/Perfis Operacionais explicitamente obrigatória (Fase 10),
      com as métricas exatas de `ml.fct_perfil_cluster`.
- [ ] KPI oficial (`dw.ref_meta_sla_anual`) separado da projeção linear em
      todo o texto (Fase 8, seção "Correção conceitual importante").
- [ ] SHAP tratado sempre como risco individual, nunca forecast (Fase 9,
      A.5).
- [ ] Forecast por equipe com fonte oficial (`ml.fct_previsao_grupo`) e
      fórmula de pressão relativa documentada (Fase 3).
- [ ] Recorrência registrada como lacuna real, com desenho de análise
      (Fase 5).
- [ ] EDA formalizada em evidências Achado/Impacto/Decisão (Fase 12).
- [ ] Métricas de validação consolidadas sem reinventar valores (Fase 13).
- [ ] Diagnósticos de ML (resíduos Prophet, `k` do K-Means, pin de
      dependências) tratados como checkpoint humano, nunca retreino
      automático (Anexo A, checkpoints ML-1 a ML-5).
- [ ] Nenhuma alteração de modelo, migration, notebook, `.env` ou
      `requirements*.txt` nesta tarefa — só `CLAUDE.md` e `PLAN.md`.
- [ ] Nenhum retreino, merge ou push realizado.
