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
3. **Heurística de `target_risco_sla` (camada 2)**: corrigida para usar
   8h como threshold de P2 (o original usava 4h ali, inconsistente com o
   próprio `threshold_sla_horas` de P2 definido em `dim_prioridade`).
4. **Chaves MD5 com COALESCE consistente**: dimensão e fato usam a mesma
   fórmula de chave (incluindo o tratamento de nulos em produto/categoria/
   subcategoria e status/codigo_fechamento). O original computava a chave
   de forma diferente na dimensão e na fato para esses casos, o que geraria
   FK nula para ~63% das linhas (produto/categoria nulos). Corrigido — 0
   FKs órfãs nas 6 dimensões, verificado após a carga.

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
