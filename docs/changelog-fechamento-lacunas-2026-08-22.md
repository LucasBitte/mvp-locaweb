# Changelog — Fechamento de lacunas (PLAN.md Fases 1-5/10/12/13), 2026-08-22

> Aplicação do `PLAN.md` (camada de dados/backend, sem FastAPI/React nesta
> rodada). Resumo do que mudou no banco `fiap` e nos dados que o futuro
> dashboard vai consumir. Nenhuma tabela de produção existente (`dw.dim_*`,
> `dw.fct_incidentes`, `ml.dim_cluster`, `ml.fct_perfil_cluster`,
> `ml.fct_risco_incidente` etc.) foi alterada ou retreinada.

## 1. Tabelas novas no banco `fiap`

| Tabela | Migration | Script que popula | Linhas | Schema completo |
|---|---|---|---|---|
| `ml.fct_pressao_equipe` | `026_ml_fct_pressao_equipe.sql` | `notebooks/pressao_equipe.py` | 112 (16 equipes × D+1..D+7) | `docs/dicionario-dados.md` |
| `ml.fct_previsao_produto` | `027_ml_fct_previsao_produto.sql` | `notebooks/forecast_produto.py` | 357 (51 produtos × D+1..D+7) | `docs/dicionario-dados.md` |
| `dw.fct_recorrencia_operacional` | `028_dw_fct_recorrencia_operacional.sql` | `notebooks/recorrencia.py` | 649 (4 granularidades) | `docs/dicionario-dados.md` |

Todas as 3 são **dado novo, aditivo** — nenhuma coluna de tabela existente
foi renomeada, removida ou teve seu tipo alterado. `ml.fct_pressao_equipe`
e `ml.fct_previsao_produto` seguem o padrão append/idempotente por `origem`
já usado em `ml.fct_previsao_grupo`/`_categoria`; `dw.fct_recorrencia_operacional`
é recarregada por completo a cada execução (janela móvel, não faz sentido
"append por origem").

## 2. O que isso muda para o dashboard (quando a Etapa 5/6 começar)

| Tela | O que ganha | Fonte nova |
|---|---|---|
| **Detalhe** (Onde vai estar concentrado?) | Pressão operacional por equipe (badge normal/atenção/crítico) e split de volume previsto por **produto** (além de categoria, que já existia) | `ml.fct_pressao_equipe`, `ml.fct_previsao_produto` |
| **Alertas** (O que fazer?) | Regras `pressao_operacional_equipe` e `recorrencia_operacional` (PLAN.md Fase 11) agora têm fonte de dado real para existir | `ml.fct_pressao_equipe`, `dw.fct_recorrencia_operacional` |
| **Painel/KPI/Fatores/Clusters** | Sem mudança de fonte nesta rodada | — |

Nenhum endpoint FastAPI foi criado ainda — essas tabelas ficam prontas para
a Etapa 5 consumir, não estão expostas via API.

## 3. Resultados obtidos (não são mudança de schema, mas são novos números reais)

- **Pressão por equipe (D+1)**: `Team02` +29,4% (atenção), `Team03` +17,0%
  (atenção), `Team17` +13,1% (atenção); nenhuma equipe em `critico` nesta
  execução; equipes de maior volume (Grupo A) estão todas abaixo da própria
  média histórica.
- **Split por produto (D+1)**: `lhco` lidera (27,7% do histórico, 34,5
  previstos), seguido de `lsin` (14,5%) e `lcem` (13,4%).
- **Recorrência**: exemplo de `recorrente_crescente` real em categoria —
  `cat94` (+466,7% vs. janela anterior, presente em 50% dos dias),
  `cat35` (+100,0%, 60% dos dias).
- **Diagnóstico k=2..8 do K-Means** (read-only, não alterou o modelo em
  produção): sem vencedor claro entre as métricas; `k=4` fica intermediário,
  sem defesa estatística forte nem motivo para trocar. Ver
  `docs/metricas-validacao.md` §3.
- **Consolidação de métricas** revelou 3 achados que precisam de decisão
  humana (nenhum é bug introduzido nesta rodada — já existiam nos artefatos
  dos modelos, só não estavam consolidados): Prophet em produção não supera
  o baseline simples `mediana_dow_4sem`; XGBoost não atinge a meta de
  AUC-ROC 0,85 registrada no próprio artefato; K-Means sem `k` ótimo claro.
  Ver `docs/metricas-validacao.md`.

## 4. Documentos novos

- `docs/eda-consolidada.md` — 8 evidências Achado/Impacto/Decisão.
- `docs/metricas-validacao.md` — métricas de Prophet/XGBoost/K-Means
  consolidadas.
- `docs/dicionario-dados.md` — atualizado com as 3 tabelas novas (seção
  correspondente de cada schema).
- `CLAUDE.md` — seção 2 (comandos) ganhou os 4 scripts novos na ordem de
  execução; seção 4 marca as lacunas de P2/P3, pressão por equipe, produto,
  recorrência e diagnóstico K-Means como fechadas.

## 5. O que NÃO mudou

- Nenhuma migration/tabela existente foi editada — só criação de tabelas
  novas (026, 027, 028).
- `ml.dim_cluster`, `ml.fct_perfil_cluster`, `ml.fct_risco_incidente`,
  `ml.fct_shap_incidente` e os demais `ml.fct_previsao_*` já existentes:
  intocados.
- Nenhum modelo foi retreinado (Prophet, K-Means, XGBoost seguem exatamente
  como estavam).
- `requirements.txt`/`requirements-notebooks.txt`: intocados (pin de versão
  continua pendente, checkpoint humano — Anexo A do `PLAN.md`, ML-3).
- FastAPI (`app/api/`) e React (`app/web/`): intocados — fora do escopo
  desta rodada (Fases 6-9/11/14-16 do `PLAN.md`).

## 6. Achado à parte (não relacionado a esta implementação)

`docs/design/aiops_dashboard_redesign.html` (mockup de referência das 6
telas) foi removido do disco durante esta sessão por ação externa a este
trabalho (confirmado com o usuário como intencional, não uma ação deste
agente). `CLAUDE.md` §1 ainda referencia esse caminho — se a remoção for
definitiva, essa referência precisa ser atualizada numa próxima revisão.
