# Dicionário de dados

Referência rápida das tabelas do banco `fiap`. Para o raciocínio por trás do
desenho (grão, filtros, adaptações), ver `docs/schema-fonte-incidentes.md` e
`docs/modelo-dimensional.md` — este documento é só a lista de colunas.

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
| `threshold_sla_horas` | integer (nulo) | Meta contratual: P1=4h, P2=8h, P3=24h, P4=72h; P5 sem meta |

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
