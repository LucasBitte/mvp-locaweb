# Modelo dimensional — schema `dw` (banco `fiap`)

Adaptado do star schema do projeto original em AWS (`notebooks/04_dbt_transform_silver_to_gold_marts.ipynb`),
substituindo S3 bronze/silver + dbt sobre RDS por leitura direta de
`public.incidentes` + `etl/transform.py` (SQL puro + Python, sem dbt).

## Grão da fato

**`dw.fct_incidentes`: 1 linha = 1 incidente (chamado)** que exigiu esforço
humano real, aberto a partir de 2025-01-01.

Filtros aplicados na carga (mesmos do projeto original):
- `status <> 'Sem Intervenção'` — remove alertas de monitoramento que se
  autorresolvem (~65% da tabela bruta, ~81k/122k linhas).
- `aberto >= '2025-01-01'`.

Resultado: 122.543 linhas brutas → **41.441 linhas na fato** (bate com o
volume reportado pelo notebook original rodando sobre a base AWS).

## Dimensões

| Tabela | Grão | Linhas carregadas |
|---|---|---|
| `dim_produto_categoria` | combinação distinta (produto, categoria, subcategoria) | 921 |
| `dim_grupo` | grupo_designado | 16 |
| `dim_tempo` | dia de calendário com incidente | 365 |
| `dim_status` | combinação distinta (status, codigo_fechamento) | 35 |
| `dim_prioridade` | prioridade_num, com bucket/criticidade/threshold_sla_horas | 5 |
| `dim_abertura` | timestamp distinto de abertura (turno, hora, fora do horário comercial) | 41.364 |

## Adaptações em relação ao projeto original

1. **Corte de histórico**: mantido `aberto >= 2025-01-01`, replicando o
   original (decisão do usuário — descarta ~1.100 linhas de 2023-2024).
2. **`fechado_sem_tecnico`**: mantida a regra literal do original
   (`codigo_fechamento IN ('Resolvido pelo Usuário','Sem Descrição')`).
   Esse vocabulário não existe em `public.incidentes` (aqui os códigos são
   outros: "Falha de Aplicação", "Sem retorno do solicitante" etc.) — a
   coluna é sempre `False` nesta base. Mantida por fidelidade à regra
   original, coberta por teste (`test_fechado_sem_tecnico_vocabulario_local_sempre_false`).
3. **Heurística de `target_risco_sla` (camada 2)**: ~~corrigida para usar
   8h como threshold de P2~~ — **essa "correção" estava errada, revertida em
   2026-08-21.** Ver seção "Correção de thresholds de SLA" abaixo.
4. **Chaves MD5 com COALESCE consistente**: dimensão e fato usam a mesma
   fórmula de chave (incluindo o tratamento de nulos em produto/categoria/
   subcategoria e status/codigo_fechamento). O original computava a chave
   de forma diferente na dimensão e na fato para esses casos, o que geraria
   FK nula para ~63% das linhas (produto/categoria nulos). Corrigido — 0
   FKs órfãs nas 6 dimensões, verificado após a carga.

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
(`etl/transform.py`, replicado em SQL no notebook 04) foi definido sem
conferir contra o Dicionário de Dados oficial do desafio. O projeto AWS
original já usava o valor certo de P2 (4h) na heurística de
`target_risco_sla` (camada 2, `notebooks/03_bronze_silver_transformacao.ipynb`)
— mas ao montar o `dw` nesta adaptação, esse heurístico foi "corrigido" para
8h **na direção errada**, achando que o `threshold_sla_horas` de
`dim_prioridade` (que já estava errado) era a fonte da verdade. O erro só
existia em `dw.*`: `ml.ml_base_features.target_risco_sla` lê
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

**`ml.*` não foi tocado nesta correção.** `ml.ml_base_features.excedeu_tempo_esperado`
e `ml.ml_sla_classification_dataset.target_excedeu_tempo` continuam com o
threshold antigo — essa é justamente a coluna usada como rótulo de treino do
XGBoost (`ml.fct_risco_incidente`), então corrigi-la exige retreinar o
modelo, não só recalcular a mart. Decisão registrada: retreino fica para uma
tarefa separada.

**Bug de infraestrutura descoberto durante a correção**: `TRUNCATE
dw.fct_incidentes` (usado tanto por `etl/transform.py` quanto pelo notebook
04) passou a falhar com `FeatureNotSupported` desde que `ml.fct_risco_incidente`
ganhou uma FK para `dw.fct_incidentes` (migration 021, Etapa 4) — TRUNCATE
não permite referências de FK sem CASCADE, e um CASCADE ali apagaria as
41.441 linhas de score do XGBoost como efeito colateral. Por isso esta
correção foi aplicada via `UPDATE` cirúrgico em vez de rodar o reload padrão
(`python -m etl.transform`). **Os dois scripts de reload de `dw.*` estão
com essa trava pré-existente e não puderam ser re-executados ponta a ponta
para validar esta correção** — ela foi validada com queries diretas
antes/depois no banco (ver PR) e com o notebook 04 revisado apenas na
fonte, não executado. Fica como débito técnico a resolver antes da próxima
vez que `dw.*` precisar de uma recarga completa (truncate+insert real).

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
