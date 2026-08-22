# Dicionário de dados

Referência rápida das tabelas do banco `fiap`. Para o raciocínio por trás do
desenho (grão, filtros, adaptações), ver `docs/schema-fonte-incidentes.md` e
`docs/modelo-dimensional.md` — este documento é só a lista de colunas.

Schemas: `public` (fonte bruta), `staging` (camada Silver), `dw` (modelo
dimensional / star schema), `ml` (marts de features para modelos de ML).

Verificado contra o schema real do banco `fiap` (via `information_schema`) em
2026-08-21 — 100% de aderência, nenhuma tabela/coluna divergente. Para
volumetria atual (linhas por tabela) e um catálogo executivo compacto, ver
[`docs/schema-e-cobertura-mockup.md`](schema-e-cobertura-mockup.md), que
também compara cada tela do mockup do dashboard com os dados aqui descritos.

## Fonte

### `public.incidentes`
Tabela transacional bruta. 1 linha = 1 chamado. 122.543 linhas (2023-2025).

| Coluna | Tipo | Descrição |
|---|---|---|
| `numero` | text (PK) | Identificador do chamado (ex: `INC8263208`) |
| `prioridade` | text | Texto `"N - Rótulo"`, ex: `"2 - Alta"` |
| `produto` | text | Sistema/aplicação impactada (63,6% nulo) |
| `categoria` | text | Tipo de falha (63,4% nulo) |
| `subcategoria` | text | Detalhe da categoria (63,4% nulo) |
| `grupo_designado` | text | Equipe responsável |
| `item_configuracao` | text | Ativo de TI (CI) com falha |
| `aberto` | timestamp | Abertura do chamado |
| `resolvido` | timestamp | Resolução técnica (67,2% nulo) |
| `encerrado` | timestamp | Encerramento administrativo |
| `duracao_min` | integer | Duração em minutos (tem outliers extremos) |
| `codigo_fechamento` | text | Motivo do encerramento (66,7% nulo) |
| `descricao_resumida` | text | Título do chamado |
| `solucao` | text | Texto livre da solução (87,5% nulo) |
| `aberto_por` | text | `Monitoramento` ou `Manual` |
| `incidente_pai` | text | Auto-referência a `numero` (87,7% nulo) |
| `status` | text | Estado do chamado |
| `entrou_kpi` | boolean | Se entrou no acompanhamento de KPI/SLA |
| `kpi_violado` | boolean | Se violou o KPI (nulo quando `entrou_kpi = false`) |

## Modelo dimensional (schema `dw`)

### `dw.dim_produto_categoria`
1 linha por combinação (produto, categoria, subcategoria).

| Coluna | Tipo | Descrição |
|---|---|---|
| `dim_produto_categoria_sk` | text (PK) | `MD5(produto\|\|categoria\|\|subcategoria)` |
| `produto` | text | Nulo tratado como `"Não Classificado"` |
| `categoria` | text | Nulo tratado como `"Não Classificado"` |
| `subcategoria` | text | Nulo tratado como `"Não Informada"` |

### `dw.dim_grupo`
1 linha por equipe.

| Coluna | Tipo | Descrição |
|---|---|---|
| `dim_grupo_sk` | text (PK) | `MD5(grupo_designado)` |
| `grupo_designado` | text | Nome da equipe |

### `dw.dim_tempo`
1 linha por dia de calendário com incidente (grão de **dia**).

| Coluna | Tipo | Descrição |
|---|---|---|
| `dim_tempo_sk` | text (PK) | `MD5(data_abertura)` |
| `data_abertura` | date | Data pura |
| `ano` | integer | |
| `mes_num` | integer | 1-12 |
| `nome_mes` | text | Nome do mês em português |
| `semana_ano` | integer | Semana ISO do ano |
| `trimestre` | integer | 1-4 |
| `ano_mes` | text | `"YYYY-MM"` |
| `dia_semana_num` | integer | 0=domingo .. 6=sábado |
| `nome_dia` | text | Nome do dia em português |
| `is_fim_de_semana` | boolean | Sábado ou domingo |

### `dw.dim_status`
1 linha por combinação (status, código de fechamento).

| Coluna | Tipo | Descrição |
|---|---|---|
| `dim_status_sk` | text (PK) | `MD5(status\|\|codigo_fechamento)` |
| `status` | text | |
| `codigo_fechamento` | text | Nulo tratado como `"Não Informado"` |
| `entrou_kpi` | boolean | |

### `dw.dim_prioridade`
1 linha por nível de prioridade.

| Coluna | Tipo | Descrição |
|---|---|---|
| `dim_prioridade_sk` | text (PK) | `MD5(prioridade_num)` |
| `prioridade_num` | integer | 1 (crítico) a 5 |
| `prioridade_texto` | text | Texto original da fonte |
| `bucket_prioridade` | text | Ex: `"P2 - Alta"` |
| `nivel_criticidade` | text | `"Critico"` (P1/P2) ou `"Normal"` |
| `threshold_sla_horas` | integer | Meta contratual (Dicionário de Dados oficial do desafio): P1=4h, P2=4h, P3=12h, P4=24h, P5=96h |

### `dw.dim_abertura`
1 linha por timestamp distinto de abertura (grão de **timestamp**, não de dia).

| Coluna | Tipo | Descrição |
|---|---|---|
| `dim_abertura_sk` | text (PK) | `MD5(aberto_at)` |
| `aberto_at` | timestamp | Timestamp completo |
| `hora_abertura` | integer | 0-23 |
| `turno_abertura` | text | Madrugada / Manha / Tarde / Noite |
| `fora_horario_comercial` | boolean | Fora de 8h-18h |
| `abriu_fim_de_semana` | boolean | |

### `dw.fct_incidentes`
Fato central. **1 linha = 1 incidente** que exigiu esforço humano real
(`status <> 'Sem Intervenção'`) e foi aberto a partir de 2025-01-01.
41.441 linhas.

| Coluna | Tipo | Descrição |
|---|---|---|
| `incident_sk` | text (PK) | `MD5(numero)` |
| `dim_produto_categoria_sk` | text (FK) | |
| `dim_grupo_sk` | text (FK) | |
| `dim_tempo_sk` | text (FK) | |
| `dim_status_sk` | text (FK) | |
| `dim_prioridade_sk` | text (FK) | |
| `dim_abertura_sk` | text (FK) | |
| `incident_id` | text (único) | Chave degenerada — `numero` original, para drill-down sem join |
| `duracao_horas` | numeric | `duracao_min / 60` |
| `duracao_minutos` | integer | Valor bruto da fonte |
| `kpi_status_int` | smallint | -1 isento/desconhecido, 0 dentro do prazo, 1 violou |
| `target_risco_sla` | smallint | 0/1 — variável alvo do classificador de risco |
| `exige_intervencao` | boolean | Sempre `true` (pós-filtro) |
| `possui_pai` | boolean | Tem `incidente_pai` preenchido |
| `horas_ate_resolucao` | numeric (nulo) | Horas entre abertura e resolução técnica |
| `foi_resolvido` | boolean | `resolvido_at` preenchido |
| `is_filho_de_problema` | boolean | Igual a `possui_pai` |
| `triagem_incompleta` | boolean | Subcategoria não preenchida na origem |
| `fechado_sem_tecnico` | boolean | Sempre `false` nesta base (ver `docs/modelo-dimensional.md`) |
| `excedeu_tempo_esperado` | boolean | Duração > threshold da prioridade |
| `score_risco_operacional` | smallint | 0-8, soma de fatores de risco |
| `aberto_at` | timestamp | |
| `resolvido_at` | timestamp (nulo) | |
| `encerrado_at` | timestamp | |

## Marts de features para ML (schema `ml`)

Espelham as antigas marts dbt do projeto AWS (mesma estrutura dos parquets em
`data/raw/`). Populadas por `notebooks/05_ml_feature_marts.ipynb` a partir de
`staging.incidentes_silver`. **Divergências de `dw.fct_incidentes`**:
- `target_risco_sla`/`score_risco_operacional` aqui usam o valor já calculado
  pela Silver, sem o clamp final de `-1`→`0` que `dw.fct_incidentes` aplica —
  por isso `target_risco_sla` pode valer `-1` (KPI desconhecido, sem
  heurística aplicável) nestas tabelas, o que nunca acontece em
  `dw.fct_incidentes`. O threshold de P2 usado na heurística (4h) é o mesmo
  valor oficial usado em `dw.fct_incidentes` desde a correção de 2026-08-21
  (ver `docs/modelo-dimensional.md`) — não é mais uma divergência.
- `excedeu_tempo_esperado` (aqui) / `target_excedeu_tempo` (em
  `ml_sla_classification_dataset`) **ainda usam os thresholds antigos e
  incorretos** (P1=4h/P2=8h/P3=24h/P4=72h, sem meta para P5) — só
  `dw.fct_incidentes.excedeu_tempo_esperado` foi corrigido. Esta coluna é o
  rótulo de treino do XGBoost (`ml.fct_risco_incidente`); corrigi-la exige
  retreinar o modelo, então a correção foi deliberadamente adiada para uma
  tarefa separada (ver `docs/modelo-dimensional.md`).

### `ml.ml_base_features`
1 linha por incidente (41.441, mesma população de `staging.incidentes_silver`).
Equivalente a `int_incidents_enriched` / `ml_base_features.parquet`.

| Coluna | Tipo | Observação |
|---|---|---|
| `incident_id` | text (PK) | |
| `incidente_pai` | text (nulo) | |
| `aberto_por` | text | |
| `prioridade` | text | |
| `prioridade_num` | int | |
| `produto` | text | |
| `categoria` | text | |
| `subcategoria` | text | |
| `grupo_designado` | text | |
| `item_configuracao` | text (nulo) | Único campo trazido via join com `public.incidentes` — a Silver não carrega |
| `status` | text | |
| `codigo_fechamento` | text | |
| `entrou_kpi` | boolean | |
| `kpi_violado` | boolean (nulo) | |
| `kpi_status_int` | smallint | -1/0/1 |
| `possui_pai` | boolean | |
| `exige_intervencao` | boolean | Sempre `true` (grão já filtrado) |
| `target_risco_sla` | smallint | -1/0/1 — ver nota de divergência acima |
| `duracao_horas` / `duracao_segundos` | numeric / bigint | |
| `aberto_at` / `resolvido_at` (nulo) / `encerrado_at` | timestamp | |
| `data_abertura` | date | |
| `hora_abertura`, `dia_semana_num`, `semana_ano`, `mes_abertura`, `trimestre`, `ano_mes` | int/text | |
| `turno_abertura` | text | |
| `fora_horario_comercial`, `abriu_fim_de_semana` | boolean | |
| `horas_ate_resolucao` | numeric (nulo) | |
| `foi_resolvido`, `is_filho_de_problema`, `triagem_incompleta`, `fechado_sem_tecnico`, `excedeu_tempo_esperado` | boolean | |
| `score_risco_operacional` | smallint | 0-8 |

### `ml.ml_cluster_dataset`
1 linha por incidente (41.441). Subconjunto causa+efeito de `ml_base_features`
para o K-Means — sem risco de vazamento (clusterização descreve o passado).
Colunas: `incident_id` (PK/FK `ml_base_features`), `prioridade_num`,
`grupo_designado`, `categoria`, `subcategoria`, `produto`, `hora_abertura`,
`turno_abertura`, `dia_semana_num`, `fora_horario_comercial`,
`abriu_fim_de_semana`, `mes_abertura`, `trimestre`, `possui_pai`,
`is_filho_de_problema`, `triagem_incompleta`, `duracao_horas`,
`horas_ate_resolucao`, `foi_resolvido`, `excedeu_tempo_esperado`,
`fechado_sem_tecnico`, `target_risco_sla`, `kpi_status_int`,
`score_risco_operacional`, `duracao_horas_scaled` (nulo — preenchido pelo
notebook de clustering), `cluster_id` (nulo — idem).

### `ml.ml_sla_classification_dataset`
1 linha por incidente (41.441). Livre de vazamento de dados — só features
disponíveis no minuto 0 de abertura. Colunas: `incident_id` (PK/FK
`ml_base_features`), `prioridade_num`, `grupo_designado`, `categoria`,
`subcategoria`, `possui_pai`, `is_filho_de_problema`, `triagem_incompleta`,
`hora_abertura`, `dia_semana_num`, `turno_abertura`,
`fora_horario_comercial`, `abriu_fim_de_semana`, `semana_ano`,
`mes_abertura`, `duracao_horas`, `target_risco_sla` (smallint, target 1),
`target_excedeu_tempo` (boolean, target alternativo).

### `ml.ml_forecast_dataset`
1 linha por dia (365). Agregação de `ml_base_features` no grão de dia, para o
Prophet. Colunas: `data_abertura` (PK), `dia_semana_num`, `semana_ano`,
`mes_abertura`, `trimestre`, `ano_mes`, `is_fim_de_semana`, `total_chamados`,
`total_p1`..`total_p4`, `total_criticos`, `total_violacoes_sla`,
`pct_violacao_sla`, `pressao_operacional_dia`, `score_risco_medio_dia`,
`media_horas_resolucao`.

## Saídas dos modelos de ML (schema `ml`)

Populadas pelos notebooks `forecast_incidentes_revisado.py`,
`model_clustering_kmeans_Revisado.ipynb` e `model_risk_xgboost_.ipynb`, lendo
das marts acima e gravando no banco `fiap`.

### `ml.fct_previsao_diaria_total`
Previsão Prophet de volume total diário, D+1 a D+7. **Append** (não
truncate+insert) — cada `origem` é uma execução nova, mantida para comparar
previsto x realizado depois. Colunas: `previsao_total_sk` (PK), `origem`,
`h`, `horizonte` ('D+1'..'D+7'), `ds`, `yhat`, `yhat_lower`, `yhat_upper`,
`modelo_versao`, `data_execucao`. `UNIQUE(origem, ds)`.

### `ml.fct_previsao_prioridade` / `ml.fct_previsao_categoria`
Quebra do forecast total por prioridade/categoria via **split proporcional
histórico** (não é um Prophet por corte — `share_historico` é a fração do
volume histórico daquele corte, aplicada sobre `yhat` do total). Mesmas
colunas de controle (`origem`, `h`, `horizonte`, `ds`, `modelo_versao`,
`data_execucao`) + `prioridade_num`/`categoria`, `share_historico`,
`yhat_prioridade`/`yhat_categoria`. `categoria` é texto simples (não FK para
`dw.dim_produto_categoria` — grão mais fino do que a tela "Top 5 categorias"
precisa).

### `ml.dim_cluster`
Taxonomia curada dos 4 clusters do K-Means (A-D), vinda do mockup
`docs/design/aiops_dashboard_redesign.html`. Não é reescrita a cada execução
do notebook — edição manual se o significado de um cluster mudar. Colunas:
`cluster_id` (PK, 'A'-'D'), `nome_perfil`, `descricao_curta`, `tags` (CSV),
`cor_hex`, `modelo_versao_referencia`.

### `ml.fct_perfil_cluster`
Métricas agregadas por cluster, recarregadas por completo a cada execução do
K-Means (truncate+insert). Alimenta o gráfico de bolhas e os cards da tela
Clusters. Colunas: `perfil_cluster_sk` (PK), `cluster_id` (FK `dim_cluster`),
`modelo_versao`, `data_execucao`, `n_incidentes`, `pct_volume`,
`duracao_media_horas`, `taxa_resolucao_pct`, `taxa_sla_violado_pct`.

### `ml.fct_importancia_feature`
Importância global de features do XGBoost (|SHAP| médio por coluna, ou gain
do XGBoost se o SHAP não estiver disponível), recarregada por completo a
cada execução. Colunas: `importancia_sk` (PK), `modelo_versao`,
`data_execucao`, `feature`, `importance_pct`, `rank`.

### `ml.fct_importancia_conceito`
Mesma importância, agrupada por **conceito de negócio** (ex: "Dia da
semana", "Categoria e triagem") em vez de coluna crua — é essa granularidade
que o painel "Fatores" do mockup mostra (`ml.fct_importancia_feature` é a
referência técnica por coluna). Só é populada quando o SHAP roda de verdade
(fica vazia no fallback por gain do XGBoost, que não tem agrupamento por
conceito). Colunas: `importancia_conceito_sk` (PK), `modelo_versao`,
`data_execucao`, `conceito`, `n_colunas`, `importance_pct`, `rank`.

### `ml.fct_risco_incidente`
Score de risco de violação de SLA por incidente (XGBoost calibrado),
cobertura total de `dw.fct_incidentes` (41.441 linhas), recarregada por
completo a cada execução. Colunas: `incident_sk` (PK, FK
`dw.fct_incidentes`), `incident_id`, `modelo_versao`, `data_execucao`,
`score_bruto`, `score_calibrado`, `threshold_aplicado`, `predicao_risco`,
`faixa_risco` (Baixo/Moderado/Alto/Critico), `motivo_principal`,
`escopo_modelo` (validado/extrapolado), `particao` (treino/validacao/teste/
fora_do_escopo), `y_real` (nulo fora do escopo validado).

### `ml.fct_shap_incidente`
Contribuições SHAP por feature, só para os `TOP_N_SHAP` (30) incidentes de
maior `score_calibrado` a cada execução — não a população toda. Alimenta o
painel "Valores SHAP" da tela Fatores, reinterpretado como explicação dos
incidentes de maior risco (não do forecast de volume — decisão registrada em
`docs/modelo-dimensional.md`). Colunas: `shap_sk` (PK), `incident_sk` (FK
`dw.fct_incidentes`), `incident_id`, `modelo_versao`, `data_execucao`,
`feature`, `shap_value` (log-odds, sinal preservado), `direcao`
(aumenta_risco/reduz_risco), `rank_abs`, `score`.
