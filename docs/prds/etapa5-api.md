# PRD — Etapa 5: API FastAPI servindo as 6 telas do dashboard

> Status: proposto (contrato de dados — sem código). Cobre `app/api/` — Painel, Detalhe
> (rótulo "Operação"), KPI (rótulo "OLA & Metas"), Fatores, Clusters, Alertas. Nomes
> canônicos e mapeamento tela↔fonte: `PLAN.md` §4. Ver `CLAUDE.md` §4 e §9 para o contexto
> geral do pipeline.
>
> **Revisão 2026-08-22 — fecha as lacunas do `PLAN.md` Fases 6-9/11 nos contratos abaixo.**
> Este PRD havia sido escrito antes das Fases 1-5/10/12/13 do `PLAN.md` rodarem; boa parte
> do texto original ficou desatualizado (a meta de OLA era tratada como placeholder de 2
> linhas, os thresholds de SLA eram os do mockup, e pressão por equipe/split por
> produto/recorrência não existiam como tabela). Esta revisão substitui todo o conteúdo
> desatualizado pelo estado real do banco `fiap` hoje. Resumo do que mudou:
> - `dw.ref_meta_sla_anual` **é dado real** (24 linhas, migration `024`, faixas por
>   prioridade×indicador — não mais placeholder de 2 linhas); §4.3 reescrita por inteiro.
> - `dw.dim_prioridade.threshold_sla_horas` **já está corrigido** para os valores oficiais
>   (P1=4h/P2=4h/P3=12h/P4=24h/P5=96h, 2026-08-21) — não é mais uma divergência intencional
>   frente ao mockup; §3 e §4.2 atualizadas.
> - Pressão operacional por equipe (`ml.fct_pressao_equipe`, migration `026`) passa a fazer
>   parte do contrato de `/api/painel` (§4.1) — não existia quando este PRD foi escrito.
> - Split por produto (`ml.fct_previsao_produto`, migration `027`) vira uma granularidade
>   opcional de `/api/detalhe` (§4.2), ao lado de categoria.
> - Recorrência por produto/categoria (`dw.fct_recorrencia_operacional`, migration `028`)
>   entra em `/api/detalhe` (§4.2) e alimenta um novo tipo de alerta em `/api/alertas`
>   (§4.6) — **não** é a recorrência por item de configuração (CI), que continua fora de
>   escopo (§3, inalterado).
> - `/api/fatores` (§4.4) e `/api/clusters` (§4.5) não tinham lacuna material — mantidos,
>   com pequenos ajustes de referência cruzada.

## 1. Problema

`app/api/` hoje é só o esqueleto (`GET /health`). Os dados reais já existem nos schemas
`dw` (star schema) e `ml` (features + saídas dos 4 modelos de ML — Etapa 4, ✅, incluindo
os fechamentos de lacuna do `PLAN.md`), mas nem todo elemento que o dashboard React já
renderiza (`app/web/src/data/dashboardData.ts`, dado estático, Fase 15) tem hoje uma fonte
real por trás:

- **tem fonte real hoje** (não tinha quando este PRD foi escrito pela 1ª vez): meta anual
  de OLA (`dw.ref_meta_sla_anual`), pressão por equipe (`ml.fct_pressao_equipe`), split de
  forecast por produto (`ml.fct_previsao_produto`), recorrência por produto/categoria
  (`dw.fct_recorrencia_operacional`);
- **ainda sem fonte** (fora de escopo desta etapa, §3): limite mensal de volume por
  prioridade, recorrência por item de configuração (CI) com previsão de próxima falha.

Sem decidir explicitamente, endpoint a endpoint, o que é dado real, o que ainda é lacuna
sinalizada e o que fica fora de escopo, a implementação da Etapa 5 corre o risco de repetir
dois mal-entendidos já sinalizados no `CLAUDE.md`/`PLAN.md`: tratar a proporção histórica
do forecast por prioridade/categoria/produto como um modelo por corte, e apresentar
`ml.fct_shap_incidente` como explicação do forecast de amanhã em vez de risco individual.

## 2. Objetivo

Servir, via endpoints REST **somente leitura**, os dados reais de `dw.*` e `ml.fct_*`
necessários para as 6 telas do dashboard React já implementado (`app/web/src/components/
screens/`) — um endpoint por tela — sinalizando de forma explícita e testável, na própria
resposta (nunca só na UI):

- todo valor derivado de **proporção histórica** (forecast por prioridade/categoria/produto);
- todo valor ainda sem fonte real, com `null` + flag explícita (nunca omitido em silêncio);
- a leitura correta do painel de SHAP (risco de incidentes individuais, não forecast de
  volume do dia seguinte — regra semântica permanente, `PLAN.md` Fase 9).

## 3. Não-objetivos

- Autenticação/autorização da API.
- Qualquer método de escrita (`POST`/`PUT`/`DELETE`) — a API é somente leitura nesta etapa.
- Paginação ou histórico de execuções passadas de forecast (só a `data_execucao` mais
  recente de cada tabela `ml.fct_*`/`dw.fct_recorrencia_operacional`).
- **Recorrência por item de configuração (CI)** com previsão de próxima falha (tela
  Alertas) — não existe modelo de recorrência por CI em nenhum dos 4 modelos de ML nem em
  `dw.fct_recorrencia_operacional` (que é por produto/categoria, não por CI); fica fora de
  escopo até existir uma fonte real. **Diferente da recorrência por produto/categoria**, que
  já tem fonte real (`dw.fct_recorrencia_operacional`, migration `028`) e está em escopo
  (§4.2, §4.6).
- Limite mensal de volume por prioridade (tela Detalhe) — nenhuma tabela expõe esse dado
  hoje; continua fora de escopo, sinalizado como `null` no payload (§4.2).
- Servir dados brutos de `public.incidentes` ou `staging.incidentes_silver` via API.
- Cache ou otimização de performance além do necessário para o volume atual (~41 mil linhas
  em `dw.fct_incidentes`).
- Construção do frontend (Etapa 6) — este PRD cobre só a API; o React (Fase 15) já existe
  com dado estático e troca só a fonte (`fetch` no lugar das funções `computeXxx()` de
  `dashboardData.ts`) quando a API existir.
- ~~Corrigir os valores de SLA do mockup~~ — **obsoleto**: `dw.dim_prioridade.
  threshold_sla_horas` já foi corrigido para os valores oficiais (P1=4h/P2=4h/P3=12h/
  P4=24h/P5=96h, 2026-08-21); não há mais divergência a tratar na Etapa 6, a API expõe o
  valor real da coluna diretamente.

## 4. Endpoints e critérios de aceite

Convenção: todas as respostas incluem `data_execucao`/`modelo_versao` (ou equivalente) das
tabelas `ml.fct_*`/`dw.fct_recorrencia_operacional` de origem, e todo endpoint filtra
sempre pela execução mais recente de cada tabela (essas tabelas são append-only ou
recarregadas por completo entre execuções do pipeline — nunca misturar execuções).

### 4.1 `GET /api/painel`

Query params: `prioridade` (opcional; default `todas` — nunca `P2_P3` por padrão aqui,
o recorte P2/P3 é da tela Detalhe/Alertas, `PLAN.md` Fase 2), `dias` (default `30`, janela
do histórico exibido no gráfico).

Fontes: `ml.ml_forecast_dataset` (histórico diário pré-agregado), `ml.fct_previsao_diaria_total`
(quando `prioridade=todas`) ou `ml.fct_previsao_prioridade` (quando filtrado por
prioridade — proporção histórica), `ml.fct_pressao_equipe` (pressão por equipe, `PLAN.md`
Fase 3 — **novo neste PRD**, não existia na versão original).

```json
{
  "previsao_d1": {"valor": 125, "data": "2026-01-01", "modelo_versao": "prophet_v1"},
  "previsao_d7_media": {"valor": 118, "variacao_pct_vs_media_historica": 9.7},
  "risco_ola": {"nivel": "medio", "pct_violacao_media_movel": 14.2, "janela_dias": 14},
  "serie": [
    {"data": "2025-12-02", "tipo": "historico", "valor": 113},
    {"data": "2026-01-01", "tipo": "previsao", "horizonte": "D+1", "valor": 125}
  ],
  "pressao_equipes": [
    {
      "dim_grupo_sk": "...", "grupo_designado": "Team02",
      "yhat_previsto": 41.2, "media_historica_diaria": 31.8,
      "pressao_relativa_pct": 29.4, "nivel_pressao": "atencao",
      "metodo_origem": "prophet_individual"
    }
  ],
  "metodologia": null
}
```

Quando `prioridade != todas`, `previsao_d1`/`previsao_d7_media`/cada ponto `tipo=previsao`
da `serie` ganham `"metodologia": "proporcao_historica"` e `"share_historico"` (dado que
`ml.fct_previsao_prioridade` é split proporcional, não um modelo por corte).

`pressao_equipes` é sempre relativa a D+1 (`h=1`), ordenada por `pressao_relativa_pct` desc,
lida diretamente de `ml.fct_pressao_equipe` — a API **nunca recalcula** a fórmula
(`(yhat_previsto - media_historica_diaria) / media_historica_diaria * 100`), só lê o valor
já persistido pelo `notebooks/pressao_equipe.py`. `nivel_pressao` vem da mesma coluna
(`normal`/`atencao`/`critico`, limiares fixos `<=10%`/`10-30%`/`>30%` documentados no
notebook, não recalculados na API).

**Critérios de aceite:**
1. `previsao_d1.valor` é igual ao `yhat` (arredondado) da linha de maior `data_execucao` em
   `ml.fct_previsao_diaria_total` com `horizonte='D+1'`, quando `prioridade=todas`.
2. `serie` contém exatamente `dias` pontos com `tipo=historico` e 7 pontos com
   `tipo=previsao` (`horizonte` de `D+1` a `D+7`).
3. `risco_ola.nivel` ∈ {`baixo`, `medio`, `alto`}, calculado por faixas fixas documentadas
   no código sobre a média móvel de `pct_violacao_sla` de `ml.ml_forecast_dataset` — nunca
   hardcoded como texto solto.
4. Quando `prioridade != todas`, todo item de previsão retornado tem
   `metodologia="proporcao_historica"` e `share_historico` não-nulo — nunca omitido.
5. `pressao_equipes` retorna exatamente as 16 equipes de `dw.dim_grupo` para `h=1` da
   execução mais recente de `ml.fct_pressao_equipe`, ordenadas por `pressao_relativa_pct`
   desc — nenhuma equipe omitida, nenhum recálculo da fórmula na camada de API.

### 4.2 `GET /api/detalhe`

Query params: `horizonte` (default `D+1`), `agrupamento` (`categoria` default | `produto` —
**novo neste PRD**, `PLAN.md` Fase 4).

Fontes: `ml.fct_previsao_prioridade`, `dw.dim_prioridade` (thresholds reais, já corrigidos),
`ml.fct_previsao_categoria` **ou** `ml.fct_previsao_produto` (conforme `agrupamento`),
`dw.fct_recorrencia_operacional` (recorrência — **novo neste PRD**, `PLAN.md` Fase 5).

```json
{
  "prioridades": [
    {
      "prioridade_num": 2,
      "bucket_prioridade": "P2 - Alta",
      "previsto": 18,
      "threshold_sla_horas": 4,
      "metodologia": "proporcao_historica",
      "share_historico": 0.31,
      "pct_limite_mensal": null,
      "is_placeholder_limite": true
    }
  ],
  "agrupamento": "categoria",
  "top_entidades": [
    {"nome": "cat94", "yhat": 21.4, "share_historico": 0.214, "metodologia": "proporcao_historica"}
  ],
  "recorrencia": {
    "granularidade": "categoria",
    "janela_referencia": "2025-12-31",
    "entidades": [
      {
        "entidade": "cat94", "volume_atual": 34, "volume_baseline": 6,
        "delta_pct": 466.7, "cobertura_dias_atual_pct": 50.0,
        "status_recorrencia": "recorrente_crescente"
      }
    ]
  }
}
```

`threshold_sla_horas` vem sempre de `dw.dim_prioridade.threshold_sla_horas` — valores reais
já corrigidos (P1=4h/P2=4h/P3=12h/P4=24h/P5=96h), nunca um valor hardcoded na API ou no
frontend.

`pct_limite_mensal`/`is_placeholder_limite` continuam como antes: **nenhuma tabela expõe
limite mensal de volume por prioridade hoje** (§3, inalterado) — `pct_limite_mensal` fica
sempre `null` e `is_placeholder_limite` sempre `true`; teste de contrato garante que o
segundo campo nunca é omitido (para o frontend nunca tratar `null` como "sem limite" por
omissão).

`top_entidades` reaproveita o mesmo formato para `categoria` (`ml.fct_previsao_categoria`)
e `produto` (`ml.fct_previsao_produto`) — o campo `agrupamento` do payload indica qual das
duas tabelas foi lida; o nome do campo por linha é sempre `nome`/`yhat` (não
`categoria`/`yhat_categoria` nem `produto`/`yhat_produto`), para o frontend não precisar de
lógica condicional por granularidade.

`recorrencia.entidades` filtra `dw.fct_recorrencia_operacional` pela `granularidade`
correspondente ao `agrupamento` pedido (`categoria`→`categoria`, `produto`→`produto`) e pelo
`status_recorrencia` ∈ {`recorrente_crescente`, `recorrente_estavel`} — enum real confirmado
em produção (`docs/dicionario-dados.md`): `recorrente_estavel` / `recorrente_crescente` /
`recorrente_em_queda` / `pico_pontual` / `novo_padrao` / `volume_insuficiente` /
`sem_padrao_claro`. **Não existe o valor `"recorrente"` sozinho** (uma versão anterior
deste PRD citava esse valor por engano — corrigido nesta revisão). Só os dois status acima
entram no bloco de detalhe (`recorrente_em_queda`/`pico_pontual`/`novo_padrao` não são o
padrão "recorrente e ativo" que esta tela quer destacar); ordenado por `delta_pct` desc,
limitado a um top 10.

**Critérios de aceite:**
1. `prioridades` reflete exatamente as prioridades presentes em `ml.fct_previsao_prioridade`
   para o `horizonte` pedido — nunca uma lista fixa hardcoded no código.
2. `threshold_sla_horas` bate exatamente com `dw.dim_prioridade.threshold_sla_horas` (não um
   valor hardcoded na API).
3. `pct_limite_mensal=null` e `is_placeholder_limite=true` sempre — teste de contrato
   garante que `is_placeholder_limite` nunca é omitido.
4. `top_entidades` tem no máximo 5 itens, ordenados por `yhat` desc, cada um com
   `metodologia="proporcao_historica"` e `share_historico` presentes; a tabela lida
   (`ml.fct_previsao_categoria` vs. `ml.fct_previsao_produto`) corresponde exatamente ao
   `agrupamento` pedido.
5. `recorrencia.entidades` nunca inclui uma linha com `status_recorrencia="volume_insuficiente"`
   nem `"estavel"`; `granularidade` do bloco de recorrência sempre bate com `agrupamento`.

### 4.3 `GET /api/kpi`

> **Reescrita integral (revisão 2026-08-22)** — o texto original assumia
> `dw.ref_meta_sla_anual` como 2 linhas placeholder (`meta_quebras_ano`/`is_placeholder_meta`).
> A tabela real (migration `024`) é uma tabela de **faixas**: 1 linha por
> (`prioridade_num` ∈ {2,3}, `indicador` ∈ {`ola_quebrado`,`volume_tratado`}, `faixa`), 6
> faixas por combinação, cada uma com `pct_atingimento` (150/125/100/75/50/0) — 24 linhas
> reais. Lookup pronto: `etl/ref_meta_sla.py::faixa_meta_sla(engine, prioridade_num,
> indicador, contagem_acumulada) -> dict`. **Só existem faixas para P2/P3** — não fabricar
> linhas de P1/P4 nesta tela (o dashboard React atual, `computeBandasMeta()` em
> `dashboardData.ts`, mostra P1/P2/P3/P4 com faixas inventadas para P1/P4; isso é uma
> divergência a corrigir na Etapa 5/6, não repetir no contrato real).

Query params: `ano` (default: ano da âncora temporal do pipeline — `MAX(aberto_at)` em
`dw.fct_incidentes`, 2025 no banco atual, **não** o ano-calendário real; ver `PLAN.md`
Fase 1 sobre a âncora. Quando `ano` = âncora, `dias_decorridos` é o dia-do-ano da âncora;
para qualquer outro `ano`, o endpoint trata como ano-calendário já encerrado por completo
— não há noção de "hoje" fora da âncora do pipeline).

Fontes: `dw.ref_meta_sla_anual` (dado real, migration `024`) + `etl/ref_meta_sla.py::faixa_meta_sla()`,
`dw.fct_incidentes` (`kpi_status_int=1` para contagem acumulada de `ola_quebrado`; contagem
de linhas do ano para `volume_tratado`).

```json
{
  "ano": 2026,
  "dias_decorridos": 234,
  "dias_restantes": 131,
  "indicadores": [
    {
      "prioridade_num": 2,
      "bucket_prioridade": "P2 - Alta",
      "indicador": "ola_quebrado",
      "contagem_acumulada_ano": 26,
      "faixa": {"faixa_min": null, "faixa_max": 30, "pct_atingimento": 150, "ordem_faixa": 1},
      "status": "dentro_da_meta",
      "probabilidade_atingir_meta_pct": 61.0,
      "metodologia_probabilidade": "projecao_linear"
    }
  ]
}
```

`indicadores` sempre tem **4 linhas** (2 prioridades × 2 indicadores) — nunca P1/P4, nunca
um 3º indicador. `faixa` vem inteiramente de `faixa_meta_sla()` — a API não reimplementa a
lógica de faixa, só chama a função existente.

`status` é derivado só do `pct_atingimento` da faixa **observada** (dado real, sem
projeção): `pct_atingimento >= 100` → `dentro_da_meta`; `50 <= pct_atingimento < 100` →
`atencao`; `pct_atingimento < 50` → `critico`. Thresholds fixos documentados no código, não
recalculados no frontend.

`probabilidade_atingir_meta_pct` = projeção linear determinística já decidida em `PLAN.md`
Fase 8: `(contagem_acumulada_ano / dias_decorridos) * dias_totais_do_ano`, projetado até o
fim do ano e comparado contra **a meta de referência da faixa `pct_atingimento=100`**
(`faixa_max` da linha com `ordem_faixa` correspondente a 100%, ex.: P2/`ola_quebrado` → 39).
`metodologia_probabilidade="projecao_linear"` sempre presente. **Nunca usar Poisson ou
outro modelo estatístico** — decisão já tomada, não em aberto.

> ⚠️ **Decisão a confirmar antes da implementação**: usar o `faixa_max` da faixa
> `pct_atingimento=100` como "a meta" para a fórmula de projeção acima é a leitura mais
> direta do schema real, mas não está explicitamente escrita em nenhum documento anterior
> (o `PLAN.md` Fase 8 define a fórmula, não qual número é "a meta" no schema de faixas).
> Confirmar com checkpoint humano antes de fixar isso em código — não é um "achismo de UI"
> qualquer, é a base do KPI mais visível do dashboard.

`status` **nunca** é derivado de `probabilidade_atingir_meta_pct` — a separação entre
observado (real) e projeção (heurística) é uma decisão já tomada (`PLAN.md` Fase 8,
"Correção conceitual importante") e não pode ser reintroduzida silenciosamente.

**Critérios de aceite:**
1. `indicadores` tem exatamente 4 linhas (P2/P3 × `ola_quebrado`/`volume_tratado`) — nunca
   P1/P4, nunca uma linha fabricada sem faixa correspondente em `dw.ref_meta_sla_anual`.
2. `contagem_acumulada_ano` bate exatamente com a contagem real em `dw.fct_incidentes`
   filtrada por prioridade + indicador + `ano` do payload (validado por query manual de
   conferência nos testes).
3. `faixa` é sempre o retorno direto de `faixa_meta_sla()` — nenhuma lógica de faixa
   duplicada na camada HTTP.
4. `probabilidade_atingir_meta_pct` segue a fórmula de projeção linear documentada acima;
   `metodologia_probabilidade="projecao_linear"` está sempre presente no payload.
5. `status` é derivado só do `pct_atingimento` observado (nunca da projeção) — thresholds
   fixos documentados no código, nunca calculado no frontend.
6. Nenhuma métrica de avaliação de modelo (ROC-AUC, PR-AUC, Brier, silhouette etc.) aparece
   neste endpoint — KPI é sempre sobre metas/faixas oficiais, nunca performance de modelo
   (`PLAN.md`, Anexo A, "Correção conceitual importante").

### 4.4 `GET /api/fatores`

Fontes: `ml.fct_importancia_conceito` (primária, com fallback para
`ml.fct_importancia_feature`), `ml.fct_shap_incidente` (join `dw.fct_incidentes`),
`dw.fct_incidentes` agregado (join `dim_produto_categoria` + `dim_tempo`).

> A tabela `ml.fct_importancia_conceito` é a leitura executiva certa para este painel
> (conceitos de negócio — "Prioridade do chamado", "Carga operacional do time" etc., não
> colunas cruas); `ml.fct_importancia_feature` é fallback técnico só para quando o SHAP não
> rodou naquela execução.

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

`granularidade` é sempre `"conceito"` quando `ml.fct_importancia_conceito` tem linhas para
a `data_execucao` mais recente do XGBoost; cai para `"coluna"` (lendo
`ml.fct_importancia_feature`, item nesse caso com `feature` no lugar de `conceito`) só
quando a tabela de conceito estiver vazia para aquela execução — nunca escondido do
payload.

O painel de SHAP explica os incidentes de **maior risco de SLA atual**
(`ml.fct_shap_incidente`, top 30 por execução), **nunca** "o impacto na previsão do dia
seguinte" — regra semântica permanente (`PLAN.md` Fase 9/Anexo A.5: Prophet → volume
futuro; XGBoost → risco; SHAP → explicação individual do risco do XGBoost; nunca misturar
as três). Nenhum campo ou label do payload deve mencionar "previsão"/"amanhã" nesse bloco.

**Critérios de aceite:**
1. `importancia_conceitos` ordenado por `rank` asc; reflete a `data_execucao` mais recente
   de `ml.fct_importancia_conceito` quando essa tabela tiver linhas para a execução — nesse
   caso `granularidade="conceito"`.
2. Quando `ml.fct_importancia_conceito` estiver vazia para a execução mais recente
   (fallback de gain do XGBoost), o endpoint usa `ml.fct_importancia_feature` e
   `granularidade="coluna"` — o campo `granularidade` nunca é omitido em nenhum dos dois
   casos.
3. `shap_top_risco` contém **todas as linhas** (grão incidente×feature, ~7 por incidente —
   210 linhas para os 30 incidentes de uma execução típica) da execução mais recente de
   `ml.fct_shap_incidente` — a seleção do top 30 já acontece na origem (a tabela só é
   populada com esses incidentes), então a API filtra só por `data_execucao`, **nunca**
   aplica um `LIMIT` por linha (um `LIMIT 30` por linha corta no meio de um incidente e
   devolve menos de 30 incidentes distintos — bug já encontrado e corrigido na
   implementação). Nenhum campo do payload usa os termos "previsão" ou "amanhã".
4. `heatmap_categoria_dia` cobre as combinações categoria × `dia_semana_num` de
   `dw.fct_incidentes` com volume > 0, **limitado às N categorias de maior volume total**
   (sugestão: 10) — `dw.dim_produto_categoria` tem **141 categorias distintas em uso**
   (confirmado nesta auditoria), então "todas as combinações" sem limite geraria ~987
   células, impraticável para um heatmap; nenhuma célula das categorias exibidas fica
   ausente por volume zero.

### 4.5 `GET /api/clusters`

Fontes: `ml.fct_perfil_cluster` join `ml.dim_cluster` (execução mais recente).

> ⚠️ **Dois achados de auditoria (2026-08-22), verificados ao vivo contra o banco:**
> 1. `ml.fct_perfil_cluster.taxa_sla_violado_pct` é calculada em
>    `model_clustering_kmeans_Revisado.ipynb` a partir de `excedeu_tempo_esperado`
>    (duração > threshold da prioridade) — **94-98% em todos os 4 clusters** no banco real
>    hoje. O indicador oficial de SLA (`kpi_status_int=1`, o mesmo da tela KPI) dá
>    **0,95%** no total do banco — duas definições de "violação" com ordens de grandeza de
>    distância. Decisão (checkpoint humano, sem retreinar nem alterar a tabela): o campo é
>    renomeado no payload da API para `taxa_excedeu_tempo_esperado_pct` e o payload carrega
>    uma nota fixa (`nota_metrica_sla`) explicando a diferença — nunca chamar esse campo de
>    "SLA" sem qualificação em nenhuma tela.
> 2. `ml.dim_cluster` (taxonomia curada manualmente, não recalculada a cada execução — ver
>    `docs/dicionario-dados.md`) **diverge das métricas reais** de `ml.fct_perfil_cluster`
>    para pelo menos 2 dos 4 clusters: cluster B é rotulado `"Recorrentes rápidos"` /
>    `"Alta frequência · Curta duração"`, mas tem a **maior** `duracao_media_horas` dos
>    quatro (198,3h); cluster D é rotulado `"Baixo impacto"` / `"Sem violações"`, mas tem a
>    **maior** `taxa_excedeu_tempo_esperado_pct` (98,0%) e a 2ª maior duração (93,8h). Isso
>    não é um bug de código — é conteúdo curado manualmente que ficou desatualizado (a
>    migration `018_ml_dim_cluster.sql` registra que veio do mockup original e não é
>    reescrita a cada execução do K-Means). **Não corrigido nesta etapa** — reescrever
>    `nome_perfil`/`descricao_curta`/`tags` é decisão de produto/conteúdo, não algo para a
>    camada de API decidir sozinha; a API só repassa o que está em `ml.dim_cluster`, como
>    já fazia. Recomendação: registrar como item de dívida técnica no `PLAN.md` Anexo A
>    (mesmo padrão dos achados de PCA/OneHotEncoder já lá) e revisar a taxonomia com
>    checkpoint humano antes de a tela Clusters ir ao ar com dado real.

```json
{
  "clusters": [
    {
      "cluster_id": "A", "nome_perfil": "Críticos prolongados",
      "descricao_curta": "Alta duração · P2 dominante · Alto risco OLA",
      "tags": ["Infra", "Rede", "P2", "Seg-Ter"], "cor_hex": "#ef4444",
      "n_incidentes": 13289, "pct_volume": 32.1,
      "duracao_media_horas": 30.8, "taxa_resolucao_pct": 95.4,
      "taxa_excedeu_tempo_esperado_pct": 94.8
    }
  ],
  "modelo_versao": "kmeans_v1",
  "data_execucao": "2026-08-22T11:56:19Z",
  "nota_metrica_sla": "taxa_excedeu_tempo_esperado_pct mede duração > threshold da prioridade (heurística usada como rótulo de treino do XGBoost) — não é o indicador oficial de SLA (kpi_status_int, exibido na tela KPI), que é ordens de grandeza menor no mesmo banco."
}
```

Exemplo com números reais de uma execução real (não fabricados) — ver achado 2 acima antes
de usar `nome_perfil`/`descricao_curta`/`tags` como se descrevessem fielmente as métricas
do mesmo cluster. Nota de contexto (`PLAN.md` Fase 10/Anexo A.4): `k=4` é a segmentação em
produção, sem defesa estatística forte nem motivo para trocar (diagnóstico `k=2..8` já
executado, read-only, ver `docs/metricas-validacao.md`) — o endpoint não expõe métricas de
diagnóstico (`silhouette`/`davies_bouldin`), só os perfis; essas métricas ficam em
documentação técnica/Sprint 3, nunca nesta tela (mesma
regra do `PLAN.md`, "Correção conceitual importante", aplicada aqui por analogia ao KPI).

**Critérios de aceite:**
1. Retorna exatamente os `cluster_id` presentes em `ml.dim_cluster` (A–D), cada um casado
   1:1 com sua linha mais recente em `ml.fct_perfil_cluster` por `data_execucao`.
2. Soma de `pct_volume` de todos os clusters retornados está entre 99% e 101% (tolerância
   de arredondamento).
3. `tags` é sempre uma lista (split de `ml.dim_cluster.tags`, CSV) — nunca a string bruta
   com vírgulas.

### 4.6 `GET /api/alertas`

Fontes: `ml.fct_previsao_diaria_total` + `ml.fct_previsao_categoria` (D+1 vs. média
histórica), `ml.fct_perfil_cluster` (risco por cluster), `ml.fct_pressao_equipe` (pressão
por equipe — **novo neste PRD**), `dw.fct_recorrencia_operacional` (recorrência por
produto/categoria — **novo neste PRD**). Recomendações geradas por regras de negócio no
backend, referenciando os mesmos dados de alertas — não vêm de nenhuma tabela nova.

Catálogo de regras (`PLAN.md` Fase 11 — 5 regras, cada uma com `regra_origem` explícito):

| `regra_origem` | Condição (limiar fixo, documentado no código) | Fonte |
|---|---|---|
| `pico_volume_d1` | variação de `ml.fct_previsao_diaria_total` D+1 vs. média histórica acima de um limiar fixo | `ml.fct_previsao_diaria_total` |
| `pressao_operacional_equipe` | `pressao_relativa_pct` de `ml.fct_pressao_equipe` acima de um limiar fixo (`>30%` crítico, `10-30%` atenção — mesmos limiares do notebook, §4.1) | `ml.fct_pressao_equipe` |
| `cluster_alta_violacao` | cluster com `taxa_excedeu_tempo_esperado_pct` (§4.5 — campo renomeado, não é o indicador oficial de SLA) acima de um limiar fixo | `ml.fct_perfil_cluster` |
| `concentracao_categoria` | categoria concentrando volume previsto acima de um limiar | `ml.fct_previsao_categoria` |
| `recorrencia_operacional` | entidade (produto/categoria) com `status_recorrencia="recorrente_crescente"` em `dw.fct_recorrencia_operacional` — enum real, ver §4.2 (não existe o valor `"recorrente"` sozinho) | `dw.fct_recorrencia_operacional` |

`pico_volume_d1` e `concentracao_categoria` são sempre retornados (baseline informativo,
`tipo="info"` quando não há nada fora do normal); `pressao_operacional_equipe`,
`cluster_alta_violacao` e `recorrencia_operacional` só aparecem quando a condição da regra
é satisfeita — sem alerta vazio.

```json
{
  "alertas": [
    {
      "tipo": "atencao", "regra_origem": "concentracao_categoria",
      "titulo": "cat71 concentra o volume previsto de D+1",
      "mensagem": "cat71 responde por 18,7 dos 124,5 incidentes previstos para D+1 (15,0% do total)."
    }
  ],
  "recomendacoes": [
    {"ordem": 1, "texto": "Antecipar triagem de cat71 na abertura, roteirizando direto para a fila especializada.",
     "prioridade": "media", "regra_origem": "concentracao_categoria"}
  ]
}
```

**Critérios de aceite:**
1. `alertas` nunca inclui um alerta de recorrência por **item de configuração** (CI) —
   explicitamente fora de escopo (§3). Um alerta `regra_origem="recorrencia_operacional"`
   por **produto/categoria** (fonte `dw.fct_recorrencia_operacional`) é válido e esperado —
   não confundir os dois no código nem na revisão.
2. Cada alerta em `alertas` tem `tipo` determinado por uma regra fixa e documentada no
   código (ex.: `critico` se `variacao_pct_vs_media_historica` do D+1 > 20%) — nunca uma
   regra ad-hoc não documentada; todo alerta traz `regra_origem` apontando para uma das 5
   regras da tabela acima.
3. Cada item de `recomendacoes` tem `regra_origem` referenciando qual das 5 regras gerou o
   texto — nenhuma recomendação sem rastreabilidade à regra que a gerou.
4. `recomendacoes` é gerado inteiramente a partir dos dados já expostos por `/api/alertas`,
   `/api/painel` (pressão por equipe), `/api/detalhe` (recorrência) e `/api/clusters` (sem
   tabela nova) — nenhuma dependência de dado fora do escopo desta etapa.
5. Um alerta `pressao_operacional_equipe` só é gerado quando pelo menos uma equipe tem
   `nivel_pressao != 'normal'` na execução mais recente de `ml.fct_pressao_equipe` — sem
   equipe em `atencao`/`critico`, o endpoint não fabrica um alerta vazio.

## 5. Dependências

- `db/migrations/024_dw_ref_meta_sla_anual.sql`, `026_ml_fct_pressao_equipe.sql`,
  `027_ml_fct_previsao_produto.sql`, `028_dw_fct_recorrencia_operacional.sql` — **já
  aplicadas** (`PLAN.md` Fases 3/4/5/8, 2026-08-22); nenhuma migration nova necessária para
  o escopo deste PRD.
- As saídas de modelo (`ml.fct_previsao_*`, `ml.fct_pressao_equipe`, `ml.fct_perfil_cluster`,
  `ml.fct_importancia_feature`/`_conceito`/`fct_risco_incidente`/`fct_shap_incidente`) e as
  tabelas de regra de negócio (`dw.ref_meta_sla_anual`, `dw.fct_recorrencia_operacional`)
  precisam já estar populadas — todas confirmadas populadas nesta auditoria (`PLAN.md`
  Fase 1).
- `etl/db.py` (`get_engine()`) como única via de conexão — nenhum endpoint deve abrir
  conexão própria.
- `etl/ref_meta_sla.py::faixa_meta_sla()` reaproveitado diretamente pelo endpoint
  `/api/kpi` — não reimplementar a lógica de faixa na camada HTTP.
- Roteamento em `app/api/routers/` (um módulo por tela, registrado em `app/api/main.py`).

## 6. Riscos

- **Proporção histórica mal interpretada na Etapa 6**: mesmo com `metodologia`/
  `share_historico` na resposta, o frontend pode ignorar o campo e renderizar como se fosse
  forecast por corte — mitigar deixando o campo em todo item, não só como metadado global.
- **Reinterpretação do painel SHAP diverge de uma leitura ingênua do dado**: o campo nunca
  deve mencionar "previsão"/"amanhã" — mitigado por critério de aceite explícito (§4.4).
- **Meta de projeção linear (§4.3) usa uma leitura do schema de faixas ainda não confirmada
  por checkpoint humano** — não implementar `/api/kpi` sem antes confirmar qual `faixa_max`
  representa "a meta" na fórmula de projeção (callout ⚠️ em §4.3).
- **Divergência silenciosa entre o React estático (Fase 15) e o contrato real**: o mock
  atual (`dashboardData.ts::computeBandasMeta()`) mostra faixas de P1/P4 que não existem em
  `dw.ref_meta_sla_anual` — ao ligar a API real, a tela KPI precisa passar a mostrar só
  P2/P3 (§4.3, critério 1); isso é uma mudança visível de conteúdo, não só de fonte de
  dado, e vale comunicar antes de trocar.
- **Performance de agregação em `dw.fct_incidentes`**: heatmap e alguns cálculos de KPI
  agregam ~41 mil linhas por request sem cache — aceitável no volume atual, sem otimização
  prevista nesta etapa (não-objetivo §3).
- **Fallback de granularidade em `/api/fatores`**: quando `ml.fct_importancia_conceito`
  está vazia (execução do XGBoost sem SHAP, só gain), o endpoint muda de conceito de
  negócio para coluna crua — se o frontend ignorar o campo `granularidade`, a tela pode
  mostrar rótulos técnicos (`hora_sin`, `vol_hora_grupo`) sem nenhum aviso.
- **Alerta de recorrência por CI vs. por produto/categoria confundidos na implementação**:
  o nome da regra (`recorrencia_operacional`) é o mesmo em ambos os conceitos no texto
  histórico do projeto; mitigar com o critério de aceite explícito (§4.6, critério 1) e
  nunca introduzir uma fonte de CI nesta etapa.
