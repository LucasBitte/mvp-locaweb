# Sprint 3 — Apresentação final (PLAN.md Fase 16)

> Documento de storytelling do desafio **AIOps Locaweb/FIAP**: consolida em
> narrativa única o que já está espalhado em `CLAUDE.md`, `PLAN.md` e nos
> documentos técnicos de cada etapa (dicionário de dados, modelo
> dimensional, EDA, métricas de validação, contrato da API, changelogs).
> Nenhum número aqui é novo ou estimado — cada seção aponta para a fonte
> primária. Rótulos de apresentação das telas ("Operação", "OLA & Metas",
> "Fatores de Risco", "Perfis Operacionais", "Alertas & Ações") são usados
> livremente neste documento — é o único lugar do projeto onde isso é
> intencional (`PLAN.md` §4).

## 1. Contextualização

A Locaweb opera uma central de incidentes de TI que hoje é **reativa**: a
equipe descobre que um volume alto de chamados está chegando, ou que uma
equipe está sobrecarregada, só depois que já aconteceu. O desafio AIOps
pede um dashboard **preditivo**, que responda nove perguntas de negócio
antes do problema virar impacto operacional:

| Pergunta do desafio | Onde é respondida |
|---|---|
| O que vai acontecer? (D+1..D+7) | Painel — Prophet |
| Onde vai acontecer? (prioridade/categoria/equipe) | Operação — split proporcional + Prophet por equipe |
| P2/P3 estão sob risco? | Operação — foco padrão P2+P3 |
| Qual equipe estará sob maior pressão? | Painel — pressão operacional prevista |
| Qual produto/categoria exige atenção? | Operação — top categorias/produtos |
| Por que existe risco? | Fatores de Risco — XGBoost + SHAP |
| Quais padrões existem? | Perfis Operacionais — K-Means |
| Sazonalidade / recorrência? | Painel (sazonalidade semanal) + Operação (recorrência 30d) |
| O que fazer? | Alertas & Ações — regras prescritivas |

**Dado de origem**: `public.incidentes`, 122.543 chamados (2023-2025),
extraídos para o Postgres `fiap` (VPS próprio do projeto — sem dependência
de infraestrutura legada AWS/dbt/RDS, removida no início da Sprint 2).
A evolução cloud na Sprint 4 é aditiva: o Postgres continua origem, S3 vira
destino, dbt valida tabelas existentes e o React permanece o BI alvo. Isso
não restaura os caminhos de ingestão legados removidos nos PRs #24/#26.
Implementação e pendências de execução: `cloud/README.md`.
Corte para esforço operacional real (`status <> 'Sem Intervenção'`,
`aberto >= 2025-01-01`) resulta em **41.441 incidentes** — a população que
todo o resto do projeto usa. Ver `docs/dicionario-dados.md` e
`docs/modelo-dimensional.md`.

## 2. Gestão das Sprints

O projeto foi entregue em 3 sprints, do zero (repositório vazio) ao
dashboard funcional com API real — cronologia real do histórico de commits
(`git log`), não uma reconstrução:

### Sprint 1 — Fundação de dados (2026-08-21, PRs #1-#14)

Setup do repositório, inspeção do schema bruto, construção do modelo
dimensional (`dw.*`, star schema) e das marts de features (`ml.ml_*`), EDA
inicial adaptada para ler direto do banco `fiap`. Entrega: pipeline
bronze→silver→dw/ml rodando ponta a ponta contra dado real, zero
infraestrutura legada.

### Sprint 2 — Modelos de ML + correções de qualidade (2026-08-21/22, PRs #15-#29)

Os 4 modelos de ML rodando contra o banco com output real (`ml.fct_*`):
Prophet (forecast total), K-Means (clusters), XGBoost+SHAP (risco de SLA).
Nesta sprint dois problemas de qualidade de dado real foram encontrados e
corrigidos com rastreabilidade completa (não escondidos):

- **Threshold de SLA errado** (`dw.dim_prioridade`, P2=8h/P3=24h em vez de
  4h/12h oficiais) — corrigido 2026-08-21, com retreino do XGBoost (rótulo
  de treino dependia do threshold) e correção do bug de infraestrutura que
  isso revelou (`TRUNCATE` em `dw.*` quebrando por FK — trocado por UPSERT
  idempotente). Ver `docs/modelo-dimensional.md`.
- **Meta de OLA sem fonte real** — `dw.ref_meta_sla_anual` criada com os 24
  valores oficiais do Dicionário de Dados do desafio (2 indicadores × 2
  prioridades × 6 faixas), substituindo o placeholder do mockup.

Fechou também a previsão de demanda por equipe (`ml.fct_previsao_grupo`,
arquitetura híbrida A/B/C — Prophet individual para as equipes grandes,
split proporcional para a cauda longa).

### Sprint 3 — Lacunas do desafio + MVP funcional (2026-08-22)

Sprint mais longa em decisões, comprimida num único dia de trabalho
intenso. Nesta ordem:

1. **Fechamento de lacunas** (`PLAN.md` Fases 1-5/10/12/13): auditoria
   viva contra o banco, validação do foco P2/P3 (78,9% do volume real),
   pressão operacional por equipe (`ml.fct_pressao_equipe`), split por
   produto (`ml.fct_previsao_produto`), recorrência operacional
   (`dw.fct_recorrencia_operacional`), diagnóstico `k=2..8` do K-Means, EDA
   e métricas de validação consolidadas.
2. **Dashboard React** (6 telas) portado do design Claude Design, inicialmente
   com dado estático (mesmos números reais das fases acima, só não
   dinâmicos ainda).
3. **API FastAPI** (`PLAN.md` Fase 14): 6 endpoints servindo dado real,
   contrato completo documentado, 2 achados de auditoria confirmados ao
   vivo contra o banco (detalhados na seção 6 abaixo).
4. **Frontend religado à API** (`PLAN.md` Fase 15): as 6 telas passaram a
   buscar dado real via `fetch`, sem nenhum número estático restante; 3
   telas precisaram de redesenho porque o mockup original mostrava algo
   que o dado real não sustenta.
5. **Este documento** (`PLAN.md` Fase 16).

## 3. Arquitetura

```
public.incidentes              (bronze — 122.543 linhas, 2023-2025)
        │
        ▼  notebook 03
staging.incidentes_silver      (silver — 41.441 linhas, pós-2025)
        │
        ├──▶ notebook 04 ──▶ dw.*        (star schema, 6 dimensões + fato)
        │
        └──▶ notebook 05 ──▶ ml.ml_*     (marts de features, leakage-free)
                                   │
                                   ▼
                    forecast total / forecast por equipe / clustering / xgboost
                                   │
                              ml.fct_*   (saídas dos 4 modelos)
                                   │
                                   ▼
                        FastAPI (app/api/, 6 endpoints)
                                   │
                                   ▼
                        React (app/web/, 6 telas)
```

4 schemas no banco `fiap`: `public` (bronze), `staging` (silver), `dw`
(star schema para BI/API), `ml` (marts de features + saídas de modelo).
`dw.fct_incidentes` é a fato central — grão 1 linha = 1 incidente, 41.441
linhas, carregada via UPSERT idempotente (nunca `TRUNCATE`, por causa das
FKs de `ml.fct_risco_incidente`/`ml.fct_shap_incidente`). Documentação
completa: `docs/dicionario-dados.md` (coluna a coluna) e
`docs/modelo-dimensional.md` (raciocínio de design + correções).

**Camada de API** (`app/api/`): FastAPI somente leitura, SQL raw via
`sqlalchemy.text()` (sem ORM), um `pydantic.BaseModel` por endpoint como
`response_model`, engine cacheada via `etl.db.get_engine()`
(`app/api/deps.py`) — nenhum endpoint abre conexão própria. Contrato
completo endpoint a endpoint: `docs/prds/etapa5-api.md`.

**Camada de apresentação** (`app/web/`): React + Vite + TypeScript. Cliente
HTTP tipado (`src/lib/api.ts`, espelha os `pydantic.BaseModel` da API) +
hook de fetch/loading/erro (`src/lib/useApi.ts`). `src/data/dashboardData.ts`
contém só funções puras de apresentação (recebem a resposta da API,
devolvem geometria/texto prontos para renderizar) — nenhuma lógica de
negócio duplicada da API no frontend.

## 4. Modelos

4 modelos de ML, todos rodando contra o banco `fiap` real, com seeds fixas
(`random_state=42`, 11 ocorrências entre os 3 notebooks/script):

| Modelo | Lê de | Grava em | O que responde |
|---|---|---|---|
| **Prophet** (forecast total) | `ml.ml_forecast_dataset` | `ml.fct_previsao_diaria_total`/`_prioridade`/`_categoria` | D+1..D+7, com splits proporcionais por prioridade/categoria (não são modelos por corte) |
| **Prophet por equipe** | `ml.ml_base_features` | `ml.fct_previsao_grupo` + `ml.fct_pressao_equipe` | D+1..D+7 por equipe, arquitetura híbrida A/B/C conforme viabilidade da série (`docs/modelo-dimensional.md` e `docs/forecast-por-equipe.md`) |
| **K-Means** (clusters) | `ml.ml_cluster_dataset` | `ml.dim_cluster` + `ml.fct_perfil_cluster` | 4 perfis operacionais, `k=4` (checkpoint humano — seção 6) |
| **XGBoost + SHAP** (risco) | `ml.ml_sla_classification_dataset` | `ml.fct_importancia_feature`/`_conceito`, `ml.fct_risco_incidente`, `ml.fct_shap_incidente` | Score de risco por incidente + explicação individual (SHAP), não forecast |

**Regra semântica permanente, reforçada em toda a documentação do
projeto**: Prophet → volume futuro; XGBoost → risco; SHAP → explicação
individual do risco do XGBoost. As três nunca se misturam — em particular,
o painel de SHAP explica "por que este incidente tem risco elevado agora",
nunca "por que haverá mais chamados amanhã".

**Decisão de arquitetura mais visível da Sprint 2**: o forecast por equipe
não podia ser um split proporcional único, porque 16 equipes têm volumes
radicalmente diferentes (`Team14` sozinha = 41,3% do volume; 13 equipes
dividem 17,3%). A investigação (`notebooks/06_forecast_investigacao_equipe.ipynb`)
cortou em 3 grupos por viabilidade de série diária — Grupo A (Prophet
individual, 4 equipes), Grupo B (Prophet diário/semanal conforme
desempenho, 4 equipes), Grupo C (split proporcional, 8 equipes). Detalhe
completo em `docs/forecast-por-equipe.md`.

## 5. EDA

8 evidências no formato Achado/Impacto/Decisão, extraídas ao vivo do banco
`fiap` (`docs/eda-consolidada.md`). Os 3 achados mais relevantes para quem
vai usar o dashboard:

1. **O "salto de regime" não existe no dado que os modelos usam.** A
   tabela bruta (`public.incidentes`) tem um salto de ~21-27 mil/mês
   causado por ruído de monitoramento autorresolvido — mas no grão
   filtrado que os modelos realmente treinam (`dw.fct_incidentes`,
   `ml.ml_forecast_dataset`), o volume mensal de 2025 é estável (2.343 a
   4.053/mês). Corrige um mal-entendido que já estava documentado em
   `docs/schema-fonte-incidentes.md`.
2. **P2+P3 = 78,9% do volume real** (P3 sozinha já é 56,2%) — confirma que
   o foco padrão do desafio nessas duas prioridades cobre a maioria
   operacional, não uma fatia arbitrária; P1 tem 1 incidente em todo o
   histórico (0,0%), volume insuficiente para qualquer modelo dedicado.
3. **Violação de SLA oficial é um evento raro** (`kpi_status_int=1` =
   0,6%, 238 incidentes), **completamente diferente** do rótulo de treino
   do XGBoost (`target_excedeu_tempo`, duração > threshold, ~95% de base
   rate). São dois conceitos de "risco" que não podem ser tratados como
   sinônimos — é a raiz do achado de auditoria da seção 6.

Sazonalidade semanal confirmada (pico quinta-feira, 7.954 incidentes;
queda no fim de semana, domingo 2.482) e "storm days" por incidente-pai (22
dias com um único chamado-pai respondendo por ≥40% do volume diário de uma
equipe) — ambos já tratados no Prophet (`weekly_seasonality`/`holidays`
pontuais), sem ação nova necessária.

## 6. Validação

Métricas consolidadas dos 3 modelos preditivos, reaproveitando os
artefatos já gerados — **não reconstruídas do zero** (`docs/metricas-validacao.md`).

| Modelo | Meta registrada | Resultado real | Status |
|---|---|---|---|
| Prophet (forecast total) | Superar baseline em MAE | **Não supera** `mediana_dow_4sem` (MAE 35,73 vs. 31,24) — ganha em cobertura de intervalo (78,6%) | ⚠️ |
| XGBoost (risco de SLA) | AUC-ROC ≥ 0,85 | 0,80 (teste) / 0,76 (backtest) — **não atingida** | ⚠️ |
| K-Means (clusters) | `k=4` definido a priori | Silhouette máximo em `k=2` (0,3814), Davies-Bouldin mínimo em `k=8` (0,8961) — `k=4` não vence em nenhuma métrica, mas também não é o pior | ⚠️ |

Nenhum destes três "⚠️" é uma falha silenciosa nem exige ação automática —
todos já estavam nos artefatos de treino, só não estavam consolidados num
único lugar antes desta Sprint. Cada um é uma decisão que continua sendo
do time (retreinar Prophet? relaxar a meta de AUC-ROC? trocar `k`?), não
decidida por este projeto.

**Achado adicional, crítico para não interpretar mal o XGBoost**: a classe
positiva do modelo (`target_excedeu_tempo` = duração > threshold da
prioridade) tem base rate de 95% — é majoritária, não o evento raro que se
esperaria de "risco de violação de SLA". O motivo é a mediana real de
duração (87,9h) já exceder os thresholds de SLA por construção. Isso é
**diferente** do indicador oficial de SLA (`kpi_status_int=1`, 0,6% do
volume) usado na tela OLA & Metas. Confirmado de novo, de forma
independente, ao construir a API (Fase 14): `ml.fct_perfil_cluster.
taxa_sla_violado_pct` usa exatamente essa métrica ampla (94-98% em todos
os 4 clusters), não a oficial — por isso a API expõe o campo renomeado
(`taxa_excedeu_tempo_esperado_pct`) com uma nota explicativa em todo
payload de `/api/clusters`, para a tela Perfis Operacionais nunca
contradizer a tela OLA & Metas.

Um segundo achado, de conteúdo (não de cálculo): a taxonomia curada de
`ml.dim_cluster` (nomes/descrições/tags dos 4 perfis, escritos à mão a
partir do mockup original) diverge das métricas reais em pelo menos 2 dos
4 clusters — um cluster rotulado "curta duração" tem a *maior* duração
média real (198,3h), outro rotulado "sem violações" tem a *maior* taxa de
excesso de tempo esperado (98,0%). Não corrigido — é decisão de conteúdo,
registrada como checkpoint humano pendente em `PLAN.md` Anexo A.3/A.4.

## 7. MVP funcional (Etapas 5-6)

As 6 telas do dashboard, com dado real de ponta a ponta (nomes técnicos
canônicos e, entre parênteses, o rótulo de apresentação):

| Tela | Fonte real | Pergunta que responde |
|---|---|---|
| **Painel** ("Visão geral") | `ml.fct_previsao_diaria_total` + `ml.fct_pressao_equipe` | O que vai acontecer? Qual equipe está sob maior pressão? |
| **Detalhe** ("Operação") | `ml.fct_previsao_prioridade`/`_categoria`/`_produto` + `dw.fct_recorrencia_operacional` | Onde vai se concentrar? P2/P3 sob risco? O que é recorrente? |
| **KPI** ("OLA & Metas") | `dw.ref_meta_sla_anual` + `dw.fct_incidentes` | Como estamos contra a meta oficial de SLA? |
| **Fatores** ("Fatores de Risco") | `ml.fct_importancia_conceito` + `ml.fct_shap_incidente` | Por que existe risco? |
| **Clusters** ("Perfis Operacionais") | `ml.dim_cluster` + `ml.fct_perfil_cluster` | Quais padrões existem? |
| **Alertas** ("Alertas & Ações") | Regras sobre as 5 telas acima | O que fazer? |

Todas as 6 telas rodam contra a API real (`app/api/`, 6 endpoints, 38
testes de contrato) — sem nenhum número estático restante. Verificado com
os 6 tabs num Chromium headless: zero erros de console, zero requisições
falhas.

**O que a tela Alertas & Ações prescreve hoje** (5 regras, cada
recomendação carrega `regra_origem` rastreável): `pico_volume_d1`
(variação de D+1 vs. média histórica), `pressao_operacional_equipe`
(desvio previsto vs. histórico da própria equipe), `cluster_alta_violacao`
(perfil com tempo excedido acima de limiar), `concentracao_categoria`
(categoria concentrando volume previsto), `recorrencia_operacional`
(entidade classificada como recorrente e em crescimento). Nenhuma regra
depende de item de configuração (CI) — dimensão que não existe no `dw`.

## 8. Storytelling

A história deste projeto não é só "construímos um dashboard preditivo" —
é **como um dado real e imperfeito foi tratado com rigor em cada etapa**,
em vez de forçado a caber num mockup bonito:

- Quando o threshold de SLA estava errado (Sprint 2), a correção não parou
  no valor da coluna — seguiu até o retreino do modelo que dependia dele e
  até o bug de infraestrutura (`TRUNCATE` vs. FK) que a correção revelou.
- Quando a meta de OLA do mockup era um placeholder de 2 linhas, o projeto
  não a manteve como estava — criou a tabela real do Dicionário de Dados
  oficial (24 linhas, 6 faixas por indicador) e reescreveu o contrato da
  API inteiro em cima dela.
- Quando a métrica de "violação" do cluster se revelou, na prática, uma
  coisa diferente do que o nome sugeria (95% vs. 0,6% no mesmo banco), a
  resposta não foi esconder o campo nem inventar um número que combinasse
  com a expectativa — foi renomear, documentar a diferença no próprio
  payload da API, e registrar o achado em 3 lugares (`CLAUDE.md`, `PLAN.md`
  Anexo A, `docs/prds/etapa5-api.md`) para não se perder.
- Quando a tela KPI do design original mostrava 4 prioridades com faixas
  de meta que não existem no banco, a tela foi redesenhada para mostrar as
  2 prioridades reais com meta — em vez de preencher as outras duas com
  números inventados só para a tela "parecer completa".

O fio condutor é o mesmo em todas essas decisões: **um número sem fonte
real nunca aparece como se tivesse** — ele fica `null`/explícito, é
documentado como lacuna, ou a tela é redesenhada em torno do que existe de
verdade. É a diferença entre um MVP que passa numa demonstração e um MVP
que resiste a alguém clicando em cada número perguntando "de onde isso
veio".

## 9. Conclusão

**Entregue**: pipeline completo bronze→silver→dw/ml→API→React, 4 modelos
de ML rodando contra dado real, 6 endpoints de API com contrato
documentado e testado, 6 telas de dashboard consumindo dado real sem
número estático, EDA e métricas de validação consolidadas, e — igualmente
importante — uma trilha de auditoria de cada correção e cada limitação
conhecida, sem nenhuma delas escondida atrás de um número bonito.

**Limitações conhecidas, registradas para decisão humana, não escondidas**:

1. Prophet em produção não supera o baseline simples em MAE/WAPE/MASE
   (ganha em cobertura de intervalo).
2. XGBoost não atinge a meta de AUC-ROC 0,85 registrada no próprio
   artefato (0,80 teste / 0,76 backtest).
3. K-Means `k=4` sem defesa estatística forte, mas também sem evidência
   clara para trocar.
4. Taxonomia curada de `ml.dim_cluster` (nomes/descrições dos 4 perfis)
   diverge das métricas reais em pelo menos 2 clusters — pendente de
   revisão de conteúdo.
5. `requirements.txt`/`requirements-notebooks.txt` sem pin de versão —
   checkpoint humano antes de fixar (`PLAN.md` Anexo A, ML-3).

Nenhuma dessas 5 é uma "próxima feature" — são decisões que precisam de
uma pessoa, não de mais código. O dashboard, hoje, responde as nove
perguntas do desafio com dado real, e é honesto sobre onde a resposta é
mais fraca do que a pergunta pediria.
