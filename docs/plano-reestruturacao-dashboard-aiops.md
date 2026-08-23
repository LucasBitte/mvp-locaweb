# Auditoria + Plano de Reestruturação do Dashboard AIOps (mvp-locaweb)

## Contexto

O dashboard atual (6 telas: Painel/Detalhe/KPI/Fatores/Clusters/Alertas) já está
religado à API real (Fase 15, 2026-08-22) e contém análises corretas em boa
parte — mas cresceu tela-a-tela, sem um storytelling único, e carrega heranças
de decisões tomadas em momentos diferentes do projeto (nomes de cluster
desatualizados, achados de auditoria já corrigidos mas ainda narrados como
bug nos docs, campos que a API já expõe mas o front não usa). O pedido desta
etapa é auditar tudo contra a fonte de verdade real (banco `fiap`, código
executado, não os docs) e desenhar a nova arquitetura de 6 telas
(Sobre/Visão Estratégica/Forecast/Risco/Perfis/Ações) sem perder nenhum
requisito já atendido. **Nenhum código será alterado nesta etapa** — este
documento é o entregável.

Toda a auditoria abaixo foi feita cruzando: os 4 guias educacionais dos
modelos, `docs/forecast-por-equipe.md`, `docs/metricas-validacao.md`,
`docs/eda-consolidada.md`, `PLAN.md` (Anexo A + matrizes), `CLAUDE.md`,
`docs/dicionario-dados.md`, `docs/modelo-dimensional.md`,
`docs/prds/etapa5-api.md`, os 6 routers de `app/api/`, as migrations DDL de
`db/migrations/`, os 6 componentes de tela + `dashboardData.ts`/`api.ts` em
`app/web/src/`, e **queries read-only diretas no banco `fiap`** para
confirmar o estado real de `ml.dim_cluster`, `ml.fct_perfil_cluster`,
`dw.fct_incidentes.kpi_status_int`/`excedeu_tempo_esperado`, e
`ml.fct_previsao_grupo.metodo`.

**Achado estrutural mais importante desta auditoria**: dois dos "pontos
conhecidos a investigar" listados como P0 (divergência de nomes de cluster;
XGBoost rotulado como "violação de OLA") **já foram corrigidos no código e
no banco** — mas a documentação (PRD, `CLAUDE.md`, docstrings) ainda narra o
bug antigo como se estivesse aberto. Isso não é motivo para pular a
auditoria — é exatamente o tipo de divergência doc-vs-realidade que a regra
de hierarquia da fonte de verdade existe para pegar. Em compensação, a
auditoria encontrou **6 gaps reais e novos** que não estavam no radar:
metodologia do Prophet total mal rotulada no card principal do Painel,
ausência de intervalo de confiança e de comparação-com-baseline em qualquer
tela, ausência de métricas de qualidade do XGBoost (AUC/MCC/Brier) em
qualquer endpoint, e o card de "pressão por equipe" escondendo o método
(individual/semanal/split) que a API já devolve. Um sexto ponto exigiu
revisão após a primeira versão desta auditoria: a hipótese original de
`base_value + Σshap == logit(score_calibrado)` estava **conceitualmente
errada** — o `TreeExplainer` do SHAP explica a saída bruta do XGBoost
(antes do calibrador isotônico), não a probabilidade calibrada final. A
Parte B (achado #7) e a Parte D (Tela 03) já refletem a versão corrigida:
`XGBoost (saída bruta) → SHAP explica a saída bruta → calibrador isotônico
→ probabilidade final`, como duas etapas distintas, nunca uma única soma.

---

## Parte A — Resumo Executivo

**Diagnóstico geral**: a infraestrutura de dados (DW + ML marts + API) é
sólida e majoritariamente honesta — nenhum número de KPI real está
fabricado, os 2 achados de auditoria mais citados no projeto já foram
corrigidos, e os placeholders (`sem fonte`, `is_placeholder_limite`) são
tratados com transparência. Os problemas reais são de **3 naturezas**:

1. **Contrato de API incompleto para o que a nova Tela 03/02 exige**: SHAP
   sem `base_value`, XGBoost sem métricas de qualidade expostas, Prophet
   total sem intervalo de confiança nem comparação com baseline. Nenhum
   desses é "dado errado" — é dado que existe no pipeline/parquet mas nunca
   chegou a uma tabela `ml.*`/endpoint.
2. **Front dessincronizado do que a API já oferece**: `metodo_origem` por
   equipe existe na resposta e é ignorado; a legenda de metodologia do
   card de previsão D+1 é uma string fixa que contradiz o campo real
   quando a previsão vem de um modelo treinado (Prophet) em vez de uma
   regra (proporção histórica) — isso é uma instância exata do "regra ≠
   Machine Learning" que não pode ficar embaralhado.
3. **Documentação desatualizada em relação ao banco**: PRD, `CLAUDE.md` e
   comentários de código ainda descrevem o cluster B/D com os nomes
   antigos (pré-migrations 029/030), que já foram corrigidos há dias.

**Arquitetura proposta**: aceitar a estrutura de 6 telas pedida
(00 Sobre · 01 Visão Estratégica · 02 Forecast & Capacidade · 03 Risco &
Explicabilidade · 04 Perfis Operacionais · 05 Ações & Governança),
storytelling `PREVER → PRIORIZAR → EXPLICAR → SEGMENTAR → AGIR`. **Uma
decisão de preservação precisa ficar explícita**: a tela KPI atual (metas
anuais/faixas/probabilidade de atingimento, `dw.ref_meta_sla_anual`)
responde uma pergunta que nenhuma das 6 novas perguntas cobre
literalmente ("como estamos contra a meta contratual oficial?" é diferente
de "o que vem" ou "o que priorizar"). Solução adotada (ver Parte C, linha
KPI): **dobrar o conteúdo integral da tela KPI para dentro da Tela 01**,
como uma seção expansível "01.5 — OLA & Metas (detalhe)", não apenas 1
card resumido — isso preserva 100% do requisito sem inventar uma 7ª tela
e sem violar a regra de preservação da Seção 3 do pedido original.

**Não removidos, apenas realocados**: todos os 6 endpoints atuais
continuam necessários; nenhuma tabela `ml.*`/`dw.*` é descontinuada;
nenhuma métrica documentada é substituída por número aproximado.

---

## Parte B — Auditoria (P0 / P1 / P2)

Legenda de prioridade: **P0** = erro de dado/target/semântica/modelo que
pode levar a decisão errada ou já contradiz um requisito explícito. **P1**
= risco de decisão errada, mas não um erro ativo hoje. **P2** = UX/clareza.

| # | Tela atual | Elemento | Valor/rótulo hoje | Fonte esperada | Fonte encontrada (real) | Status | Correção proposta | Prior. |
|---|---|---|---|---|---|---|---|---|
| 1 | Clusters | Nomes/descrições A–D | `ml.dim_cluster` já reflete `ml.fct_perfil_cluster` (migrations 029/030 já corrigiram B="Gargalo Crônico Lento" 198h, D="Alto Risco Crítico" 98%) | Métricas reais do cluster | **Já corrigido no banco** — mas `docs/prds/etapa5-api.md` §4.5, `CLAUDE.md` §4 e o docstring de `clusters.py` ainda narram os nomes antigos ("Recorrentes rápidos"/"Sem violações") como bug aberto | Doc desatualizada, dado correto | Atualizar os 3 arquivos de doc/comentário para remover a narrativa de bug já resolvido; manter só o histórico ("corrigido em 029/030") | P2 (rebaixado — **não é mais P0 de dado**) |
| 2 | Clusters + Alertas | `taxa_sla_violado_pct` (coluna crua) | Calculada de `excedeu_tempo_esperado` (94–98%), não de `kpi_status_int` (0,57% do total / ≈0,95% dos casos com status conhecido) | `kpi_status_int` | API já renomeia para `taxa_excedeu_tempo_esperado_pct` e o front nunca usa a palavra "SLA" nesta tela — **mas** `alertas.py`, regra `cluster_alta_violacao`, ainda lê a coluna crua `taxa_sla_violado_pct` internamente | Correto para o usuário final; ambíguo internamente | Renomear a coluna na migration (ou criar view) para eliminar a ambiguidade em qualquer camada, não só no payload | P1 |
| 3 | Painel | Card "Previsão D+1" — legenda de metodologia | Sempre exibe "proporção histórica (não é modelo por corte)" quando `metodologia` existe | Deveria refletir o `metodologia` real vindo da API (Prophet treinado ≠ split por prioridade) | `PainelScreen.tsx:62-64` renderiza uma string fixa, **desacoplada do campo real** — quando a previsão é do Prophet total (modelo treinado), a legenda ainda pode implicar que é regra | Mistura regra com ML no rótulo | Renderizar `data.previsao_d1.metodologia` de verdade, ou badge condicional `MODELO·PROPHET` vs `REGRA·PROPORÇÃO HISTÓRICA` | **P0** |
| 4 | Painel/Forecast | Intervalo de confiança do forecast total | Nenhum — só ponto (`yhat`) | `ml.fct_previsao_diaria_total.yhat_lower/yhat_upper` já existem na tabela | API (`PrevisaoPonto`/`SeriePonto`/`PrevisaoMedia`) **não expõe** os campos — contrato incompleto | Gap de contrato de API | Adicionar `yhat_lower`/`yhat_upper` ao contrato de `/api/painel` e `/api/detalhe`; tela 02 exibe fan chart | **P0** (viola "nunca exibir previsão pontual como se fosse exata") |
| 5 | — (não existe hoje) | Comparação Prophet vs. melhor baseline | Não exibida em nenhuma tela | `data/ml/prophet/metricas_avaliacao_final.csv` (local, MAE 35,73 vs 31,24) | Nenhuma tabela `ml.*` persiste a comparação; nenhum endpoint expõe | Gap de persistência + API | Nova tabela `ml.fct_avaliacao_modelo` (ou similar) alimentada por `forecast_incidentes_revisado.py`; novo campo/endpoint consumido pela Tela 02 | **P0** (critério de aceite explícito do pedido original) |
| 6 | Painel | "Pressão por equipe" — método usado | Não mostra se é Prophet individual/semanal/split | `ml.fct_pressao_equipe.metodo_origem` já existe | API já devolve `metodo_origem` (`PressaoEquipe.metodo_origem`); `computeTeamPressure` never lê o campo | Dado disponível, ignorado no front | Expor `metodo_origem` como badge por linha na tela 02.B | P1 |
| 7 | — (não existe hoje) | `base_value` do SHAP + ordem de calibração | Não existe; e a hipótese inicial desta auditoria (`base_value+Σshap == logit(score_calibrado)`) estava conceitualmente errada | Pré-requisito do waterfall pedido para a Tela 03, com a matemática certa | `ml.fct_shap_incidente` **não tem coluna `base_value`**; e o pipeline real é `XGBoost (saída bruta) → SHAP explica a saída bruta → calibrador isotônico → score_calibrado` — SHAP nunca explica a probabilidade já calibrada | Gap de schema **+ risco de validação matemática incorreta se implementado como planejado originalmente** | (1) Confirmar no código do notebook exatamente o que o `TreeExplainer` explica hoje (margem bruta/log-odds pré-calibração, ou já alguma probabilidade — **verificar, não assumir**); (2) Adicionar `base_value` referente a essa MESMA saída bruta; (3) Validar `base_value + Σshap_value == saída_bruta_do_xgboost` (nunca `logit(score_calibrado)`); (4) Tratar o calibrador isotônico como etapa **separada e posterior** no waterfall — a decomposição SHAP explica a saída bruta, a calibração aparece como um passo visual distinto depois, não embutida nas contribuições | **P0** (pré-requisito de schema **e de metodologia** para a Tela 03 — sem os dois, o waterfall não pode ser construído honestamente) |
| 8 | — (não existe hoje) | Métricas de qualidade do XGBoost (AUC, MCC, Brier, prevalência, threshold) | Não exibidas em nenhuma tela hoje (`/api/fatores` só tem importância + SHAP + heatmap) | `ml.fct_model_metrics`/parquet local já têm os números (AUC 0,7965 teste, MCC 0,076, Brier 0,0457, meta 0,85 não atingida) | Gap de contrato de API — dado existe, endpoint não expõe | Novo bloco no contrato de `/api/fatores` (`qualidade_modelo`) | **P0** (a Tela 03 pedida exige isso; sem o campo a tela não pode existir como especificada) |
| 9 | — (não existe hoje) | Diagnóstico de qualidade do K-Means (Silhouette/DB/PCA por k) | Não exibido hoje | `data/ml/kmeans/diagnostico_k_2_a_8.csv` (local) | Nenhuma tabela `ml.*` persiste o diagnóstico comparativo; `/api/clusters` não expõe | Gap de persistência + API | `ml.fct_avaliacao_modelo` (dimensao='k', tabela genérica — ver achado #26/Parte E) + campo novo em `/api/clusters` | P1 |
| 10 | Detalhe | "% do limite mensal" | `null` + `is_placeholder_limite=true`, UI mostra "sem fonte" | Nenhuma (não existe indicador oficial mensal) | **Já correto** — honestidade preservada | OK | Manter como está na nova Tela 02 | — (nenhuma) |
| 11 | KPI | Texto fixo "150/125/100/75/50/0%" | String estática na JSX | Deveria derivar de `faixas` reais retornadas pela API | Hardcoded, pode divergir silenciosamente se `dw.ref_meta_sla_anual` mudar | Drift risk | Computar a partir do array `faixas` real, não hardcode | P2 |
| 12 | Painel | "Volume base 2025" = 41.441 | `VOLUME_HISTORICO_2025` hardcoded em `dashboardData.ts:42`, usado também no Detalhe (share→contagem) | `dw.fct_incidentes` agregado ao vivo | Hardcoded — correto hoje, mas quebra silenciosamente se o ano de referência mudar | Drift risk | Expor via API (`/api/painel` ganha `volume_total_ano_referencia`); remover constante do front | P1 |
| 13 | Painel | Frase "volume mensal estável entre 2.343 e 4.053" | String estática com 2 números literais na JSX | Derivado da EDA (`docs/eda-consolidada.md` achado 1) | Hardcoded, é um detalhe de EDA anual, não um KPI diário | Fora de lugar numa tela executiva | Remover da Tela 01 (baixa densidade); mover para a metodologia da Tela 02 se necessário | P2 |
| 14 | — (existe como CSV local) | Métricas de backtest por equipe (Prophet) | `data/ml/forecast_equipe/metricas_backtest_equipe.csv` já existe (56 linhas, 8 equipes × 7 modelos, gravado em 2026-08-23) | Deveria estar em `ml.*` + API para virar visual da Tela 02 | Gap parcialmente fechado — artefato local existe, mas não subiu para banco/API | Gap de persistência remanescente | `ml.fct_avaliacao_modelo` (dimensao='equipe', tabela genérica — ver achado #26/Parte E) + step de persistência SQL em `forecast_equipe.py` + campo/endpoint novo | P1 (era P0 antes desta sessão; hoje é "falta subir para o banco", não "falta calcular") |
| 15 | Header (global) | "dw · ml · 2025-12-31" | String fixa | Deveria refletir `data_execucao`/`origem` reais por modelo (podem divergir entre Prophet/K-Means/XGBoost) | Hardcoded — hoje coincide, mas é uma bomba-relógio | Drift risk | Expor `data_execucao` por bloco (cada endpoint já retorna isso para clusters) em vez de 1 string global | P1 |
| 16 | Global | Dependência `recharts` no `package.json` | Listada, **não usada em nenhum componente** (todo gráfico é SVG artesanal) | — | Inconsistência arquitetural | Confunde quem for implementar a Fase 4 (nova arquitetura visual) | Decidir explicitamente na Fase 4: adotar recharts de verdade ou remover a dependência morta | P2 |
| 17 | App.tsx | `MOSTRAR_ORIGEM=true` hardcoded, sem toggle na UI | Componente `SourceTag` suporta esconder, nunca é usado | — | Na verdade correto (usuário pediu "origem sempre visível") — achado é código morto, não falta de feature | Remover o dead prop do componente, não adicionar toggle | P2 |
| 18 | Alertas | `REGRA_ORIGEM_LABEL` — fallback para string crua | Se `regra_origem` não mapeado, mostra o id interno cru (pode conter "violacao") | Rótulo humano sempre | Risco baixo, mas existe (`?? a.regra_origem` fallback) | Vazamento potencial de terminologia interna | Garantir 1:1 completo no dicionário, ou mover o rótulo pronto pro backend | P2 |
| 19 | — (não existe hoje) | AUC-ROC vs. meta 0,85 explícito ao usuário | Não mostrado em nenhuma tela | `docs/metricas-validacao.md` já documenta que a meta não foi atingida em nenhuma partição | Gap de exposição (dado existe, tela não mostra) | Ligado ao achado #8 — mesma correção | P1 |
| 20 | Migration `006_dim_prioridade.sql` | Comentário do cabeçalho | "P1=4h, P2=8h, P3=24h, P4=72h" | Valor real carregado por `etl/transform.py::SLA_THRESHOLD_HORAS` | P1=4/P2=4/P3=12/P4=24/P5=96h — o **comentário** está desatualizado, a **lógica** está correta | Doc-in-code drift | Atualizar o comentário do cabeçalho da migration (não mexer na lógica) | P2 |
| 21 | PLAN.md | "Critérios finais de aceite" (11 itens) | Todos `[ ]` não marcados, apesar da prosa dizer que Fases 1–15 estão concluídas | Deveria refletir status real | Inconsistência de rastreabilidade — não é bug de dado, é falta de fechamento formal | Governança pendente | Fazer 1 passada marcando o que está realmente atendido (a maioria já está, por esta auditoria) | P1 |
| 22 | — (não existe hoje) | "0 mudanças de regime" (Prophet total) | Não exibido em nenhuma tela | Já investigado e documentado (`docs/guia-modelo-prophet-forecast.md`) | Achado real, mas de baixo valor de insight isolado | Não inventar insight de uma ausência | Mostrar só como item secundário/expansível na Tela 02, nunca como destaque | P2 |
| 23 | Fatores | Nome do indicador de risco XGBoost | "score_calibrado · risco de exceder o tempo esperado da prioridade" | Não deve ser chamado de "violação de OLA" | **Já está correto** — nunca usa "OLA"/"SLA" nesta tela | OK | Manter a redação exata na nova Tela 03 | — (nenhuma) |
| 24 | — (não existe hoje) | Confusion matrix / calibration curve do XGBoost | Não exibidos | `docs/guia-modelo-risco-xgboost.md` já tem os números (TP=3165,FP=164,FN=0,TN=1; calibração isotônica por prioridade) | Gap de exposição — ligado ao achado #8 | Mesma correção do #8: bloco `qualidade_modelo` cobre isso | P1 |
| 25 | KPI | Nome do campo `probabilidade_atingir_meta_pct` | Sugere probabilidade estatística | Método real é `metodologia_probabilidade="projecao_linear"` — determinístico, nunca probabilístico | Nome do campo é **semanticamente incorreto** frente ao método que de fato calcula o valor — mesma classe de erro que "violação de OLA" para o XGBoost, só que ainda não corrigida | Nomenclatura confunde regra com estimativa probabilística | Renomear para `projecao_atingimento_meta_pct` (API + frontend); manter `probabilidade_atingir_meta_pct` como alias por 1 release se for preciso compatibilidade retroativa, nunca de forma permanente | P1 |
| 26 | — (decisão de arquitetura desta auditoria) | Persistência de métricas de avaliação (achados #5, #9, #14) | Plano original desta auditoria propunha 3 tabelas novas (`ml.fct_avaliacao_modelo`, `ml.fct_avaliacao_equipe`, `ml.fct_diagnostico_kmeans`) | Os 3 casos de uso compartilham a mesma forma lógica: execução de modelo × métrica × valor, opcionalmente fatiada por 1 dimensão | 3 migrations quase idênticas geram dívida técnica evitável | Sprawl de schema | Consolidar em **1 tabela genérica** `ml.fct_avaliacao_modelo` no formato longo (ver Parte E, avaliação explícita das 2 alternativas) | P1 (decisão de governança, resolvida nesta revisão) |

---

## Parte C — Matriz de Rastreabilidade

Base: `PLAN.md` §3 ("Matriz desafio × solução") e §4 ("Matriz obrigatória
das 6 telas") — únicos requisitos oficiais encontrados no projeto (nenhum
requisito foi inventado nesta auditoria).

| Requisito original | Fonte de dado | Modelo / Regra | Tabela | Tela atual | Tela nova | Mantido? |
|---|---|---|---|---|---|---|
| O que vai acontecer (volume total D+1..D+7) | `ml.ml_forecast_dataset` | Prophet total (`prophet_regime`) | `ml.fct_previsao_diaria_total` | Painel | **02 · Forecast & Capacidade** (Bloco A) | ✅ Sim |
| Onde vai estar concentrado (prioridade/categoria/produto) | `dw.fct_incidentes` | Proporção histórica (**regra**, não modelo treinado por corte) | `ml.fct_previsao_prioridade`/`_categoria`/`_produto` | Detalhe | **02 · Forecast & Capacidade** (bloco novo "distribuição") | ✅ Sim |
| Qual equipe exige atenção / capacidade por equipe | `ml.ml_base_features` | Prophet híbrido A/B/C | `ml.fct_previsao_grupo` + `ml.fct_pressao_equipe` | Painel (pressão) | **02 · Forecast & Capacidade** (Bloco B) | ✅ Sim |
| Como estamos contra a meta contratual oficial de SLA | `dw.fct_incidentes.kpi_status_int` + `dw.ref_meta_sla_anual` | Regra determinística (projeção linear, nunca probabilística) | `dw.ref_meta_sla_anual` | KPI | **01 · Visão Estratégica** (seção expansível "01.5 OLA & Metas") — ver justificativa abaixo | ✅ Sim, realocado |
| Por que existe risco (importância global + individual) | `ml.ml_sla_classification_dataset` | XGBoost + SHAP | `ml.fct_importancia_conceito`/`_feature` + `ml.fct_shap_incidente` | Fatores | **03 · Risco & Explicabilidade** | ✅ Sim |
| Quais padrões estruturais existem | `ml.ml_cluster_dataset` | K-Means (k=4) | `ml.dim_cluster` + `ml.fct_perfil_cluster` | Clusters | **04 · Perfis Operacionais** | ✅ Sim |
| Sazonalidade / recorrência operacional | `dw.fct_incidentes` | Regra (janela móvel 30d vs. 30d anteriores) | `dw.fct_recorrencia_operacional` | Detalhe | **02 · Forecast & Capacidade** (bloco recorrência) | ✅ Sim |
| O que fazer (ação prescritiva) | Combinação de todos os `ml.fct_*` acima | Regras/templates (rule engine, não IA) | n/a (lógica em `alertas.py`) | Alertas | **05 · Ações & Governança** | ✅ Sim |
| Validação/backtest/baselines dos modelos | parquets locais + `docs/metricas-validacao.md` | n/a (metodologia de validação) | **Gap**: sem tabela `ml.*` dedicada hoje | Não existe tela para isso hoje | **05 · Ações & Governança** ("Saúde dos modelos") + blocos de metodologia em 02/03/04 | ⚠️ Parcial — requer nova tabela (achados #5, #9, #14) |
| Explicar o projeto/arquitetura para quem avalia | `PLAN.md`, `CLAUDE.md` | n/a | n/a | Não existe tela para isso hoje | **00 · Sobre o Projeto** (nova) | ✅ Novo, não substitui nada |

**Justificativa da realocação KPI → Tela 01**: as 5 perguntas do novo
storytelling (Prever/Priorizar/Explicar/Segmentar/Agir) não cobrem
literalmente "estamos cumprindo a meta contratual oficial?" — essa
pergunta é sobre **conformidade**, não sobre previsão/risco/segmentação.
Criar uma 7ª tela violaria o pedido explícito de 6 telas; **remover** o
conteúdo violaria a regra de preservação (Seção 3). A solução adotada é
manter o resumo de 4 KPIs em 01.1 (como já pedido) e adicionar uma seção
**expansível** (não substitui, apenas normalmente recolhida) com a tabela
completa de faixas/probabilidade por prioridade × indicador — mantém a
densidade baixa da Tela 01 no estado padrão e preserva 100% do conteúdo
para quem expandir.

---

## Parte D — Blueprint das Seis Telas

Ordem obrigatória dentro de cada tela (conforme pedido): Resumo → Visual
principal → Diagnóstico → Detalhe → Insight/Ação → Metodologia. Densidade:
00 editorial, 01 baixa, 02 média/alta, 03 alta-organizada, 04 média/alta,
05 baixa/média.

### TELA 00 — SOBRE O PROJETO

**Objetivo**: apresentar o sistema antes de qualquer número. **Pergunta**:
qual problema este projeto resolve e como os componentes trabalham juntos?
**Fontes**: nenhuma fonte de dado ao vivo — conteúdo estático/editorial
derivado de `PLAN.md`/`CLAUDE.md`. **Sem filtros.**

| Visual | Pergunta respondida | Tipo | Fonte | Interação |
|---|---|---|---|---|
| Hero + framework Prever→Priorizar→Explicar→Segmentar→Agir | Do que se trata o projeto? | Bloco editorial | Estático | — |
| Diagrama "Framework AIOps" (Dados→Entender→Prever/Priorizar/Segmentar→Explicar→Agir) | Como os modelos se complementam? | Diagrama de fluxo | Estático | — |
| 5 cards "as cinco perguntas" | Que pergunta cada componente responde? | 5 cards | Estático | CTA por card → tela correspondente |
| Pipeline de dados (Fonte→Bronze→Silver→DW→ML→Dashboard→Decisão) | De onde vêm os números? | Diagrama vertical | Estático (nomes reais de schema) | — |
| Matriz "Requisitos × Solução" | O desafio oficial foi atendido? | Tabela/checklist | `PLAN.md` §3 (real) | — |
| 3 cards "Dados × Modelos × Regras" | O que é fato, o que é estimativa, o que é decisão? | 3 cards | Estático | — |
| Bloco "Princípios de governança" | Quais são as limitações admitidas? | Cards textuais | Estático (extraído de `docs/metricas-validacao.md`) | — |
| Navegação (6 telas) + CTA | Por onde eu começo? | Menu/CTA | — | Link para tela 01 |

**Insight final**: nenhum — esta tela é orientação, não decisão.

---

### TELA 01 — VISÃO ESTRATÉGICA

**Objetivo**: cockpit executivo, compreensível em 20–30s. **Pergunta**: o
que está acontecendo, o que tende a acontecer, onde agir? **Fontes**:
`/api/painel` (resumo), `/api/kpi` (seção 01.5), `/api/fatores`
(resumo de risco), `/api/clusters` (resumo de perfil), `/api/alertas`
(top prioridades). **Sem filtros** (drill-down via CTA, não via controle
nesta tela).

| Visual | Pergunta respondida | Tipo | Métrica | Fonte | Interação | Insight esperado |
|---|---|---|---|---|---|---|
| 4 KPI cards (volume atual, situação OLA, forecast D+1, pressão D+7) | Estado da operação agora | KPI cards + badge de origem | `total_chamados`, `kpi_status_int` agregado, `yhat` D+1, `pressao_relativa_pct` média | `/api/painel`, `/api/kpi` | — | Situação geral em 1 olhar |
| 3 cards "lentes" (Prophet/XGBoost/K-Means) | Quanto vem? Quem priorizar? Que perfil pesa mais? | 3 cards grandes | `yhat`+intervalo, top risco+driver, cluster prioritário+participação | `/api/painel`, `/api/fatores`, `/api/clusters` | CTA → tela 02/03/04 | Direciona para a tela certa |
| Lista "Prioridades do dia" (3–5 itens) | O que fazer primeiro? | Lista priorizada (sem gráfico) | severidade+evidência+impacto+ação | `/api/alertas` (top N) | — | Seção executiva principal |
| Mini tendência (sparkline, opcional) | Como estamos indo nos últimos dias? | Sparkline | `total_chamados` recente + `yhat` D+1 | `/api/painel.serie` (últimos ~14 pontos) | — | Contexto rápido, não duplica a Tela 02 |
| **01.5 — OLA & Metas (progressive disclosure)** | Estamos dentro da meta contratual oficial? | Estado padrão: 1 resumo por prioridade (status + % projetado). Só ao expandir: tabela completa (4 linhas P2/P3 × ola_quebrado/volume_tratado) + 6 faixas por linha | `status`, `projecao_atingimento_meta_pct` (renome do achado #25) no resumo; `contagem_acumulada_ano`, `faixas` no detalhe expandido | `/api/kpi` (conteúdo integral da tela KPI atual) | **Recolhido por padrão**; expandir revela o detalhe completo, sem paginação nem tela separada | Preserva 100% do requisito original sem inflar a densidade padrão da tela |

**Insight final**: quais 3–5 prioridades merecem atenção imediata, com
evidência e origem.

---

### TELA 02 — FORECAST & CAPACIDADE

**Objetivo**: quanto trabalho vem e onde preparar capacidade — com
densidade reduzida no topo e o diagnóstico técnico rebaixado para uma
seção secundária. **Pergunta central**: quanto vem, quando, e onde haverá
pressão? Duas camadas de dado permanecem conceitualmente distintas em
todo visual (**Prophet total** vs. **Prophet por equipe, arquitetura
híbrida A/B/C**) — a mudança pedida é de **ordem/prioridade visual**, não
de fusão dos dois modelos. Estrutura em 3 blocos, nessa ordem:
`Decisão → Diagnóstico operacional → Qualidade/metodologia`. **Fontes**:
`/api/painel`, `/api/detalhe`, mais os campos novos dos achados #4/#5/#6/
#14 (intervalo de confiança, baseline, metodo_origem, backtest por
equipe). **Filtros**: prioridade (Detalhe), horizonte D+1..D+7, categoria
vs. produto (agrupamento).

**02.1 — Decisão (topo da tela, sempre visível)**

| Visual | Pergunta | Tipo | Métrica | Dimensão | Fonte | Interação | Insight |
|---|---|---|---|---|---|---|---|
| Forecast principal D+1..D+7 [Prophet total] | Quanto vem e com que incerteza? | Line + fan chart | `yhat`,`yhat_lower`,`yhat_upper` | Data | `/api/painel` (ampliado, achado #4) | Tooltip por dia | Volume esperado + incerteza real |
| Pressão relativa por equipe [Prophet equipe] | Quem está acima/abaixo da própria média? | Diverging bar chart | `pressao_relativa_pct` | Equipe | `/api/painel.pressao_equipes` | — | Nunca comparar em volume absoluto |
| Principais categorias/recorrências [Detalhe] | Onde o volume vai se concentrar e o que está crescendo? | Bar chart + cards | `yhat_categoria`, `delta_pct`, `cobertura_dias_atual_pct` | Categoria | `/api/detalhe` (top entidades + recorrência) | — | Sinal de atenção não-óbvio no volume total |

**02.2 — Diagnóstico operacional (meio da tela)**

| Visual | Pergunta | Tipo | Métrica | Dimensão | Fonte | Interação | Insight |
|---|---|---|---|---|---|---|---|
| Histórico diário [Prophet total] | Existe tendência/padrão? | Line chart | `total_chamados` | Data (série longa) | `ml.ml_forecast_dataset` | Zoom/range | Contexto histórico |
| Diagrama da arquitetura híbrida [Prophet equipe] | Por que 3 métodos diferentes? | Diagrama de fluxo | — | — | Estático (`docs/forecast-por-equipe.md`) | — | Educa antes de mostrar número |
| Forecast por equipe D+1 [Prophet equipe] | Quanto cada equipe deve esperar? | Bar chart horizontal | `yhat` | Equipe | `/api/painel.pressao_equipes` (ampliado com `metodo_origem`, achado #6) | Tooltip: método+desvio% | Direciona reforço de capacidade |
| Volume médio por equipe + limiares [Prophet equipe] | Por que cada equipe caiu no método que caiu? | Bar chart horizontal | Média diária | Equipe | `ml.ml_base_features` agregado | Linhas em 1/dia e 5/dia | Critério visual explícito |
| Método usado por equipe (tabela/dot plot) [Prophet equipe] | Qual equipe usa qual técnica de fato? | Tabela compacta | Volume médio + método | Equipe | `ml.fct_previsao_grupo.metodo` real (não inferido do grupo A/B/C nominal) | — | Team12/17/02 usam individual mesmo estando na faixa B |
| Curvas por método (3 equipes exemplo) [Prophet equipe] | Como a forma da previsão muda por método? | Line chart múltiplo | `yhat`+intervalo | Horizonte | `ml.fct_previsao_grupo` | Seleção de equipe | Split proporcional não tem forma própria |

**02.3 — Qualidade & metodologia (seção secundária, recolhida por padrão)**

| Visual | Pergunta | Tipo | Métrica | Dimensão | Fonte | Interação | Insight |
|---|---|---|---|---|---|---|---|
| Performance do modelo (tabela) [Prophet total] | O Prophet bate um baseline simples? | Tabela/scorecard | MAE/WAPE/MASE Prophet vs. melhor baseline | Modelo | `ml.fct_avaliacao_modelo` (achado #5, tabela genérica — ver Parte E/F) | Destaque visual do vencedor | Honestidade: baseline vence hoje (35,73 vs. 31,24) |
| Erro por horizonte [Prophet total] | Quanto a previsão piora de D+1 a D+7? | Line chart | MAE, cobertura% | Horizonte (D+1..D+7) | `/api/painel`/tabela genérica | — | Confiar menos em D+7 |
| Sazonalidade semanal [Prophet total] | Quais dias concentram volume? | Bar chart | Volume médio | Dia da semana | `ml.ml_forecast_dataset` agregado | — | Pico quinta-feira (EDA achado 6) |
| Mudança de regime [Prophet total] | Houve quebra de patamar? | Texto + mini-linha | Razão mediana móvel 28d | Data | Investigação já documentada (`guia-modelo-prophet-forecast.md`) | Expandir | Nunca virar destaque de "0 mudanças" |
| Distribuição dos métodos [Prophet equipe] | Quantas equipes em cada método? | 3 KPI cards | Contagem | Método | `ml.fct_previsao_grupo.metodo` (7 individual / 1 semanal / 8 split, confirmado ao vivo) | — | **Metade das equipes (8/16) usa split proporcional; a outra metade (8/16) usa modelagem temporal própria** (7 individual + 1 semanal) — não é maioria em nenhuma direção, é uma divisão exata ao meio |
| Métricas de backtest por equipe [Prophet equipe] | O modelo da equipe é bom? | Bar chart (MAE/WAPE por equipe, Grupo A/B) | MAE, WAPE%, veredito | Equipe | `ml.fct_avaliacao_modelo` (dimensao='equipe', achado #14 — CSV já existe, falta subir) | — | Honestidade por equipe, não só agregada |

**Insight final**: qual volume esperamos e onde reforçar capacidade —
com o método/confiabilidade de cada número explícito.

---

### TELA 03 — RISCO & EXPLICABILIDADE

**Objetivo**: priorizar antes de o problema estourar, com explicação
auditável. **Pergunta**: quais incidentes merecem atenção e por quê?
**Ordem visual pedida explicitamente**: ranking operacional primeiro,
classificação binária nunca em destaque — a tela abre decidindo quem
priorizar, não classificando "risco sim/não". **Pré-requisito de schema**
(achado #7 revisado + #8): `base_value` referente à saída bruta do
XGBoost (não à saída calibrada) e bloco `qualidade_modelo` no contrato de
`/api/fatores` — sem isso, os visuais 03.3/03.5 não podem ser construídos
com dado real. **Filtros**: seleção de incidente (para SHAP local),
filtro por prioridade (para AUC por prioridade).

**03.1 — Decisão (topo, ranking em vez de binário)**

| Visual | Pergunta | Tipo | Métrica | Fonte | Interação | Insight |
|---|---|---|---|---|---|---|
| 1. Ranking Top N | Quem priorizar primeiro? | Tabela operacional | `score_calibrado`, top fator | `/api/fatores` (novo: ranking por incidente) | Seleção → alimenta o waterfall (03.3) | Lista acionável, não "risco sim/não" — visual de abertura da tela |
| 2. Distribuição das probabilidades | O modelo separa os casos ou todos ficam parecidos? | Histogram | `score_calibrado` | `ml.fct_risco_incidente` (novo campo agregado) | Linha de threshold | Threshold atual classifica quase tudo como risco |

**03.2 — Explicação (por que o ranking ficou assim)**

| Visual | Pergunta | Tipo | Métrica | Fonte | Interação | Insight |
|---|---|---|---|---|---|---|
| 3. SHAP do incidente selecionado (waterfall) | Por que este incidente específico tem esse score? | Waterfall em 2 passos visuais: (a) `base_value`+`shap_value` → saída bruta do XGBoost; (b) saída bruta → `score_calibrado` via calibrador isotônico, mostrado como um passo distinto, não somado às contribuições | `ml.fct_shap_incidente` (+ `base_value` da saída bruta, achado #7 revisado) | Seleção de incidente (herdada do ranking 03.1) | Explicação individual auditável, com a calibração explicitamente separada da decomposição SHAP |
| 4. Importância global (por conceito) | O que normalmente pesa mais no risco, em todos os incidentes? | Bar chart horizontal | `importance_pct` | `/api/fatores.importancia_conceitos` | — | Prioridade do chamado domina (32%) |

**03.3 — Qualidade do modelo (seção secundária, honestidade sem esconder)**

| Visual | Pergunta | Tipo | Métrica | Fonte | Interação | Insight |
|---|---|---|---|---|---|---|
| 5a. Calibration curve | Quando o modelo diz 80%, isso é 80% na prática? | Reliability diagram | `score_calibrado` vs. frequência real | Novo bloco `qualidade_modelo` (achado #8) | — | Calibração isotônica por prioridade já é boa |
| 5b. Matriz de confusão | Onde o modelo erra? | Heatmap 2×2 | TP/FP/FN/TN no threshold atual | Novo bloco `qualidade_modelo` | — | Recall≈100% só porque threshold é baixo |
| 5c. Qualidade por prioridade | A performance agregada esconde diferença entre prioridades? | Bar chart | AUC geral vs. AUC por prioridade | Novo bloco `qualidade_modelo` | — | Paradoxo de Simpson (AUC agregado 0,80, P2 isolado 0,66) |
| 5d. Métricas-chave (cards) | O modelo é bom de forma honesta? | Cards compactos | AUC, MCC, Brier, prevalência, threshold | Novo bloco `qualidade_modelo` | — | Meta 0,85 não atingida; MCC=0,076 é o número mais honesto |
| 5e. Heatmap categoria × dia | Onde e quando o volume de risco se concentra? | Heatmap | Volume médio | `/api/fatores.heatmap_categoria_dia` (já existe) | — | Padrão espaço-tempo |

**Insight final**: quem priorizar e quais fatores sustentam essa
priorização — com a qualidade do modelo explícita, sem esconder o MCC
baixo atrás de um F1 alto.

---

### TELA 04 — PERFIS OPERACIONAIS (K-MEANS)

**Objetivo**: mostrar onde estão os perfis estruturais e qual merece
intervenção **segundo uma regra explícita**, nunca pela maior taxa
isolada. **Pergunta**: que tipos de comportamento existem e onde
concentram os problemas? **Fonte de verdade**: `ml.dim_cluster` +
`ml.fct_perfil_cluster` — confirmados ao vivo nesta auditoria como já
consistentes entre si (achado #1). **Filtros**: nenhum obrigatório;
seleção de cluster para destacar nos gráficos de composição.

**Regra inicial de priorização (determinística, documentada, rotulada
como REGRA — nunca como ML — e explicitamente provisória)**: escolher o
cluster "prioritário" só pela maior `taxa_excedeu_tempo_esperado_pct`
(hoje, cluster D, 98,0%) esconde que D é o **menor** cluster em volume
(10,5%) — o impacto agregado na operação pode ser bem menor do que
parece isoladamente. Como primeira aproximação, este plano propõe um
indicador chamado **"Impacto por volume e excedência"**:
`impacto_volume_excedencia_pct = pct_volume × taxa_excedeu_tempo_esperado_pct`.
Aplicando aos números reais confirmados nesta auditoria
(`ml.fct_perfil_cluster`, execução 2026-08-22): **B = 31,3% (maior) > A =
30,4% > C = 23,2% > D = 10,3% (menor)** — a ordem inverte quase por
completo frente a "olhar só a taxa". Cluster B também tem a maior
duração média (198h), o que é mais um indício a favor de B, não uma
prova.

**Isto não é a definição definitiva de "impacto operacional" nem uma
regra permanente** — é um ponto de partida documentado com apenas 2
fatores, para substituir "olhar só a maior taxa" por algo levemente mais
informado. Uma versão futura deve incorporar, com validação do time de
operação (não decidida pelo dashboard sozinho): duração média, severidade/
prioridade dos incidentes do cluster, custo operacional estimado, ou
outros pesos que a operação considere relevantes. Até essa validação
acontecer, o ranking resultante **não deve ser tratado como verdade
causal** ("cluster B causa mais problema") nem como decisão automática de
prioridade — é um insumo para discussão, exibido como REGRA explícita,
nunca como saída de um modelo.

| Visual | Pergunta | Tipo | Métrica | Dimensão | Fonte | Interação | Insight |
|---|---|---|---|---|---|---|---|
| Bubble chart principal | Onde cada cluster fica em duração × excedência × volume? | Bubble scatter | `duracao_media_horas`, `taxa_excedeu_tempo_esperado_pct`, `pct_volume` | Cluster | `/api/clusters` (já existe, sem mudança) | Tooltip | Visão executiva imediata |
| **Impacto por volume e excedência (novo, regra inicial)** | Qual cluster merece atenção primeiro, considerando volume **e** excedência juntos — como ponto de partida, não veredito final? | Bar chart horizontal (score composto, ordenado) | `impacto_volume_excedencia_pct = pct_volume × taxa_excedeu_tempo_esperado_pct` (REGRA documentada e provisória, não ML) | Cluster | `/api/clusters` (cálculo client-side ou campo novo `impacto_volume_excedencia_pct`) | Nota fixa no visual: "regra inicial de 2 fatores, sujeita a revisão com a operação" | B > A > C > D — inverte a leitura ingênua "maior taxa = prioridade", mas não é causal nem definitivo |
| Cards dos 4 clusters | Qual é o perfil de cada cluster? | 4 cards | Nome, volume, duração, taxa, tags | Cluster | `/api/clusters` | — | "Caracterizado por", nunca "causado por" |
| Composição por prioridade | Cada cluster é dominado por qual prioridade? | 100% stacked bar | % por prioridade | Cluster × Prioridade | Novo agregado (`ml.ml_cluster_dataset` já tem `cluster_id`+`prioridade_num`) | — | Mostra o que diferencia estruturalmente |
| Composição por categoria | Cada cluster concentra quais categorias? | Heatmap | % por categoria | Cluster × Categoria | Mesmo dataset | — | Mais legível que várias barras |
| Principais características | O que realmente diferencia o cluster da média geral? | Dot plot | Diferença vs. média geral | Feature × Cluster | Mesmo dataset | — | Base factual para a descrição curta |
| Qualidade da clusterização (painel secundário) | k=4 é ótimo ou uma escolha de compromisso? | 3 mini-gráficos (Silhouette×k, DB×k, PCA variância) | Silhouette, Davies-Bouldin, % variância | k (2–8) | `ml.fct_avaliacao_modelo` (dimensao='k', achado #9 — tabela genérica, ver Parte E/F) | — | k=4 não é ótimo estatístico em nenhuma métrica — decisão de negócio, documentada como tal |
| PCA scatter | Os clusters se separam espacialmente? | Scatter PC1×PC2 | Coordenadas PCA | Cluster | Mesmo diagnóstico | — | Diagnóstico técnico, não prova de separação perfeita (39,95% variância explicada) |

**Insight final**: qual perfil merece atenção primeiro segundo a regra
inicial de "Impacto por volume e excedência" (hoje: cluster B, não D) e
que tratamento estrutural faz sentido — sempre com a ressalva de que essa
regra é um ponto de partida de 2 fatores, não uma verdade causal nem uma
decisão permanente, e nunca ordenando por uma métrica isolada sem
declarar a fórmula usada.

---

### TELA 05 — AÇÕES & GOVERNANÇA

**Objetivo**: fechar o ciclo Prever→Priorizar→Explicar→Segmentar→**Agir**.
**Pergunta**: o que fazer, com qual evidência, com qual confiança?
**Fontes**: `/api/alertas` (já existe), mais um bloco novo de "saúde dos
modelos" consolidando os achados #5/#8/#9/#14 (comparação de baseline,
qualidade XGBoost, diagnóstico K-Means, backtest por equipe). **Poucos
gráficos** — o foco é alerta→evidência→ação→responsável.

| Visual | Pergunta | Tipo | Métrica | Fonte | Interação | Insight |
|---|---|---|---|---|---|---|
| Alertas ativos | O que está fora do esperado agora? | Lista/cards priorizados | severidade+evidência+origem+condição | `/api/alertas.alertas` (já existe) | — | Ordenado por severidade/impacto |
| Recomendações | O que fazer a respeito? | Action cards | ação+owner+prioridade+origem | `/api/alertas.recomendacoes` (já existe) | — | Sempre rotulado como regra, nunca IA |
| Matriz impacto × urgência (opcional) | Quais alertas priorizar primeiro? | 2×2 matrix | Impacto, urgência | Derivado dos alertas | Seleção de quadrante | Só se houver volume suficiente de alertas |
| Saúde dos modelos | Cada modelo está fazendo o que promete? | Tabela de governança | Status (regra objetiva), métrica-chave, limitação | Consolida achados #5/#8/#9/#14 | — | Prophet perde do baseline pontual; XGBoost abaixo da meta; K-Means sem k ótimo — tudo dito sem rodeio |
| Fluxo de rastreabilidade (por alerta) | De onde veio este alerta? | Diagrama compacto | Alerta→Regra→Modelo→Tabela→Dado | Metadado já existente em cada alerta (`regra_origem`) | Interativo (futuro) | Auditabilidade ponta a ponta |
| Limitações (cards textuais) | O que este sistema **não** garante? | Cards | Texto | Consolida achados desta auditoria + `docs/metricas-validacao.md` | — | Nunca escondido em tooltip |

**Insight final**: cada ação recomendada rastreável até o dado e o
requisito original, com a confiança do modelo/regra que a originou
explícita.

---

## Parte E — Plano de Correção (Fases)

**Fase 1 — Verdade dos dados** (sem código de produto): rodar as queries
de confirmação desta auditoria de novo no momento da implementação (dados
podem ter mudado); confirmar se as migrations 029/030 realmente já foram
aplicadas em qualquer ambiente além deste.

**Fase 1.1 — Avaliação explícita: 1 tabela genérica vs. 3 tabelas
específicas** (achado #26, resolvida nesta revisão): antes de criar
schema novo para os 3 artefatos hoje só em parquet/CSV local (comparação
Prophet-vs-baseline, backtest por equipe, diagnóstico k do K-Means):

| Opção | Prós | Contras |
|---|---|---|
| (a) 3 tabelas específicas (`ml.fct_avaliacao_modelo`, `ml.fct_avaliacao_equipe`, `ml.fct_diagnostico_kmeans`) | Schema mais legível por caso de uso; colunas tipadas por métrica | 3 migrations quase idênticas; 3 padrões de escrita a manter; Tela 05 ("Saúde dos modelos") precisa consultar 3 tabelas |
| (b) **1 tabela genérica** `ml.fct_avaliacao_modelo` em formato longo: `avaliacao_sk, modelo (prophet_total\|prophet_equipe\|kmeans\|xgboost), modelo_versao, data_execucao, dimensao (null\|'equipe'\|'k'), chave_dimensao (null\|'Team14'\|'4'), metrica (text), valor (numeric), is_baseline (bool), baseline_nome (text, null)` | 1 migration; 1 lugar único para a Tela 05 consultar "saúde de qualquer modelo"; os 3 casos de uso já compartilham a mesma forma lógica (execução × métrica × valor, opcionalmente fatiada por 1 dimensão) | Leitura precisa pivotar métrica→coluna no lado da API (aceitável — o consumo é sempre via endpoint, nunca SQL direto do frontend) |

**Decisão desta auditoria: opção (b)** — menor dívida técnica futura e
melhor governança (um único ponto de consulta). Esta é a tabela referida
como `ml.fct_avaliacao_modelo` em todo o resto deste documento
(`dimensao='equipe'` cobre o achado #14, `dimensao='k'` cobre o achado
#9, `dimensao=null` cobre o achado #5). Decidir também nesta fase o
formato final da coluna `base_value` (achado #7).

**Fase 2 — Correções de modelo/semântica**: persistir os 3 artefatos que
hoje só existem em parquet/CSV local (comparação de baseline do Prophet
total, backtest por equipe, diagnóstico k=2..8 do K-Means) na tabela
genérica `ml.fct_avaliacao_modelo`; confirmar o que o `TreeExplainer`
realmente explica no notebook do XGBoost, calcular `base_value` sobre a
saída bruta e validar matematicamente contra ela (nunca contra
`score_calibrado`); renomear/esclarecer `taxa_sla_violado_pct` na origem
(não só no payload). Nenhum retreino de modelo é necessário para nenhum
destes itens — são todos persistência/instrumentação do que já foi
calculado.

**Fase 3 — Camada de dados/API**: estender os contratos de `/api/painel`
(intervalo de confiança, `volume_total_ano_referencia`, `metodo_origem`
exposto), `/api/fatores` (bloco `qualidade_modelo`, ranking top-N,
`base_value`), `/api/clusters` (diagnóstico k) e `/api/detalhe`/novo
endpoint para avaliação de modelo/equipe.

**Fase 4 — Nova arquitetura visual**: implementar as 6 telas do blueprint
(Parte D); decidir explicitamente sobre `recharts` (adotar ou remover);
remover hardcodes identificados nos achados #3/#12/#13/#15/#17.

**Fase 5 — Integração**: religar as 6 telas às APIs estendidas; garantir
que nenhuma tela nova regride uma funcionalidade das telas atuais (usar a
Parte C como checklist).

**Fase 6 — QA técnico**: testes de contrato de API (schemas novos),
teste de que `soma(shap_value)+base_value == saída_bruta_do_xgboost` (não
`score_calibrado` — a calibração é validada separadamente, como
monotonicidade do calibrador isotônico), teste de que os 3 métodos de
`ml.fct_previsao_grupo.metodo` continuam consistentes após qualquer nova
execução.

**Fase 7 — QA visual**: revisão de densidade por tela (Tela 01 não pode
crescer além do "baixa densidade" definido, mesmo com a seção 01.5
expansível), revisão de nomenclatura (nunca "violação de OLA" para o
target do XGBoost, nunca "probabilidade" para a projeção linear de meta).

**Fase 8 — Validação contra requisitos**: reexecutar a Parte C
(rastreabilidade) linha a linha contra a implementação final; fechar
formalmente os "Critérios finais de aceite" do `PLAN.md` (achado #21).

---

## Parte F — Plano por Arquivo (alto nível, sem código)

| Arquivo | Mudança | Dependência | Risco | Critério de aceite |
|---|---|---|---|---|
| `db/migrations/0NN_ml_fct_avaliacao_modelo.sql` (novo, **genérico** — achado #26) | 1 tabela em formato longo (`modelo`,`modelo_versao`,`data_execucao`,`dimensao`,`chave_dimensao`,`metrica`,`valor`,`is_baseline`,`baseline_nome`) cobrindo os 3 casos de uso (Prophet-vs-baseline, backtest por equipe, diagnóstico K-Means) | Nenhuma | Baixo (tabela nova, append-only) | 3 scripts diferentes inserem nesta mesma tabela, cada um com seu `modelo`/`dimensao` |
| `db/migrations/0NN_ml_fct_shap_incidente_base_value.sql` (novo) | `ALTER TABLE ml.fct_shap_incidente ADD COLUMN base_value numeric` — referente à **saída bruta** do XGBoost, não à saída calibrada | Confirmar antes o que o `TreeExplainer` explica hoje no notebook (achado #7) | Médio — precisa validação matemática antes de expor | `soma(shap_value)+base_value == saída_bruta_do_xgboost` (nunca `logit(score_calibrado)`) para uma amostra de incidentes |
| `notebooks/forecast_incidentes_revisado.py` | Persistir comparação com baseline em `ml.fct_avaliacao_modelo` (`dimensao=null`) | Migration acima | Baixo (append, mesmo padrão já usado) | Nova tabela populada a cada execução |
| `notebooks/forecast_equipe.py` | Persistir `metricas_backtest_equipe.csv` também em `ml.fct_avaliacao_modelo` (`dimensao='equipe'`) | Migration acima | Baixo — já gera o CSV, só falta o `INSERT` | 8 equipes × N métricas por execução |
| `notebooks/diagnostico_kmeans_k.py` | Persistir também em `ml.fct_avaliacao_modelo` (`dimensao='k'`) | Migration acima | Baixo | 7 linhas (k=2..8) × N métricas por execução |
| `notebooks/model_risk_xgboost_.ipynb` | (1) Confirmar exatamente o que o `TreeExplainer` explica hoje; (2) calcular `base_value` sobre a saída bruta; (3) validar `base_value+Σshap == saída_bruta` (não `score_calibrado`); (4) gravar `base_value` em `ml.fct_shap_incidente` | Migration acima | Médio | Validação de soma bate com a **saída bruta**, calibração documentada como etapa separada |
| `app/api/routers/painel.py` | Adicionar `yhat_lower`/`yhat_upper`, `volume_total_ano_referencia`, expor `metodo_origem` já lido | Nenhuma (dados já existem na tabela) | Baixo | Contrato retrocompatível (campos novos, nada removido) |
| `app/api/routers/fatores.py` | Novo bloco `qualidade_modelo` (AUC/MCC/Brier/threshold/prevalência/confusion matrix/calibração), ranking top-N, `base_value` no `ShapItem` | Migration `base_value` + `ml.fct_avaliacao_modelo` (dimensao=null, XGBoost) | Médio | Bloco novo populado, nada quebra os campos existentes |
| `app/api/routers/clusters.py` | Expor diagnóstico k (`ml.fct_avaliacao_modelo`, dimensao='k') + campo `impacto_volume_excedencia_pct` (regra inicial e provisória volume×taxa, ver Tela 04 — não confundir com uma métrica definitiva de "impacto operacional") | Migration acima | Baixo | Novo campo opcional na resposta, com nota de que é regra sujeita a revisão |
| `app/api/routers/kpi.py` | Renomear `probabilidade_atingir_meta_pct` → `projecao_atingimento_meta_pct` (achado #25) | Nenhuma | Baixo — só rename de campo calculado, nada persistido muda | Frontend consome o novo nome; alias temporário se necessário |
| `app/web/src/lib/api.ts` | Tipos novos para os campos acima | Endpoints atualizados | Baixo | `tsc -b` limpo |
| `app/web/src/data/dashboardData.ts` | Remover `VOLUME_HISTORICO_2025` hardcoded; expor `metodo_origem`; corrigir legenda de metodologia (achado #3); calcular `impacto_volume_excedencia_pct` se não vier pronto da API, sempre com o rótulo "regra inicial" no texto de apoio | API estendida | Médio (é o arquivo mais tocado) | Zero literais numéricos de negócio no arquivo; nenhum texto trata o ranking como causal ou definitivo |
| `app/web/src/components/screens/*` (reescrita para 6 novas telas) | Nova estrutura conforme Parte D | Todos os itens acima | Alto (maior mudança de UI) | Checklist da Parte C, 100% dos requisitos mantidos |
| `app/web/src/App.tsx` | Nova navegação (00–05), remover `MOSTRAR_ORIGEM` morto | Novas telas prontas | Baixo | Navegação funcional entre as 6 telas |
| `app/web/package.json` | Decisão sobre `recharts` (adotar ou remover) | Decisão de Fase 4 | Baixo | Sem dependência não utilizada no bundle final |
| `docs/prds/etapa5-api.md` | Atualizar §4.5 removendo a narrativa do bug de cluster já corrigido; documentar os novos campos de contrato | Nenhuma | Baixo | Doc reflete o banco real |
| `app/api/routers/clusters.py` (docstring) + `app/api/routers/alertas.py` (docstring) | Remover referência ao bug de nomes de cluster já corrigido | Nenhuma | Baixo | Comentário reflete estado atual |
| `CLAUDE.md` §4 | Atualizar achado de divergência de cluster para "corrigido em 029/030"; adicionar os novos gaps fechados | Nenhuma | Baixo | Seção 10/4 reflete estado real |
| `PLAN.md` Anexo A | Novo checkpoint (`ML-6`?) para `base_value`/qualidade do XGBoost exposta; fechar formalmente os "Critérios finais de aceite" | Nenhuma | Baixo | Checklist com itens realmente marcados |
| `db/migrations/006_dim_prioridade.sql` | Corrigir comentário do cabeçalho (não a lógica) | Nenhuma | Nenhum | Comentário bate com `etl/transform.py` |

---

## Parte G — Lacunas Técnicas (não inventar dado para preencher)

- **Métricas de backtest por equipe (Prophet)**: cálculo já existe
  (`metricas_backtest_equipe.csv`, 2026-08-23), mas ainda não está em
  tabela `ml.*` nem em endpoint — é o gap mais "quase resolvido" da lista.
- **Comparação Prophet vs. baseline**: só existe em parquet/CSV local,
  nunca foi para uma tabela `ml.*`. Sem isso, a Tela 02 não pode mostrar
  o critério de aceite "comparação com baseline estiver visível" com dado
  vivo — hoje precisaria citar `docs/metricas-validacao.md` como
  snapshot datado, não como métrica dinâmica.
- **Diagnóstico k=2..8 do K-Means**: mesma situação — só em CSV local.
- **`base_value` do SHAP**: não existe em nenhuma tabela hoje. É um
  pré-requisito de schema **e de metodologia**, não uma correção de bug —
  primeiro é preciso confirmar exatamente o que o `TreeExplainer` explica
  no notebook atual (saída bruta/log-odds pré-calibração, tipicamente —
  mas isso precisa ser lido no código, nunca assumido), calcular
  `base_value` sobre essa mesma saída, e só então validar
  `base_value+Σshap == saída_bruta`. A calibração isotônica é uma etapa
  **separada e posterior**, nunca somada dentro da decomposição SHAP —
  nunca assumir que "base do modelo = X" sem essa prova em 2 etapas.
- **Ausência de CI**: segue como lacuna declarada em `CLAUDE.md`/
  `PLAN.md` — não investigada nesta auditoria (fora do escopo de
  dashboard/dado).
- **Prophet perde do baseline simples em MAE/WAPE/MASE (35,73 vs. 31,24)**
  — achado real e já documentado, não é um "bug a corrigir", é uma
  limitação a expor honestamente na Tela 02/05.
- **XGBoost abaixo da meta de AUC-ROC 0,85** em todas as partições
  (0,846 validação / 0,7965 teste / 0,7637 backtest médio) — mesma
  natureza: expor, não esconder atrás do F1 alto.
- **K-Means sem k ótimo em nenhuma das 3 métricas** — k=4 é decisão de
  negócio documentada, não resultado estatístico — já formalizado no
  checkpoint `ML-2` do `PLAN.md` (fechado 2026-08-22).
- **Divergência de rótulos de cluster**: **não é mais uma lacuna** — já
  corrigida no banco (migrations 029/030). O que resta é atualizar a
  documentação que ainda a descreve como aberta (achado #1).
- **`PLAN.md` "Critérios finais de aceite"**: nenhum item está
  formalmente marcado, apesar de a maioria já estar de fato atendida por
  esta auditoria — fechar isso é trabalho de governança, não de dado.

---

## Critérios de Aceite (status real encontrado nesta auditoria)

| Critério (do pedido original) | Status hoje | Ação necessária |
|---|---|---|
| Nenhum KPI hardcoded se existir fonte oficial | ⚠️ Parcial — `VOLUME_HISTORICO_2025` e a data do header ainda são hardcoded | Achados #12, #15 |
| Documentação e dashboard consistentes | ⚠️ Parcial — docs descrevem um bug de cluster já corrigido | Achado #1 |
| Target do XGBoost correto | ✅ Já correto ("risco de exceder o tempo esperado", nunca "OLA") | Nenhuma |
| SHAP matematicamente bem interpretado | ❌ Não verificável hoje — falta `base_value` | Achado #7 |
| Prophet total mostra incerteza | ❌ Não — só ponto | Achado #4 |
| Comparação com baseline visível | ❌ Não — só em doc estática | Achado #5 |
| Forecast por equipe reflete A/B/C real | ⚠️ Parcial — dado correto no banco, mas método não aparece na UI | Achado #6 |
| Split proporcional não é chamado de individual | ✅ Já correto (`metodo` real, não inferido, existe na base) | Nenhuma |
| Métricas não persistidas não são inventadas | ✅ Respeitado nesta auditoria e nos guias | Nenhuma |
| Clusters derivados das tabelas oficiais | ✅ Sim, e já corrigidos | Nenhuma |
| k=4 não é apresentado como ótimo estatístico | ✅ Já correto (`PLAN.md` ML-2) | Nenhuma |
| Projeção aritmética não é chamada de probabilidade | ❌ Não — o campo se chama `probabilidade_atingir_meta_pct` mesmo o método sendo `"projecao_linear"` (determinístico) | Achado #25: renomear para `projecao_atingimento_meta_pct` na Fase 3 |
| Regras não são chamadas de IA | ✅ Respeitado (`REGRA` sempre distinta de `MODELO`) | Nenhuma |
| Requisitos originais rastreáveis | ✅ Parte C desta auditoria cobre 100% | Nenhuma |

---

## Verificação (quando a implementação começar)

- Reexecutar as queries read-only desta auditoria (`ml.dim_cluster`,
  `ml.fct_perfil_cluster`, `dw.fct_incidentes.kpi_status_int`/
  `excedeu_tempo_esperado`, `ml.fct_previsao_grupo.metodo`) para
  confirmar que o estado do banco não mudou entre esta auditoria e a
  implementação.
- Para cada tabela nova (Parte F), confirmar contagem de linhas esperada
  após a primeira execução do script correspondente.
- Confirmar no código do notebook exatamente o que o `TreeExplainer`
  explica (saída bruta/log-odds pré-calibração, ou outra) — documentar
  antes de escrever qualquer teste.
- `soma(shap_value) + base_value == saída_bruta_do_xgboost` (tolerância
  numérica pequena) para uma amostra de incidentes — **nunca** contra
  `score_calibrado`/`logit(score_calibrado)` — antes de expor o waterfall.
- Verificar separadamente que o calibrador isotônico é monotônico
  (saída bruta crescente → `score_calibrado` não decrescente), como
  checagem da etapa de calibração, distinta da checagem do SHAP acima.
- `tsc -b`/`npm run build` limpos após a extensão de `api.ts`.
- Checklist da Parte C (rastreabilidade) revisitado linha a linha contra
  a implementação final das 6 telas.
