# MVP Locaweb — AIOps Incidentes

Pipeline de dados e dashboard de incidentes de TI: da tabela bruta de chamados no
banco Postgres `fiap` até um modelo dimensional (star schema) e uma aplicação web
com painéis interativos.

Pipeline de ITSM/AIOps completo: previsão de volume com Prophet, classificação de
risco de SLA com XGBoost, clustering de incidentes com K-Means. O modelo
dimensional usa surrogate keys `MD5(COALESCE(campo::text,''))` e convenção de
nomes `dim_*`/`fct_*`.

## Estrutura

```
notebooks/    Notebooks originais do projeto (forecast Prophet, risco XGBoost, clustering K-Means)
db/           DDL versionado do modelo dimensional (migrations) e dados de referência (seeds)
etl/          Transformação: tabela bruta de chamados -> dimensões + fato
app/api/      Backend FastAPI, consulta o modelo dimensional
app/web/      Frontend React (Vite), consome a API
tests/        Testes de ETL e API
docs/design/  Mockup de referência do dashboard (aiops_dashboard_redesign.html)
```

`notebooks/` contém o trabalho de modelagem original (previsão de volume, risco de
SLA, clustering) que fundamenta este pipeline — as saídas desses modelos são a fonte
de vários painéis do dashboard (ver `docs/design/aiops_dashboard_redesign.html`).

## Documentação

- [docs/resumo-projeto.md](docs/resumo-projeto.md) — estado atual do projeto (comece por aqui)
- [docs/dicionario-dados.md](docs/dicionario-dados.md) — colunas de todas as tabelas (fonte, `dw` e `ml`)
- [docs/schema-e-cobertura-mockup.md](docs/schema-e-cobertura-mockup.md) — catálogo de schema + comparativo tela a tela do mockup vs dados reais
- [docs/schema-fonte-incidentes.md](docs/schema-fonte-incidentes.md) — levantamento de `public.incidentes`
- [docs/modelo-dimensional.md](docs/modelo-dimensional.md) — grão, adaptações e como recarregar o `dw`

## Status

Projeto em construção — ver plano de execução por etapas. Documentação de setup,
grão da tabela fato e instruções de execução serão preenchidas nas próximas etapas
(inspeção de schema, modelagem dimensional, ETL, API, web).

## Pré-requisitos

- Postgres com acesso ao banco `fiap`
- Python 3.11+ e Node 18+
- Copiar `.env.example` para `.env` e preencher as credenciais do banco `fiap`
  (nunca commitar o `.env`)
