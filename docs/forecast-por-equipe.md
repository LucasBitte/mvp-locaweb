# Previsão de demanda por equipe — `ml.fct_previsao_grupo`

> Documentação única do modelo de forecast por equipe (`grupo_designado`).
> Complementa (não substitui) as entradas equivalentes em
> `docs/dicionario-dados.md` (coluna a coluna) e `docs/modelo-dimensional.md`
> (seção "`ml.fct_previsao_grupo` — corte A/B/C por equipe").

## 1. Por que este modelo existe

O desafio pede explicitamente previsão de demanda **por equipe**
(`dw.dim_grupo`, 16 equipes), para "evitar sobrecarga nas equipes". Até
esta tarefa só existia forecast de volume total (Prophet) mais dois splits
proporcionais — por prioridade e por categoria — nenhuma quebra por equipe.

`fct_previsao_prioridade`/`fct_previsao_categoria` **não são modelos
próprios**: são o `yhat` do total redistribuído por `share_historico`
(participação histórica do corte no volume). Aplicar a mesma técnica
ingenuamente a 16 equipes não atenderia ao pedido do desafio — equipes
grandes têm volume e regularidade suficientes para um modelo dedicado de
verdade; equipes pequenas não. Por isso a arquitetura é **híbrida**.

## 2. Arquitetura — visão geral

```
ml.ml_base_features (grão: incidente)
        │
        ├─ agregação diária por (grupo_designado, data_abertura)
        │  calendário completo, zero-fill
        │  → notebooks/06_forecast_investigacao_equipe.ipynb (Fase 0)
        │
        ▼
  corte de viabilidade por média diária ────────────────────────────┐
        │                                                            │
   ┌────┴────┐                                              ┌───────┴──────┐
   │ Grupo A │  média ≥ 5/dia                                │   Grupo C    │
   │ Grupo B │  1 ≤ média < 5/dia                             │ média < 1/dia│
   └────┬────┘                                              └───────┬──────┘
        │  notebooks/forecast_equipe.py (Fase 1)                    │
        ▼                                                            ▼
  Prophet diário individual                          split proporcional do yhat
  (holidays = storm days)                             de ml.fct_previsao_diaria_total
        │                                                            │
        ├─ Grupo B: veredito vs. melhor baseline (±5% MAE)           │
        │  "PERDE PARA" → agrega semanal, distribui por dow          │
        │  "EMPATA"/"SUPERA" → mantém diário                         │
        │                                                            │
        ▼                                                            ▼
              ml.fct_previsao_grupo (16 equipes × D+1..D+7, append por origem)
```

Fonte de dado: `ml.ml_base_features` — mesma linhagem que alimenta
`ml.ml_forecast_dataset` (fonte real do Prophet do total), não
`dw.fct_incidentes` (teve divergência de threshold identificada na correção
de SLA, ver `docs/modelo-dimensional.md`).

## 3. Corte de viabilidade (Fase 0 — investigação)

Notebook: `notebooks/06_forecast_investigacao_equipe.ipynb` (executado,
resultados salvos nas células). Métrica: **média diária de
incidentes/equipe** sobre o calendário completo 2025-01-01 a 2025-12-31,
com `% de dias zerados` e **coeficiente de variação** (desvio padrão /
média) como desempate.

Dois cotovelos claros no volume total por equipe:

| Equipe | Volume total | Média/dia | % dias zero | CV |
|---|---|---|---|---|
| Team14 | 17.107 | 46,87 | 0,00% | 0,58 |
| Team11 | 9.688 | 26,54 | 1,10% | 0,65 |
| Team05 | 7.439 | 20,38 | 3,56% | 1,29 |
| Team09 | 2.897 | 7,94 | 1,92% | 0,74 |
| — cotovelo 1 (queda de ~3,25×) — |||||
| Team12 | 892 | 2,44 | 35,07% | 2,32 |
| Team03 | 803 | 2,20 | 21,92% | 1,08 |
| Team17 | 708 | 1,94 | 22,74% | 1,10 |
| Team02 | 472 | 1,29 | 38,08% | 1,26 |
| — cotovelo 2 (maioria dos dias sem chamado a partir daqui) — |||||
| Team10 | 343 | 0,94 | 71,23% | 3,87 |
| Team16 | 244 | 0,67 | 64,93% | 2,30 |
| Team01 | 229 | 0,63 | 66,58% | 2,43 |
| Team15 | 215 | 0,59 | 86,30% | 11,16 |
| Team07 | 182 | 0,50 | 66,85% | 1,70 |
| Team08 | 124 | 0,34 | 74,25% | 2,21 |
| Team04 | 81 | 0,22 | 89,59% | 4,15 |
| Team06 | 17 | 0,05 | 96,99% | 7,14 |

| Grupo | Critério | Equipes | Técnica |
|---|---|---|---|
| **A** | média diária ≥ 5 | Team14, Team11, Team05, Team09 | Prophet individual |
| **B** | 1 ≤ média diária < 5 | Team12, Team03, Team17, Team02 | Prophet diário → semanal se necessário |
| **C** | média diária < 1 | Team10, Team16, Team01, Team15, Team07, Team08, Team04, Team06 | split proporcional |

## 4. Grupo A — Prophet individual por equipe

Mesma metodologia/hiperparâmetros de base do forecast total
(`notebooks/forecast_incidentes_revisado.py`, reaproveitados por import em
`notebooks/forecast_equipe.py`): `weekly_seasonality=True`,
`yearly_seasonality=False` (menos de um ciclo anual completo de
histórico), `changepoint_range=1.0`, `changepoint_prior_scale=0.05`,
`interval_width=0.80`. Cada equipe: reindexação em calendário completo
(zero-fill), backtest de origem móvel, previsão D+1..D+7 com
`yhat`/`yhat_lower`/`yhat_upper`.

### Achado: `Team05` e o "storm day" — investigado antes do treino

`Team05` chamou atenção na Fase 0 por CV=1,29 (desvio padrão > média),
sinal de outlier. Investigação em `ml.ml_base_features` (coluna
`incidente_pai`), antes de treinar essa equipe: os dias de maior volume são
dominados por um **único incidente-pai gerando uma rajada de filhos no
mesmo dia, para a mesma equipe**. Exemplo: 2025-06-26, `INC8445074` sozinho
gerou 227 dos 270 chamados do dia (84%).

Isso se repete em **22 dias distintos** do ano
(`notebooks/forecast_equipe.py`, função `detectar_storm_days`; regra: um
`incidente_pai` não-`'Independente'` responde por ≥40% do volume do dia da
equipe **e** o volume do dia é ≥2× a mediana diária histórica da própria
equipe), cada vez via um pai **diferente e sem relação** com os anteriores.

Conclusão: **não é bug de atribuição de `grupo_designado`**, é um padrão
operacional real e recorrente — mas também **não é um evento de calendário
fixo** (datas diferentes a cada ocorrência), então não é um "feriado" anual
verdadeiro no sentido do Prophet.

**Tratamento aplicado**: os dias detectados entram como `holidays` do
Prophet — data avulsa, `lower_window=0`/`upper_window=0`, **sem ocorrência
futura**. Isso absorve o choque pontual sem distorcer a tendência/
changepoints do modelo, e sem projetar o efeito para nenhuma data futura
(um "storm day" de 2025 não tem efeito nenhum sobre uma previsão de 2026 —
só afeta datas presentes na própria tabela de `holidays`). O mesmo
mecanismo é aplicado a todas as equipes de Grupo A (e às de Grupo B que
ficam diárias — seção 5), recalculado a cada execução a partir do dado
vivo, nunca uma lista fixa de datas hardcoded.

Para equipes de mediana baixa, o filtro "≥2× mediana" sozinho marcaria
ruído comum como "storm" (ex.: `Team12`, mediana 2/dia, ~14% dos dias
cruzam esse limiar). Por isso o piso mínimo de incidentes-filho no mesmo
pai (`n_pai_min`) é mais estrito para Grupo B (`≥10`) do que para Grupo A
(`≥1`, onde o volume absoluto já torna o filtro confiável sozinho).

### Resultado — validação (holdout, origem móvel)

| Equipe | MAE (Prophet) | WAPE% | Veredito vs. melhor baseline |
|---|---|---|---|
| Team14 | 16,89 | 32,6% | EMPATA (+0,6%) |
| Team11 | 5,72 | 29,1% | EMPATA (-1,2%) |
| Team05 | 11,11 | 62,8% | EMPATA (-4,2%) |
| Team09 | 2,83 | 42,3% | SUPERA (-5,7%) |

Veredito reaproveita a lógica já existente no script do total: compara MAE
do Prophet contra o melhor baseline (médias móveis, mediana por
dia-da-semana etc.) com margem de ±5%. Nenhuma equipe supera o baseline por
margem folgada — três empatam. Isso é esperado (volume por equipe é mais
ruidoso que o total agregado) e não invalida o modelo: o Prophet ganha em
cobertura de intervalo (76–92%) e é a única técnica que produz
`yhat_lower`/`yhat_upper` por equipe — o baseline de mediana não produz
intervalo nenhum.

## 5. Grupo B — diário primeiro, semanal só se necessário

Mesmo pipeline diário do Grupo A rodado primeiro. Decisão de fallback
**por equipe**, não por grupo inteiro — reaproveita o mesmo veredito
(±5% de MAE vs. melhor baseline): só cai para semanal quando o diário
"PERDE PARA" claramente.

| Equipe | Veredito diário | Decisão |
|---|---|---|
| Team12 | SUPERA (-6,3%) | diário (`prophet_individual`) |
| **Team03** | **PERDE PARA (+11,3%)** | **semanal (`prophet_semanal`)** |
| Team17 | SUPERA (-7,5%) | diário (`prophet_individual`) |
| Team02 | EMPATA (-0,5%) | diário (`prophet_individual`) |

Só `Team03` caiu para semanal — as outras três ficaram com
`metodo='prophet_individual'`, mesmo estando no "Grupo B" da investigação
inicial (o rótulo do grupo é sobre viabilidade de *tentativa*; o `metodo`
final gravado reflete o que realmente rodou).

**Mecânica do fallback semanal** (`rodar_semanal`/`distribuir_semana_em_dias`
em `notebooks/forecast_equipe.py`):
1. Agrega a série diária em semanas ISO (segunda a domingo), descarta
   semanas incompletas.
2. Treina Prophet na série semanal (`weekly_seasonality=False`,
   `yearly_seasonality=False` — não há sazonalidade sub-semanal a modelar
   num grão já semanal).
3. Prevê semanas suficientes para cobrir D+1..D+7 (pode cruzar 2 semanas
   ISO).
4. Distribui `yhat_semana` pelos 7 dias via **share histórico de
   dia-da-semana da própria equipe** (renormalizado para somar 1).
5. `yhat_lower`/`yhat_upper` diário: escala a **largura** do intervalo
   semanal pelo mesmo share (não o limite bruto) — mantém o intervalo
   diário centrado em `yhat_dia`, sem dar falsa precisão em dias de share
   baixo.

## 6. Grupo C — split proporcional do total

Sem modelo dedicado — série diária inviável (65–97% de dias sem chamado
algum). Mesma técnica de `ml.fct_previsao_categoria`: `share_historico` da
equipe (participação no volume total de `ml.ml_base_features`, todas as 16
equipes) aplicado sobre o `yhat` já persistido em
`ml.fct_previsao_diaria_total`, para a mesma `origem`.

`yhat_lower`/`yhat_upper` ficam `NULL` — não existe intervalo de incerteza
próprio para uma estimativa derivada. **Isso é explicitamente uma
estimativa, não uma previsão dedicada** — marcado via
`metodo='split_proporcional'`, visível tanto no banco quanto nesta
documentação (não há endpoint de API ainda — Etapa 5 não começou; quando
existir, o schema de resposta precisa expor `metodo`).

## 7. Schema — `ml.fct_previsao_grupo`

`db/migrations/025_ml_fct_previsao_grupo.sql`:

```sql
CREATE TABLE IF NOT EXISTS ml.fct_previsao_grupo (
    previsao_grupo_sk  text PRIMARY KEY,                              -- MD5(origem||ds||dim_grupo_sk)
    origem              date NOT NULL,                                 -- data de referência da execução
    h                   smallint NOT NULL,                             -- 1 a 7
    horizonte           text NOT NULL,                                 -- 'D+1'..'D+7'
    ds                  date NOT NULL,
    dim_grupo_sk        text NOT NULL REFERENCES dw.dim_grupo (dim_grupo_sk),
    yhat                numeric NOT NULL,
    yhat_lower          numeric,                                       -- NULL em split_proporcional
    yhat_upper          numeric,                                       -- NULL em split_proporcional
    metodo              text NOT NULL,                                 -- ver seção 8
    modelo_versao       text NOT NULL,                                 -- 'forecast_equipe_v1'
    data_execucao        timestamp NOT NULL,
    UNIQUE (origem, ds, dim_grupo_sk)
);
CREATE INDEX IF NOT EXISTS ix_fct_previsao_grupo_ds ON ml.fct_previsao_grupo (ds);
```

**Append, não truncate+insert** — igual às demais tabelas de previsão.
Idempotente por `origem`: `notebooks/forecast_equipe.py` faz
`DELETE ... WHERE origem = :o` seguido de `INSERT` a cada execução, então
rodar de novo para a mesma `origem` substitui, não duplica.

## 8. Coluna `metodo` — semântica completa

| Valor | Quando | Tem intervalo próprio? | Equipes (nesta execução) |
|---|---|---|---|
| `prophet_individual` | Grupo A sempre; Grupo B quando o diário empata/supera o baseline | Sim | Team14, Team11, Team05, Team09, Team12, Team17, Team02 |
| `prophet_semanal` | Grupo B quando o diário perde claramente do baseline | Sim (escalado da semana) | Team03 |
| `split_proporcional` | Grupo C sempre | Não (`yhat_lower`/`yhat_upper` = `NULL`) | Team10, Team16, Team01, Team15, Team07, Team08, Team04, Team06 |

Esse campo precisa ficar visível em qualquer consumo futuro (dashboard,
API) — o objetivo é o usuário do dashboard saber, por equipe, se aquele
número vem de um modelo dedicado ou de uma estimativa derivada.

## 9. Checagem de consistência com o total

`notebooks/forecast_equipe.py` roda, ao final, uma comparação diagnóstica
entre `SUM(yhat)` das 16 equipes e o `yhat` de `ml.fct_previsao_diaria_total`
para o mesmo `(origem, ds)`. **Não é uma invariante exata** — Grupo A/B
usam modelos independentes, não são splits do total, então alguma
divergência é esperada por construção.

Execução de referência (`origem = 2025-12-31`):

| ds | soma equipes | yhat total | diff% |
|---|---|---|---|
| 2026-01-01 | 100,5 | 124,5 | -19,3% |
| 2026-01-02 | 75,3 | 94,8 | -20,5% |
| 2026-01-03 | 33,8 | 46,7 | -27,7% |
| 2026-01-04 | 19,7 | 18,5 | +6,4% |
| 2026-01-05 | 83,5 | 95,5 | -12,6% |
| 2026-01-06 | 89,8 | 102,3 | -12,3% |
| 2026-01-07 | 85,0 | 107,2 | -20,7% |

Divergência de -28% a +6% — dentro do esperado, sem sinal de bug (só
investigar se a soma dobrar ou cair pela metade em algum dia).

## 10. Como rodar

Depende de `ml.fct_previsao_diaria_total` já ter uma linha para a `origem`
corrente (Grupo C lê o `yhat` de lá) — falha alto e explícito se não
houver:

```bash
python notebooks/forecast_incidentes_revisado.py --fonte sql   # 1º: total
python notebooks/forecast_equipe.py --fonte sql                 # 2º: por equipe, mesma origem
```

~5 minutos para as 16 equipes (8 rodam backtest completo de origem móvel +
Prophet; Grupo C é só leitura + split, quase instantâneo).

## 11. Referências

- `notebooks/06_forecast_investigacao_equipe.ipynb` — Fase 0, corte de
  viabilidade (executado, com tabela + gráficos salvos).
- `notebooks/forecast_equipe.py` — Fase 1-2, implementação (Prophet
  individual, fallback semanal, split proporcional, persistência).
- `notebooks/forecast_incidentes_revisado.py` — forecast total, fonte das
  funções reaproveitadas (`Config`, `prever_prophet`, `backtest`,
  `validar_serie`, `metricas_gerais`, `BASELINES`, `calcular_shares`).
- `db/migrations/025_ml_fct_previsao_grupo.sql` — schema.
- `docs/modelo-dimensional.md` (seção "`ml.fct_previsao_grupo` — corte
  A/B/C por equipe") e `docs/dicionario-dados.md` (seção
  "`ml.fct_previsao_grupo`") — entradas equivalentes nos documentos de
  referência do projeto.
