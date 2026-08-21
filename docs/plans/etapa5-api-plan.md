# Plano — Etapa 5: API FastAPI (6 endpoints)

> Base: `docs/prds/etapa5-api.md` (aprovado) + `CLAUDE.md`. Plano de implementação — não
> contém código ainda; cada etapa abaixo vira um commit revisável na branch
> `feature/etapa5-api`.

## Contexto

`app/api/` hoje só tem `GET /health` (`app/api/main.py`). O PRD da Etapa 5
(`docs/prds/etapa5-api.md`) já decidiu, endpoint a endpoint, o contrato de resposta das
6 telas do mockup, incluindo dois pontos sensíveis documentados no `CLAUDE.md` §4/§8:

- o forecast por prioridade/categoria é proporção histórica, não modelo por corte —
  precisa do campo `metodologia`/`share_historico` em cada item, sempre;
- a meta de OLA (`dw.ref_meta_sla_anual`, ainda não existe) é placeholder — todo campo
  derivado dela precisa de `is_placeholder_*: true` explícito na resposta, nunca só
  escondido na UI.

Este plano quebra a implementação do PRD em etapas de tamanho de commit — uma por
endpoint/tela — para que cada uma seja revisável isoladamente antes de abrir o PR final.

## Convenções adotadas (consistentes com o código existente)

Confirmado por exploração de `etl/db.py`, `etl/transform.py`, `tests/test_api.py` e
`db/migrations/*`:

- **Conexão**: sempre via `etl.db.get_engine()` — nunca uma engine própria por módulo.
  Vou adicionar `app/api/deps.py` com um `get_db_engine()` cacheado (`functools.lru_cache`)
  injetado via `Depends` do FastAPI — é a única peça nova de infraestrutura compartilhada,
  criada junto com o primeiro endpoint (Etapa 2).
- **SQL**: raw SQL via `sqlalchemy.text()`, sem ORM — mesmo padrão de `etl/transform.py`.
  Sem `pandas` na camada de API (lá é usado para transformação em lote; aqui a resposta é
  JSON linha a linha, `conn.execute(text(sql), params).mappings().all()` é mais direto).
- **Validação de resposta**: um `pydantic.BaseModel` por endpoint, definido no próprio
  arquivo do router, usado como `response_model=` do FastAPI. Isso dá uma garantia
  estrutural extra: um campo obrigatório como `is_placeholder_meta` não pode ser esquecido
  silenciosamente — o Pydantic falha se não for setado.
- **Reuso entre routers**: `alertas.py` (Etapa 7) reaproveita as funções Python dos
  routers de Painel/Detalhe/Clusters chamando-as diretamente (elas continuam funções
  Python normais por trás do decorator `@router.get`) — não duplica SQL.
- **Testes**: `tests/test_api_<tela>.py`, `TestClient` contra a app real, mesmo padrão de
  `tests/test_api.py` hoje. Não há banco de teste separado (confirmado no `CLAUDE.md` §8) —
  os testes leem o banco `fiap` real (somente `SELECT`, nunca escrita), igual ao que a API
  fará em produção. Cada teste valida **contrato/estrutura** (campos presentes, tipos,
  invariantes tipo "soma de pct_volume ≈ 100"), não valores exatos que mudam a cada
  execução dos modelos.
- **Branch**: `feature/etapa5-api`, commits sequenciais nela: um por etapa abaixo. PR único
  ao final (Etapa 8), squash-merge — convenção já registrada no `CLAUDE.md` §6.

## Etapas

### Etapa 0 — Branch (setup, não é um commit de conteúdo)

Criar `feature/etapa5-api` a partir de `main` atualizada. Sem teste (nada para validar);
100% reversível (`git branch -D` local, branch remota nunca chega a existir se descartada
antes do primeiro push).

---

### Etapa 1 — Migration `dw.ref_meta_sla_anual` 🛑 CHECKPOINT HUMANO

**Por quê checkpoint**: esta migration grava os números de meta de OLA (31 quebras/ano
P2, 201/ano P3) que todo o resto da Etapa 5 vai expor como placeholder — é a primeira vez
que esse dado placeholder passa a existir formalmente no banco. `CLAUDE.md` §8 proíbe
apresentar esses números como reais sem confirmação explícita; requer revisão dos
valores e do `fonte='placeholder_mockup'` antes de aplicar no banco `fiap` real (não há
banco de teste separado).

> **Nota (2026-08-21)**: numerada `024`, não `023` — esse número foi tomado pela migration
> `023_ml_fct_importancia_conceito.sql` (PR #17), mesclada em `main` depois deste plano
> ter sido desenhado. Conferir `ls db/migrations/` antes de criar o arquivo, pra garantir
> que `024` ainda é o próximo número livre no momento da execução.

**Arquivos**: `db/migrations/024_dw_ref_meta_sla_anual.sql` (novo).

**O que fazer**: seguindo o formato de `018_ml_dim_cluster.sql` (comentário de contexto +
`CREATE TABLE IF NOT EXISTS` + seed via `INSERT ... ON CONFLICT DO NOTHING`):

```sql
CREATE TABLE IF NOT EXISTS dw.ref_meta_sla_anual (
    prioridade_num int NOT NULL,
    ano int NOT NULL,
    meta_quebras_ano int NOT NULL,
    fonte text NOT NULL,
    criado_em timestamp NOT NULL DEFAULT now(),
    PRIMARY KEY (prioridade_num, ano)
);

INSERT INTO dw.ref_meta_sla_anual (prioridade_num, ano, meta_quebras_ano, fonte)
VALUES
    (2, 2026, 31, 'placeholder_mockup'),
    (3, 2026, 201, 'placeholder_mockup')
ON CONFLICT (prioridade_num, ano) DO NOTHING;
```

**Teste que valida**: aplicar a migration no banco `fiap` (via `psql` ou script Python com
`get_engine()`), depois `SELECT * FROM dw.ref_meta_sla_anual` — confirmar 2 linhas,
`fonte='placeholder_mockup'` em ambas. Reaplicar a migration uma segunda vez para
confirmar idempotência (`IF NOT EXISTS` + `ON CONFLICT DO NOTHING` não duplica nem falha).

**Reversível**: sim — tabela nova, nenhuma FK de outra tabela aponta pra ela ainda. Reverter
é `DROP TABLE dw.ref_meta_sla_anual` (não há padrão de down-migration no projeto — as 22
migrations existentes são todas forward-only; se precisar desfazer, é uma migration nova
de `DROP`, não uma edição da 023).

---

### Etapa 2 — `GET /api/painel`

**Arquivos**: `app/api/deps.py` (novo — `get_db_engine()`), `app/api/routers/painel.py`
(novo), `app/api/main.py` (edita — `app.include_router(painel.router, prefix="/api")`),
`tests/test_api_painel.py` (novo).

**O que fazer**:
- `previsao_d1`: última `data_execucao` de `ml.fct_previsao_diaria_total` com
  `horizonte='D+1'`.
- `previsao_d7_media` + `variacao_pct_vs_media_historica`: média de `yhat` para
  `horizonte` D+1..D+7 da execução mais recente, comparada à média de `total_chamados`
  de `ml.ml_forecast_dataset` na mesma janela de `dias` (default 30) usada na série.
- `risco_ola.nivel`: média móvel de `pct_violacao_sla` (`ml.ml_forecast_dataset`) nos
  últimos 14 dias, contra faixas fixas no código (`<10` baixo, `10-20` médio, `>20` alto).
- `serie`: `dias` pontos históricos de `ml.ml_forecast_dataset.total_chamados` (ou
  `total_p{n}` se `prioridade` filtrado) + 7 pontos de previsão.
- Query param `prioridade` (default `todas`): quando setado, troca a fonte de
  `fct_previsao_diaria_total` para `ml.fct_previsao_prioridade` (mesma prioridade), e
  cada item de previsão ganha `metodologia="proporcao_historica"` + `share_historico`.

**Teste que valida** (`tests/test_api_painel.py`): `GET /api/painel` → 200; `serie` tem
exatamente `dias + 7` pontos; `risco_ola.nivel` ∈ `{baixo, medio, alto}`; com
`?prioridade=2`, todo item de previsão retornado tem `metodologia` e `share_historico`
não-nulos.

**Reversível**: sim — arquivos novos + 1 linha de `include_router` em `main.py`; reverter
o commit não afeta nenhum outro endpoint.

---

### Etapa 3 — `GET /api/detalhe`

**Arquivos**: `app/api/routers/detalhe.py` (novo), `app/api/main.py` (edita),
`tests/test_api_detalhe.py` (novo).

**O que fazer**:
- `prioridades`: `ml.fct_previsao_prioridade` (última `origem`, `horizonte` do query
  param, default `D+1`) join `dw.dim_prioridade` (por `prioridade_num`) para
  `threshold_sla_horas`/`bucket_prioridade` reais — **não** os valores do mockup.
- `pct_limite_mensal`/`is_placeholder_limite`: `LEFT JOIN dw.ref_meta_sla_anual` (ano
  corrente) `/ 12`; `is_placeholder_limite=true` sempre nesta etapa (não existe outra
  fonte). Se não houver linha de meta pro ano, `pct_limite_mensal=null`.
- `top_categorias`: `ml.fct_previsao_categoria`, última `origem`, `horizonte=D+1`,
  `ORDER BY yhat_categoria DESC LIMIT 5`, cada item com `metodologia`/`share_historico`.

**Teste que valida**: `prioridades` reflete exatamente o conjunto de `prioridade_num`
presente em `ml.fct_previsao_prioridade` pro horizonte pedido (nada hardcoded); pra cada
prioridade, `threshold_sla_horas` bate com `dw.dim_prioridade` (P2=8, P3=24 — não os
valores do mockup); `is_placeholder_limite=true` em toda linha; `top_categorias` tem no
máximo 5 itens, ordenados desc.

**Reversível**: sim.

---

### Etapa 4 — `GET /api/kpi` 🛑 CHECKPOINT HUMANO

**Por quê checkpoint**: é literalmente o contrato de resposta da tela KPI — o endpoint
que decide como `is_placeholder_meta` aparece, como `status` (`no_prazo`/`atencao`/
`critico`) é derivado, e como a "probabilidade de atingir meta anual" é calculada
(projeção linear simples, decisão já tomada no PRD, mas a implementação exata dos
thresholds de `status` é código novo que merece revisão antes de existir no banco real).

**Arquivos**: `app/api/routers/kpi.py` (novo), `app/api/main.py` (edita),
`tests/test_api_kpi.py` (novo).

**O que fazer**:
- `dias_decorridos`/`dias_restantes`: calculado a partir de `ano` (query param, default
  ano corrente) vs. data atual.
- `quebras_mes_atual`/`volume_tratado_mes`: `COUNT`/`SUM` sobre `dw.fct_incidentes`
  (`kpi_status_int=1` para quebras), filtrado por prioridade + mês/ano corrente, join
  `dw.dim_prioridade`.
- `meta_quebras_ano`/`is_placeholder_meta`: de `dw.ref_meta_sla_anual` (Etapa 1);
  `is_placeholder_meta=true` sempre que `fonte='placeholder_mockup'`.
- `probabilidade_atingir_meta_pct`: `(quebras_ate_agora / dias_decorridos) *
  dias_totais_do_ano`, comparado a `meta_quebras_ano`; `metodologia_probabilidade=
  "projecao_linear"` sempre no payload.
- `status`: thresholds fixos no código (quebras projetadas > meta → `critico`; > 70% da
  meta → `atencao`; caso contrário → `no_prazo`).

**Teste que valida**: `is_placeholder_meta=true` em toda prioridade retornada (teste de
contrato que falha se o campo sumir); `quebras_mes_atual` bate com uma query `COUNT(*)`
manual escrita no próprio teste contra `dw.fct_incidentes`; `metodologia_probabilidade`
sempre presente; `status` ∈ `{no_prazo, atencao, critico}`.

**Reversível**: sim (endpoint novo, aditivo) — mas por ser o contrato mais sensível do
PRD, revisão humana explícita antes do commit entrar na branch.

---

### Etapa 5 — `GET /api/fatores`

**Arquivos**: `app/api/routers/fatores.py` (novo), `app/api/main.py` (edita),
`tests/test_api_fatores.py` (novo).

> **Nota (2026-08-21)**: fonte de `importancia_features` mudou depois deste plano ter
> sido desenhado. A migration `023_ml_fct_importancia_conceito.sql` (PR #17, já aplicada
> e já populada) criou a tabela que o mockup realmente precisa — importância agrupada por
> **conceito de negócio** ("Dia da semana", "Categoria", "Prioridade do chamado"), não por
> coluna crua. Detalhe completo em `docs/prds/etapa5-api.md` §4.4.

**O que fazer**:
- `importancia_conceitos`: `ml.fct_importancia_conceito` (primária), última
  `data_execucao`, `ORDER BY rank`, com `granularidade="conceito"` no payload. Se essa
  tabela estiver vazia pra execução mais recente do XGBoost (acontece quando o modelo
  rodou só com fallback de gain, sem SHAP), cair para `ml.fct_importancia_feature`
  (coluna crua) com `granularidade="coluna"` — campo sempre presente, nunca omitido.
- `shap_top_risco`: `ml.fct_shap_incidente`, última `data_execucao` (até 30 incidentes,
  já é o grão da tabela). **Reinterpretação registrada no PRD**: nenhum campo/label
  menciona "previsão" ou "amanhã" — é explicação dos incidentes de maior risco atual, não
  do forecast de volume.
- `heatmap_categoria_dia`: `dw.fct_incidentes` join `dim_produto_categoria` +
  `dim_tempo` (`dia_semana_num`/`nome_dia`), `GROUP BY` categoria + dia da semana,
  `AVG`/`COUNT` conforme definição de "volume médio".

**Teste que valida**: `importancia_conceitos` ordenado por `rank`; `granularidade`
sempre presente e coerente com a tabela de origem usada (`conceito` vs `coluna`);
`shap_top_risco` tem no máximo 30 itens; varredura automática do JSON da resposta
garantindo que nenhuma string de valor contém "previsão" ou "amanhã" (case-insensitive) —
é o teste que trava a reinterpretação do painel SHAP, não deixa regressão silenciosa;
`heatmap_categoria_dia` cobre todas as combinações com volume > 0 (sem célula real
ausente).

**Reversível**: sim.

---

### Etapa 6 — `GET /api/clusters`

**Arquivos**: `app/api/routers/clusters.py` (novo), `app/api/main.py` (edita),
`tests/test_api_clusters.py` (novo).

**O que fazer**: `ml.fct_perfil_cluster` join `ml.dim_cluster`, última `data_execucao`;
`tags` convertido de CSV (`ml.dim_cluster.tags`) para lista antes de responder.

**Teste que valida**: conjunto de `cluster_id` retornado é exatamente o de
`ml.dim_cluster`; soma de `pct_volume` entre 99% e 101%; `tags` é `list[str]`, nunca a
string bruta com vírgulas.

**Reversível**: sim.

---

### Etapa 7 — `GET /api/alertas`

**Arquivos**: `app/api/routers/alertas.py` (novo — reaproveita funções de `painel.py` e
`clusters.py`), `app/api/main.py` (edita), `tests/test_api_alertas.py` (novo).

**O que fazer**:
- `alertas`: regras fixas e documentadas em código sobre os mesmos dados já expostos por
  Painel/Detalhe (ex.: `critico` se variação D+1 vs média > 20%; `info` se D+7 cai num
  fim de semana com `pct_violacao_sla` histórico de fins de semana = 0).
- `recomendacoes`: geradas por regras simples no backend (decisão do PRD), cada uma com
  `regra_origem` apontando pra qual regra a gerou — sem tabela nova, sem dado fora do que
  já está exposto por `/api/painel`, `/api/detalhe`, `/api/clusters`.

**Teste que valida**: nenhum alerta do tipo "recorrência de item de configuração"
(fora de escopo — não-objetivo do PRD); todo item de `recomendacoes` tem `regra_origem`
não-nulo pertencente a um conjunto fixo de ids de regra conhecidos (testável sem depender
do estado exato do banco).

**Reversível**: sim.

---

### Etapa 8 — Fechamento e PR para `main` 🛑 CHECKPOINT HUMANO

**Por quê checkpoint**: é a etapa final antes do merge em `main` (protegida) — pedido
explícito, além de ser sempre exigido pelo `CLAUDE.md` §6/§8.

**Arquivos**: `CLAUDE.md` (atualiza a linha da Etapa 5 na tabela de status, seção 9, de
`⬜ próximo passo` para `✅`), `docs/prds/etapa5-api.md` (atualiza o `> Status: proposto`
do topo para `implementado`).

**O que fazer**: rodar a suíte completa (`pytest tests/`), revisar o diff acumulado da
branch (`git diff main...feature/etapa5-api`), abrir o PR via `gh pr create` (squash-merge,
conforme convenção) — só depois de revisão explícita, sem push direto em `main`.

**Teste que valida**: `pytest tests/` verde (inclui todos os `test_api_*.py` das etapas
2–7 + os testes já existentes); todos os 6 endpoints respondendo 200 contra o banco
`fiap` real numa checagem manual rápida (`curl`/Swagger UI em `/docs`).

**Reversível**: sim antes do merge (branch/PR podem ser fechados sem tocar `main`); depois
do merge, reversão exigiria um novo PR de revert — por isso é o checkpoint mais crítico.

## Verificação end-to-end (depois de todas as etapas)

1. `./venv/bin/pytest tests/` — suíte completa verde.
2. Subir a API localmente (`uvicorn app.api.main:app --reload`) e abrir `/docs` (Swagger),
   testar manualmente os 6 endpoints contra o banco `fiap` real.
3. Conferir visualmente que nenhuma resposta de `/api/kpi` ou `/api/detalhe` omite os
   campos `is_placeholder_*`, e que `/api/fatores` não menciona "previsão"/"amanhã" no
   bloco de SHAP.
