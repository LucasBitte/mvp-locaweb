# PRD — Etapa 5: API FastAPI servindo as 6 telas do mockup

> Status: proposto. Cobre `app/api/` — Painel, Detalhe, KPI, Fatores, Clusters, Alertas
> (`docs/design/aiops_dashboard_redesign.html`). Ver `CLAUDE.md` §4 e §9 para o contexto
> das limitações de escopo referenciadas abaixo.
>
> **⚠️ Atualização (2026-08-21)**: `dw.ref_meta_sla_anual` **já foi criada** — mas com um
> schema diferente do sugerido abaixo (`prioridade_num`/`ano`/`meta_quebras_ano`/`fonte`,
> 2 linhas placeholder). O Dicionário de Dados oficial do desafio define a meta anual como
> uma **tabela de 6 faixas por indicador** (`ola_quebrado`/`volume_tratado`) × prioridade
> (P2/P3), cada faixa com um `pct_atingimento` (150/125/100/75/50/0) — 24 linhas reais, não
> placeholder. Ver `db/migrations/024_dw_ref_meta_sla_anual.sql`,
> `docs/modelo-dimensional.md` e o lookup pronto em `etl/ref_meta_sla.py`
> (`faixa_meta_sla(engine, prioridade_num, indicador, contagem_acumulada)`). **Todo trecho
> abaixo que referencia `meta_quebras_ano`/`is_placeholder_meta`/`fonte='placeholder_mockup'`
> está desatualizado** e precisa ser revisado contra o schema real antes da implementação
> desta etapa — o dado agora é oficial, não placeholder, mas a probabilidade de atingir a
> meta anual continua sendo heurística de projeção (fora de escopo, não implementada).

## 1. Problema

`app/api/` hoje é só o esqueleto (`GET /health`). Os dados reais já existem nos schemas
`dw` (star schema) e `ml` (features + saídas dos 3 modelos de ML — Etapa 4, ✅), mas o
mockup de referência mistura, nas 6 telas, elementos com fonte real no banco com
elementos que **não têm fonte nenhuma** hoje:

- limite mensal de volume por prioridade (tela Detalhe),
- meta anual de OLA (tela KPI — `dw.ref_meta_sla_anual` ainda não existe),
- recorrência de item de configuração com previsão de próxima falha (tela Alertas),
- e o painel "Valores SHAP" do mockup descreve algo que os dados não sustentam (explica
  incidentes de risco individual, não "a previsão do dia seguinte").

Sem decidir explicitamente, endpoint a endpoint, o que é dado real, o que é placeholder
sinalizado e o que fica fora de escopo, a Etapa 6 (frontend) vai implementar o mockup ao
pé da letra e reintroduzir os dois mal-entendidos já sinalizados no `CLAUDE.md`: tratar a
proporção histórica do forecast por prioridade/categoria como um modelo por corte, e
apresentar a meta de OLA como se fosse dado real.

## 2. Objetivo

Servir, via endpoints REST **somente leitura**, os dados reais de `dw.*` e `ml.fct_*`
necessários para renderizar fielmente as 6 telas do mockup — um endpoint por tela —
sinalizando de forma explícita e testável, na própria resposta (nunca só na UI):

- todo valor derivado de **proporção histórica** (forecast por prioridade/categoria),
- todo valor que depende da meta de OLA **placeholder** (`dw.ref_meta_sla_anual`),
- e reinterpretando o painel de SHAP para o que os dados de fato explicam (risco de
  incidentes individuais, não o forecast de volume do dia seguinte).

## 3. Não-objetivos

- Autenticação/autorização da API.
- Qualquer método de escrita (`POST`/`PUT`/`DELETE`) — a API é somente leitura nesta etapa.
- Paginação ou histórico de execuções passadas de forecast (só a `data_execucao` mais recente de cada tabela `ml.fct_*`).
- Alerta de recorrência por item de configuração (tela Alertas) — não existe modelo de recorrência por CI em nenhum dos 3 modelos de ML; fica fora de escopo até existir uma fonte real.
- Servir dados brutos de `public.incidentes` ou `staging.incidentes_silver` via API.
- Cache ou otimização de performance além do necessário para o volume atual (~41 mil linhas em `dw.fct_incidentes`).
- Construção do frontend (Etapa 6) — este PRD cobre só a API.
- Corrigir os valores de SLA do mockup (P2=4h/P3=12h): a API usa os valores reais de `dw.dim_prioridade.threshold_sla_horas` (P2=8h/P3=24h); a divergência com o mockup é intencional e deve ser tratada na Etapa 6.

## 4. Endpoints e critérios de aceite

Convenção: todas as respostas incluem `data_execucao`/`modelo_versao` (ou equivalente)
das tabelas `ml.fct_*` de origem, e todo endpoint filtra sempre pela execução mais
recente de cada tabela (essas tabelas são append-only entre execuções do pipeline).

### 4.1 `GET /api/painel`

Query params: `prioridade` (opcional; default `todas`), `dias` (default `30`, janela do
histórico exibido no gráfico).

Fontes: `ml.ml_forecast_dataset` (histórico diário pré-agregado), `ml.fct_previsao_diaria_total`
(quando `prioridade=todas`) ou `ml.fct_previsao_prioridade` (quando filtrado por
prioridade — proporção histórica).

```json
{
  "previsao_d1": {"valor": 72, "data": "2026-08-22", "modelo_versao": "prophet_v1"},
  "previsao_d7_media": {"valor": 68, "variacao_pct_vs_media_historica": 12.4},
  "risco_ola": {"nivel": "medio", "pct_violacao_media_movel": 14.2, "janela_dias": 14},
  "serie": [
    {"data": "2026-07-23", "tipo": "historico", "valor": 55},
    {"data": "2026-08-22", "tipo": "previsao", "horizonte": "D+1", "valor": 72}
  ],
  "metodologia": null
}
```

Quando `prioridade != todas`, `previsao_d1`/`previsao_d7_media`/cada ponto `tipo=previsao`
da `serie` ganham `"metodologia": "proporcao_historica"` e `"share_historico"` (dado que
`fct_previsao_prioridade` é split proporcional, não um modelo por corte).

**Critérios de aceite:**
1. `previsao_d1.valor` é igual ao `yhat` (arredondado) da linha de maior `data_execucao` em `ml.fct_previsao_diaria_total` com `horizonte='D+1'`, quando `prioridade=todas`.
2. `serie` contém exatamente `dias` pontos com `tipo=historico` e 7 pontos com `tipo=previsao` (`horizonte` de `D+1` a `D+7`).
3. `risco_ola.nivel` ∈ {`baixo`, `medio`, `alto`}, calculado por faixas fixas documentadas no código sobre a média móvel de `pct_violacao_sla` de `ml.ml_forecast_dataset` — nunca hardcoded como texto solto.
4. Quando `prioridade != todas`, todo item de previsão retornado tem `metodologia="proporcao_historica"` e `share_historico` não-nulo — nunca omitido.

### 4.2 `GET /api/detalhe`

Query params: `horizonte` (default `D+1`).

Fontes: `ml.fct_previsao_prioridade`, `dw.dim_prioridade` (thresholds reais), `dw.ref_meta_sla_anual`
(placeholder), `ml.fct_previsao_categoria` (top categorias).

```json
{
  "prioridades": [
    {
      "prioridade_num": 2,
      "bucket_prioridade": "P2 - Alta",
      "previsto": 18,
      "threshold_sla_horas": 8,
      "metodologia": "proporcao_historica",
      "share_historico": 0.31,
      "pct_limite_mensal": null,
      "is_placeholder_limite": true
    }
  ],
  "top_categorias": [
    {"categoria": "Infraestrutura", "yhat_categoria": 24.3, "share_historico": 0.28, "metodologia": "proporcao_historica"}
  ]
}
```

**Critérios de aceite:**
1. `prioridades` reflete exatamente as prioridades presentes em `ml.fct_previsao_prioridade` para o `horizonte` pedido — nunca uma lista fixa hardcoded no código.
2. `threshold_sla_horas` vem de `dw.dim_prioridade.threshold_sla_horas` (P2=8h/P3=24h reais, não os valores do mockup).
3. `pct_limite_mensal=null` e `is_placeholder_limite=true` enquanto `dw.ref_meta_sla_anual.fonte='placeholder_mockup'` — teste de contrato garante que `is_placeholder_limite` nunca é omitido.
4. `top_categorias` tem no máximo 5 itens, ordenados por `yhat_categoria` desc, cada um com `metodologia="proporcao_historica"` e `share_historico` presentes.

### 4.3 `GET /api/kpi`

Query params: `ano` (default: ano corrente).

Fontes: `dw.ref_meta_sla_anual` (nova tabela, placeholder), `dw.fct_incidentes`
(`kpi_status_int=1` para contagem de quebras reais).

```json
{
  "ano": 2026,
  "dias_decorridos": 9,
  "dias_restantes": 22,
  "ola_quebrados_total": 8,
  "prioridades": [
    {
      "prioridade_num": 2,
      "bucket_prioridade": "P2 - Alta",
      "meta_quebras_ano": 31,
      "is_placeholder_meta": true,
      "quebras_mes_atual": 8,
      "pct_quebras_vs_meta_mes": 72.0,
      "volume_tratado_mes": 120,
      "pct_volume_vs_media": 55.0,
      "status": "atencao",
      "probabilidade_atingir_meta_pct": 61.0,
      "metodologia_probabilidade": "projecao_linear"
    }
  ]
}
```

`probabilidade_atingir_meta_pct` = projeção linear determinística:
`(quebras_ate_agora / dias_decorridos) * dias_totais_do_ano`, comparada a `meta_quebras_ano`.
Sem modelo estatístico novo nesta etapa.

**Critérios de aceite:**
1. Toda prioridade no array traz `is_placeholder_meta=true` — nunca omitido — enquanto `dw.ref_meta_sla_anual` não tiver uma linha com `fonte != 'placeholder_mockup'`.
2. `quebras_mes_atual` bate exatamente com `COUNT(*)` de `dw.fct_incidentes` filtrado por `kpi_status_int=1`, prioridade e mês/ano corrente (validado por query manual de conferência nos testes).
3. `probabilidade_atingir_meta_pct` segue a fórmula de projeção linear documentada acima; `metodologia_probabilidade="projecao_linear"` está sempre presente no payload.
4. `status` ∈ {`no_prazo`, `atencao`, `critico`} derivado de thresholds fixos documentados no código (ex.: quebras projetadas > meta → `critico`; > 70% da meta → `atencao`; caso contrário → `no_prazo`) — nunca calculado no frontend.

### 4.4 `GET /api/fatores`

Fontes: `ml.fct_importancia_conceito` (primária, com fallback para
`ml.fct_importancia_feature`), `ml.fct_shap_incidente` (join `dw.fct_incidentes`),
`dw.fct_incidentes` agregado (join `dim_produto_categoria` + `dim_tempo`).

> Atualizado após a migration `023_ml_fct_importancia_conceito.sql` (PR #17, já aplicada):
> o mockup mostra importância por **conceito de negócio** ("Dia da semana", "Categoria",
> "Prioridade do chamado"), não por coluna crua ("hora_sin", "vol_hora_grupo"). A tabela
> `ml.fct_importancia_conceito` é a leitura executiva certa pra este painel;
> `ml.fct_importancia_feature` vira fallback técnico só para quando o SHAP não rodou
> (execução por gain do XGBoost, que não calcula agrupamento por conceito e deixa
> `fct_importancia_conceito` vazia).

```json
{
  "importancia_conceitos": [{"conceito": "Prioridade do chamado", "n_colunas": 3, "importance_pct": 30.76, "rank": 1}],
  "granularidade": "conceito",
  "shap_top_risco": [
    {"incident_id": "INC8263208", "feature": "prioridade_num", "shap_value": 1.8, "direcao": "aumenta_risco", "rank_abs": 1, "score_calibrado": 0.87}
  ],
  "heatmap_categoria_dia": [
    {"categoria": "Infraestrutura", "dia_semana_num": 1, "nome_dia": "Segunda", "volume_medio": 34}
  ]
}
```

`granularidade` é sempre `"conceito"` quando `ml.fct_importancia_conceito` tem linhas
para a `data_execucao` mais recente do XGBoost; cai para `"coluna"` (lendo
`ml.fct_importancia_feature`, item nesse caso com `feature` no lugar de `conceito`) só
quando a tabela de conceito estiver vazia pra aquela execução — nunca escondido do
payload.

O painel de SHAP é reinterpretado (decisão registrada neste PRD): explica os incidentes
de **maior risco de SLA atual** (`ml.fct_shap_incidente`, top 30 por execução), não "o
impacto na previsão do dia seguinte" como o texto do mockup sugere. Nenhum campo ou label
do payload deve mencionar "previsão"/"amanhã" nesse bloco.

**Critérios de aceite:**
1. `importancia_conceitos` ordenado por `rank` asc; reflete a `data_execucao` mais recente de `ml.fct_importancia_conceito` quando essa tabela tiver linhas pra execução — nesse caso `granularidade="conceito"`.
2. Quando `ml.fct_importancia_conceito` estiver vazia pra execução mais recente (fallback de gain do XGBoost), o endpoint usa `ml.fct_importancia_feature` e `granularidade="coluna"` — o campo `granularidade` nunca é omitido em nenhum dos dois casos.
3. `shap_top_risco` contém exatamente os incidentes presentes na execução mais recente de `ml.fct_shap_incidente` (até 30, conforme `TOP_N_SHAP`) — nenhum campo do payload usa os termos "previsão" ou "amanhã".
4. `heatmap_categoria_dia` cobre todas as combinações categoria × `dia_semana_num` de `dw.fct_incidentes` com volume > 0 — nenhuma célula com volume real ausente.

### 4.5 `GET /api/clusters`

Fontes: `ml.fct_perfil_cluster` join `ml.dim_cluster` (execução mais recente).

```json
{
  "clusters": [
    {
      "cluster_id": "A", "nome_perfil": "Críticos prolongados",
      "descricao_curta": "Alta duração · P2 dominante · Alto risco OLA",
      "tags": ["Infra", "Rede", "P2", "Seg-Ter"], "cor_hex": "#ef4444",
      "n_incidentes": 3840, "pct_volume": 15.2,
      "duracao_media_horas": 5.2, "taxa_resolucao_pct": 94.0, "taxa_sla_violado_pct": 38.0
    }
  ],
  "modelo_versao": "kmeans_v1",
  "data_execucao": "2026-08-15T10:00:00Z"
}
```

**Critérios de aceite:**
1. Retorna exatamente os `cluster_id` presentes em `ml.dim_cluster` (A–D), cada um casado 1:1 com sua linha mais recente em `ml.fct_perfil_cluster` por `data_execucao`.
2. Soma de `pct_volume` de todos os clusters retornados está entre 99% e 101% (tolerância de arredondamento).
3. `tags` é sempre uma lista (split de `ml.dim_cluster.tags`, CSV) — nunca a string bruta com vírgulas.

### 4.6 `GET /api/alertas`

Fontes: `ml.fct_previsao_diaria_total` + `ml.fct_previsao_categoria` (D+1 vs média
histórica), `ml.fct_perfil_cluster`/`ml.fct_risco_incidente` (risco por categoria/cluster).
Recomendações geradas por regras de negócio no backend, referenciando os mesmos dados de
alertas — não vêm de nenhuma tabela nova.

```json
{
  "alertas": [
    {
      "tipo": "critico", "titulo": "Alerta crítico — Amanhã",
      "mensagem": "Volume previsto 25% acima da média histórica...",
      "gerado_em": "2026-08-21T20:00:00Z"
    }
  ],
  "recomendacoes": [
    {"ordem": 1, "texto": "Reforçar equipa de Infraestrutura na manhã de segunda-feira (08h-12h)...",
     "prioridade": "alta", "regra_origem": "concentracao_risco_categoria_top1"}
  ]
}
```

**Critérios de aceite:**
1. `alertas` nunca inclui um alerta do tipo "recorrência de item de configuração" (explicitamente fora de escopo — não-objetivo §3).
2. Cada alerta em `alertas` tem `tipo` determinado por uma regra fixa e documentada no código (ex.: `critico` se `variacao_pct_vs_media_historica` do D+1 > 20%; `info` se D+7 cai em fim de semana com `pct_violacao_sla` histórico de fins de semana = 0) — nunca uma regra ad-hoc não documentada.
3. Cada item de `recomendacoes` tem `regra_origem` referenciando qual regra de negócio (documentada no código/PRD) gerou o texto — nenhuma recomendação sem rastreabilidade à regra que a gerou.
4. `recomendacoes` é gerado inteiramente a partir dos dados já expostos por `/api/alertas`, `/api/detalhe` e `/api/clusters` (sem tabela nova) — nenhuma dependência de dado fora do escopo desta etapa.

## 5. Dependências

- Nova migration `db/migrations/024_dw_ref_meta_sla_anual.sql`: cria `dw.ref_meta_sla_anual`
  (colunas sugeridas: `prioridade_num`, `ano`, `meta_quebras_ano`, `fonte` [ex.:
  `'placeholder_mockup'`], `criado_em`), populada com os números do mockup como
  placeholder explícito — nunca com `fonte` indicando dado real até existir uma fonte
  contratual. (Numerada `024`, não `023` — esse número já foi usado por
  `023_ml_fct_importancia_conceito.sql`, PR #17, mesclado depois deste PRD.)
- As 3 saídas de modelo (`ml.fct_previsao_*`, `ml.fct_perfil_cluster`,
  `ml.fct_importancia_feature`/`fct_importancia_conceito`/`fct_risco_incidente`/
  `fct_shap_incidente`) precisam já estar populadas — dependência da Etapa 4 (✅, mas
  exige rodar os notebooks/scripts ao menos uma vez antes de testar a API contra dados
  reais). `ml.fct_importancia_conceito` já existe e já foi populada (migration 023, PR
  #17) — nenhuma migration nova necessária pra essa tabela.
- `etl/db.py` (`get_engine()`) como única via de conexão — nenhum endpoint deve abrir
  conexão própria.
- Roteamento em `app/api/routers/` (um módulo por tela, registrado em `app/api/main.py`).

## 6. Riscos

- **Placeholder confundido com dado real**: se `is_placeholder_meta`/`is_placeholder_limite`
  for omitido em qualquer resposta, a Etapa 6 pode renderizar a meta de OLA como número
  real — mitigar com teste de contrato de schema que falha se o campo estiver ausente.
- **Append-only mal filtrado**: `ml.fct_previsao_diaria_total`/`_prioridade`/`_categoria`
  acumulam uma linha por execução (`origem`); uma query sem filtrar a `data_execucao`
  mais recente mistura previsões antigas com novas.
- **Proporção histórica mal interpretada na Etapa 6**: mesmo com `metodologia`/
  `share_historico` na resposta, o frontend pode ignorar o campo e renderizar como se
  fosse forecast por corte — é exatamente o mal-entendido que o `CLAUDE.md` já sinaliza;
  mitigar deixando o campo em todo item, não só como metadado global.
- **Reinterpretação do painel SHAP diverge do mockup validado**: o texto "impacto na
  previsão do dia seguinte" do mockup original não corresponde ao dado real; há risco de
  divergência de expectativa com quem validou o mockup — vale alinhar antes da Etapa 6.
- **Probabilidade por projeção linear é estatisticamente simplista**: comunica uma
  precisão que o método não tem; mitigar deixando `metodologia_probabilidade` sempre
  visível no payload, não só na UI.
- **Performance de agregação em `dw.fct_incidentes`**: heatmap e alguns cálculos de KPI
  agregam ~41 mil linhas por request sem cache — aceitável no volume atual, mas sem
  otimização prevista nesta etapa (não-objetivo §3).
- **Fallback de granularidade em `/api/fatores`**: quando `ml.fct_importancia_conceito`
  está vazia (execução do XGBoost sem SHAP, só gain), o endpoint muda de conceito de
  negócio pra coluna crua — se o frontend (Etapa 6) ignorar o campo `granularidade`, a
  tela pode mostrar rótulos técnicos (`hora_sin`, `vol_hora_grupo`) em vez dos conceitos
  do mockup sem nenhum aviso.
