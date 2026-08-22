# Modelo dimensional — schema `dw` (banco `fiap`)

Construído a partir de `public.incidentes` via `notebooks/04_dw_star_schema.ipynb`
(SQL puro via SQLAlchemy) e `etl/transform.py` (equivalente em pandas) — os
dois implementam a mesma lógica e devem ser mantidos em paridade.

## Grão da fato

**`dw.fct_incidentes`: 1 linha = 1 incidente (chamado)** que exigiu esforço
humano real, aberto a partir de 2025-01-01.

Filtros aplicados na carga:
- `status <> 'Sem Intervenção'` — remove alertas de monitoramento que se
  autorresolvem (~65% da tabela bruta, ~81k/122k linhas).
- `aberto >= '2025-01-01'`.

Resultado: 122.543 linhas brutas → **41.441 linhas na fato**.

## Dimensões

| Tabela | Grão | Linhas carregadas |
|---|---|---|
| `dim_produto_categoria` | combinação distinta (produto, categoria, subcategoria) | 921 |
| `dim_grupo` | grupo_designado | 16 |
| `dim_tempo` | dia de calendário com incidente | 365 |
| `dim_status` | combinação distinta (status, codigo_fechamento) | 35 |
| `dim_prioridade` | prioridade_num, com bucket/criticidade/threshold_sla_horas | 5 |
| `dim_abertura` | timestamp distinto de abertura (turno, hora, fora do horário comercial) | 41.364 |

## Decisões de design e correções

1. **Corte de histórico**: `aberto >= 2025-01-01` (decisão do usuário —
   descarta ~1.100 linhas de 2023-2024, período sem esforço operacional
   representativo).
2. **`fechado_sem_tecnico`**: regra `codigo_fechamento IN ('Resolvido pelo
   Usuário','Sem Descrição')`. Esse vocabulário não existe em
   `public.incidentes` (aqui os códigos são outros: "Falha de Aplicação",
   "Sem retorno do solicitante" etc.) — a coluna é sempre `False` nesta
   base. Mantida por consistência com o teste automatizado
   (`test_fechado_sem_tecnico_vocabulario_local_sempre_false`), que existe
   justamente para deixar esse comportamento explícito em vez de um valor
   morto silencioso.
3. ~~Heurística de `target_risco_sla` (camada 2) corrigida para usar 8h como
   threshold de P2~~ — **essa "correção" estava errada, revertida em
   2026-08-21.** Ver seção "Correção de thresholds de SLA" abaixo.
4. **Chaves MD5 com COALESCE consistente**: dimensão e fato usam a mesma
   fórmula de chave (incluindo o tratamento de nulos em produto/categoria/
   subcategoria e status/codigo_fechamento). Uma versão anterior computava a
   chave de forma diferente na dimensão e na fato para esses casos, o que
   geraria FK nula para ~63% das linhas (produto/categoria nulos). Corrigido
   — 0 FKs órfãs nas 6 dimensões, verificado após a carga.

## Correção de thresholds de SLA (2026-08-21)

`dw.dim_prioridade.threshold_sla_horas` e as colunas derivadas dele
(`excedeu_tempo_esperado`, `target_risco_sla`, `score_risco_operacional`)
estavam com valores incorretos desde a construção original do `dw`.

| Prioridade | Valor errado (até 2026-08-21) | Valor oficial (Dicionário de Dados do desafio) |
|---|---|---|
| 1 - Crítica | 4h | 4h (já estava certo) |
| 2 - Alta | 8h | **4h** |
| 3 - Média | 24h | **12h** |
| 4 - Baixa | 72h | **24h** |
| 5 - Muito Baixa | sem meta (`NULL`) | **96h** |

**Causa raiz**: o dict `SLA_THRESHOLD_HORAS = {1: 4, 2: 8, 3: 24, 4: 72}`
(`etl/transform.py`, replicado em SQL no notebook `04_dw_star_schema.ipynb`)
foi definido sem conferir contra o Dicionário de Dados oficial do desafio.
Uma camada anterior do pipeline (a heurística da Silver) já usava o valor
certo de P2 (4h) para `target_risco_sla` (camada 2,
`notebooks/03_bronze_silver_transformacao.ipynb`) — mas ao montar o `dw`
nesta adaptação, esse heurístico foi "corrigido" para 8h **na direção
errada**, achando que o `threshold_sla_horas` de `dim_prioridade` (que já
estava errado) era a fonte da verdade. O erro só existia em `dw.*`:
`ml.ml_base_features.target_risco_sla` lê
`staging.incidentes_silver.Target_Risco_SLA` sem recalcular, então sempre
teve o valor de P2 correto (4h); já `excedeu_tempo_esperado`/
`target_excedeu_tempo` (recalculado tanto em `dw.fct_incidentes` quanto em
`ml.ml_base_features`, notebook 05) estava errado nos dois lugares.

**Escopo da correção aplicada**: `dw.dim_prioridade.threshold_sla_horas` e
as 3 colunas dependentes em `dw.fct_incidentes` (`target_risco_sla`,
`excedeu_tempo_esperado`, `score_risco_operacional`) foram recalculadas e
atualizadas via `UPDATE` direto (não truncate+insert — ver nota abaixo),
41.441 linhas, 0 FKs órfãs após a correção. `etl/transform.py` e o notebook
04 foram corrigidos na fonte para não reintroduzir o valor errado numa
próxima recarga.

**`ml.*` — resolvido em 2026-08-22.** `ml.ml_base_features.excedeu_tempo_esperado`
e `ml.ml_sla_classification_dataset.target_excedeu_tempo` (notebook 05,
célula 7) foram corrigidos para os thresholds oficiais — essa é justamente a
coluna usada como rótulo de treino do XGBoost, então a correção exigiu
retreinar o modelo, não só recalcular a mart. Sequência executada:
`05_ml_feature_marts.ipynb` → `model_clustering_kmeans_Revisado.ipynb` →
`model_risk_xgboost_.ipynb`, nessa ordem, ponta a ponta (0 erros nos três).
Distribuição de `target_excedeu_tempo` por prioridade após a correção bate
exatamente com a de `dw.fct_incidentes.excedeu_tempo_esperado` (mesmo
threshold agora nos dois lugares). `ml.fct_perfil_cluster`/`ml.fct_risco_incidente`/
`ml.fct_importancia_feature`/`ml.fct_importancia_conceito`/`ml.fct_shap_incidente`
recarregados com `data_execucao` fresco — cluster K-Means não muda
(`excedeu_tempo_esperado` não é feature de treino do K-Means, só estatística
pós-hoc), a importância de conceito no XGBoost sim (novo rótulo, novo
ranking: "Prioridade do chamado" segue líder, mas "Categoria e triagem"
sobe para 2º lugar).

**Bug de infraestrutura descoberto durante a correção — ~~resolvido em
2026-08-22~~**: `TRUNCATE dw.fct_incidentes` (usado tanto por
`etl/transform.py` quanto pelo notebook `04_dw_star_schema.ipynb`) passou a
falhar com `FeatureNotSupported` desde que `ml.fct_risco_incidente` e
`ml.fct_shap_incidente` ganharam FK para `dw.fct_incidentes` (migrations
021/022, Etapa 4) — TRUNCATE não permite referências de FK sem CASCADE, e
um CASCADE ali apagaria as saídas do XGBoost/SHAP como efeito colateral.

Correção: os dois caminhos de recarga passaram de truncate+insert para
**UPSERT** (`INSERT ... ON CONFLICT (<sk>) DO UPDATE SET ...`) nas 6
dimensões + fato — nunca mais há `TRUNCATE` em `dw.*`. Toda `*_sk` é `MD5`
determinístico de uma chave natural estável, então UPSERT é idempotente: a
mesma linha de entrada sempre resolve para o mesmo PK.
`etl/transform.py::carregar()` usa um helper de staging table (escreve o
DataFrame numa tabela descartável, um único `INSERT...SELECT...ON CONFLICT`
contra a real, tudo na mesma transação); o notebook usa `ON CONFLICT`
direto no `INSERT...SELECT` de cada célula.

Validado rodando os dois caminhos **duas vezes seguidas**: `dw.fct_incidentes`
e as 6 dimensões ficam com a mesma contagem nas duas rodadas (41.441 na
fato), e `ml.fct_risco_incidente`/`ml.fct_shap_incidente` ficaram com
`data_execucao` **idêntico** antes e depois — prova de que a recarga não as
tocou. 0 FKs órfãs.

**Efeito colateral descoberto**: como UPSERT nunca faz `DELETE`, a primeira
rodada revelou 3 linhas órfãs em `dw.dim_status` (combinações de
`status`/`codigo_fechamento` que não existem mais em
`staging.incidentes_silver`, provavelmente de uma carga anterior a este
histórico) — sem nenhum `dw.fct_incidentes` referenciando-as, então
removidas manualmente uma única vez. **Premissa aceita daqui em diante**:
esta carga não apaga uma `*_sk` que deixou de aparecer numa extração nova
— população é histórica/imutável na prática. Se uma dimensão inteira
precisar de limpeza de novo, é uma operação manual pontual, não automática
(um `DELETE` automático bateria na mesma trava de FK que motivou este fix,
para `dw.fct_incidentes`).

## `dw.ref_meta_sla_anual` (2026-08-21)

Tabela de referência (não é fato de ML nem dimensão clássica) com as metas
anuais de SLA por prioridade, definidas pelo Dicionário de Dados oficial do
desafio — **dado real de negócio, não placeholder**. Só existem metas para
P2 (Alta) e P3 (Média), em dois indicadores independentes:

- `ola_quebrado` — contagem anual de incidentes que violaram o SLA;
- `volume_tratado` — contagem anual de incidentes tratados.

Cada indicador tem 6 faixas contíguas (sem sobreposição) com um
`pct_atingimento` associado (150/125/100/75/50/0%) e uma `ordem_faixa`
(1 = melhor, 6 = pior). `faixa_min`/`faixa_max` ficam `NULL` só nas pontas
abertas (`< N` e `> N`); as demais faixas são inclusivas dos dois lados —
ex.: P2/`ola_quebrado` tem `< 31` como `(NULL, 30)`, `31 a 35` como
`(31, 35)`, e assim por diante, até `> 53` como `(54, NULL)`.

A meta é definida em **contagem anual absoluta**, mas o indicador é medido
mensalmente: não existe uma meta mensal própria — o acompanhamento mensal é
a posição acumulada do ano-corrente frente a essas faixas anuais.

**Lookup de faixa**: `etl/ref_meta_sla.py`, função
`faixa_meta_sla(engine, prioridade_num, indicador, contagem_acumulada)`.
É uma **regra de negócio determinística** (comparação de intervalo, sem
nenhum modelo estatístico envolvido) — nunca deve ser apresentada como
"previsão" ou saída de IA no dashboard. 8 testes em
`tests/test_ref_meta_sla.py` cobrindo os limites de faixa e as duas pontas
abertas.

**Fora de escopo desta tabela**: a projeção/probabilidade de fechar o ano
em determinada faixa (ex.: "61% de chance de bater a meta") depende de uma
decisão de metodologia (projeção linear? Poisson?) ainda não tomada — fica
para quando a Etapa 5 (API) implementar o endpoint de KPI.

## Caveats de qualidade de dado (herdados da fonte, não corrigidos)

- `duracao_min`/`duracao_horas` têm outliers extremos (ver
  `docs/schema-fonte-incidentes.md`) — médias de duração por prioridade
  ficam infladas por esses outliers; use mediana ou filtro de outliers nos
  painéis do dashboard, não média simples.
- `incidente_pai` tem referências que não resolvem para um `numero`
  existente nesta extração — `possui_pai`/`is_filho_de_problema` refletem
  isso (o incidente *tem* um pai referenciado), mas o join para o pai em si
  pode não encontrar linha.

## Como recarregar

```bash
./venv/bin/python -m etl.transform
```

Idempotente: trunca e recarrega `dw.*` a cada execução.
