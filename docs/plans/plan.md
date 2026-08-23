# Prompt para Claude Code — Correção de Thresholds de SLA + Tabela de Metas Anuais

## Contexto

Projeto `mvp-locaweb` (desafio AIOps FIAP). Banco Postgres `fiap`, schemas
`public` (bronze) → `staging` (silver) → `dw` (star schema) → `ml` (marts de
features + saídas de modelo). Pipeline em notebooks Jupyter
(`notebooks/*.ipynb`), documentação em `docs/`.

Acabamos de comparar o `dw.dim_prioridade.threshold_sla_horas` atual contra o
**Dicionário de Dados oficial do desafio** (fonte da verdade fornecida pela
Locaweb/FIAP, não gerada pelo pipeline) e encontramos uma divergência crítica
nos thresholds de SLA, além de confirmarmos que a "meta anual" citada no
mockup do dashboard é uma regra de negócio real — só nunca foi carregada como
tabela no banco.

## Tarefa 1 — Investigar e corrigir os thresholds de SLA

### 1.1 Divergência encontrada

| Prioridade | Threshold oficial (fonte da verdade) | `dw.dim_prioridade.threshold_sla_horas` atual |
|---|---|---|
| 1 - Crítica | 4h | 4h (ok) |
| 2 - Alta | **4h** | **8h** (errado) |
| 3 - Média | **12h** | **24h** (errado) |
| 4 - Baixa | **24h** | **72h** (errado) |
| 5 - Muito Baixa | **96h** | sem meta (errado — deveria ter 96h) |

Nota: o dicionário técnico do projeto (`docs/dicionario-dados.md`) registra
que os marts em `ml.*` foram populados pela Silver usando a "heurística
original de P2=4h, sem o clamp da Etapa 2" — ou seja, é provável que o valor
correto (4h) já exista em algum ponto anterior do pipeline, e a divergência
tenha sido introduzida especificamente na etapa que gerou `dw.dim_prioridade`
e propagada para `dw.fct_incidentes`.

### 1.2 Investigação obrigatória antes de alterar qualquer coisa

1. Localize, nos notebooks do pipeline (provavelmente etapa de construção do
   `dw` — schema dimensional), onde `threshold_sla_horas` é definido para
   `dim_prioridade`. Identifique se é um dicionário hardcoded no código, uma
   tabela de apoio, ou lido de algum lugar.
2. Localize também onde a "Etapa 2" (mencionada em `docs/modelo-dimensional.md`)
   fez a correção/clamp que teria mudado os valores. Entenda a justificativa
   original dessa mudança — pode ter sido uma correção legítima para outro
   propósito que acabou usando o número errado, ou pode ter sido um erro de
   digitação/lógica.
3. Verifique se `staging.incidentes_silver` ou `ml.ml_base_features` já usam
   o valor correto (4h/4h/12h/24h/96h) em algum campo equivalente, para
   confirmar a hipótese de que só o `dw` diverge.
4. Levante todas as colunas de `dw.fct_incidentes` que dependem, direta ou
   indiretamente, de `threshold_sla_horas`:
   - `excedeu_tempo_esperado` (duração > threshold da prioridade)
   - `target_risco_sla`
   - `kpi_status_int`
   - `score_risco_operacional` (verificar se o threshold entra na soma dos
     fatores de risco)
5. Levante se `ml.fct_risco_incidente` (score de risco do XGBoost) foi
   treinado usando alguma dessas colunas como feature ou target — se sim, o
   modelo pode precisar ser retreinado após a correção, não só os dados
   recalculados.

Reporte o que encontrou (com trechos de código/notebook citados) **antes**
de aplicar qualquer correção, para validação.

### 1.3 Correção

Depois da investigação validada:

1. Corrija a fonte dos thresholds para os valores oficiais:
   `{1: 4, 2: 4, 3: 12, 4: 24, 5: 96}` (horas).
2. Recarregue `dw.dim_prioridade.threshold_sla_horas` com os valores corretos.
3. Recalcule, no `dw.fct_incidentes`, todas as colunas listadas no item 1.2.4
   que dependem do threshold. Preserve o grão e as demais colunas.
4. Se `ml.fct_risco_incidente` usa target/features derivados do threshold
   antigo, sinalize explicitamente se é necessário retreinar o modelo — não
   retreine automaticamente sem confirmação.
5. Atualize `docs/modelo-dimensional.md` registrando: o valor errado que
   existia, o valor correto, a causa raiz encontrada na investigação, e a
   data da correção.

### 1.4 Regra de elegibilidade para KPI (confirmar e alinhar)

O dicionário oficial define que só entram no cálculo de KPI incidentes que
atendem **todas** as condições:
- `prioridade` em (1, 2, 3) — prioridades 4 e 5 nunca entram no KPI;
- `incidente_pai` **vazio** (incidente com pai preenchido nunca entra no
  KPI, mesmo que prejudique outro incidente que entrou);
- `status <> 'Sem Intervenção'`.

Verifique se `dw.fct_incidentes` (ou os campos `entrou_kpi`/`kpi_status_int`)
já aplicam essas três condições corretamente. Hoje sabemos que o filtro de
`status <> 'Sem Intervenção'` já é aplicado no grão da tabela — confirme se
o filtro por `prioridade in (1,2,3)` e por `incidente_pai` vazio também são
respeitados nos campos de KPI, e corrija se não forem. Documente o resultado
da verificação em `docs/modelo-dimensional.md`.

---

## Tarefa 2 — Criar `dw.ref_meta_sla_anual`

### 2.1 Regras de negócio (fonte da verdade)

Só existem metas anuais para as prioridades **2 (Alta)** e **3 (Média)**, em
dois indicadores independentes: OLA quebrado no ano e volume total tratado
no ano. Cada indicador tem 6 faixas com um `% de atingimento` associado.

**OLA quebrado no ano** (quantidade de incidentes que violaram o SLA):

| Prioridade | Faixa | % de atingimento |
|---|---|---|
| 2 - Alta | < 31 | 150% |
| 2 - Alta | 31 a 35 | 125% |
| 2 - Alta | 36 a 39 | 100% |
| 2 - Alta | 40 a 45 | 75% |
| 2 - Alta | 46 a 53 | 50% |
| 2 - Alta | > 53 | 0% |
| 3 - Média | < 201 | 150% |
| 3 - Média | 201 a 230 | 125% |
| 3 - Média | 231 a 263 | 100% |
| 3 - Média | 264 a 290 | 75% |
| 3 - Média | 291 a 320 | 50% |
| 3 - Média | > 320 | 0% |

**Volume total de incidentes tratados no ano**:

| Prioridade | Faixa | % de atingimento |
|---|---|---|
| 2 - Alta | < 4585 | 150% |
| 2 - Alta | 4585 a 5388 | 125% |
| 2 - Alta | 5389 a 6168 | 100% |
| 2 - Alta | 6169 a 6252 | 75% |
| 2 - Alta | 6253 a 6336 | 50% |
| 2 - Alta | > 6336 | 0% |
| 3 - Média | < 19489 | 150% |
| 3 - Média | 19489 a 22116 | 125% |
| 3 - Média | 22117 a 22524 | 100% |
| 3 - Média | 22525 a 23892 | 75% |
| 3 - Média | 23893 a 24276 | 50% |
| 3 - Média | > 24276 | 0% |

Importante: a meta é definida em **contagem anual absoluta**, mas o
indicador é "medido mensalmente" — ou seja, não existe uma meta mensal
própria. O acompanhamento mensal é a posição acumulada do ano-corrente
frente a essas faixas anuais (ex.: "estamos em X quebras de OLA acumuladas
até o mês corrente, o que projetaria fechar o ano em qual faixa").

### 2.2 Desenho da tabela

Crie uma migration para `dw.ref_meta_sla_anual` com uma linha por
(prioridade, indicador, faixa), no estilo de uma tabela de referência/lookup,
não uma tabela de fatos. Sugestão de estrutura (ajuste se encontrar um
padrão melhor no projeto):

```sql
CREATE TABLE dw.ref_meta_sla_anual (
    ref_meta_sla_anual_sk   TEXT PRIMARY KEY,      -- MD5(prioridade_num||indicador||faixa_min||faixa_max)
    prioridade_num          INTEGER NOT NULL,       -- 2 ou 3
    indicador               TEXT NOT NULL,          -- 'ola_quebrado' | 'volume_tratado'
    faixa_min               INTEGER,                -- NULL = sem limite inferior
    faixa_max               INTEGER,                -- NULL = sem limite superior (faixa ">")
    pct_atingimento         NUMERIC NOT NULL,        -- 150, 125, 100, 75, 50, 0
    ordem_faixa             SMALLINT NOT NULL        -- 1 (melhor) a 6 (pior), para ordenar/buscar a faixa certa
);
```

Popule com as 24 linhas (2 prioridades × 2 indicadores × 6 faixas) descritas
no item 2.1. Trate as faixas abertas (`< 31` e `> 53`) com `faixa_min`/
`faixa_max` nulos conforme o lado aberto.

### 2.3 Lógica de cálculo (documentar, não é ML)

Implemente (fora do banco, na camada que for consumir — script Python ou
view SQL, o que for mais consistente com o resto do projeto) uma função que,
dado prioridade + indicador + contagem acumulada no ano, retorna a faixa e o
`% de atingimento` correspondente. Deixe claro na documentação e em qualquer
resposta de API que isso é uma **regra de negócio determinística**, não uma
saída de modelo de ML — não deve ser apresentado como "previsão" ou
"inteligência artificial" no dashboard.

Não implemente ainda a projeção/probabilidade de fechar o ano em qual faixa
(isso depende de decisão de produto sobre metodologia — projeção linear,
Poisson, etc. — trate como fora do escopo desta tarefa, só deixe a função de
lookup de faixa pronta e testável).

### 2.4 Critérios de aceite

- Migration aplicada, tabela `dw.ref_meta_sla_anual` com 24 linhas corretas
  (conferir manualmente contra as tabelas do item 2.1).
- Thresholds de `dw.dim_prioridade` corrigidos para `{1:4, 2:4, 3:12, 4:24,
  5:96}` horas, com a causa raiz da divergência documentada.
- Todas as colunas dependentes de threshold em `dw.fct_incidentes`
  recalculadas e consistentes com os novos valores (query de verificação
  antes/depois incluída no PR).
- `docs/modelo-dimensional.md` e `docs/dicionario-dados.md` atualizados
  refletindo os valores corretos e a existência da nova tabela.
- Nenhuma alteração em `ml.*` sem confirmação explícita (a menos que a
  investigação do item 1.2 comprove que o retreino é necessário — nesse caso,
  reportar e aguardar aprovação antes de retreinar).
- PR separado para: (a) correção de thresholds, (b) criação de
  `dw.ref_meta_sla_anual`. Não misturar as duas mudanças no mesmo commit,
  para facilitar revisão e rollback independente.

## O que NÃO fazer

- Não "corrigir" nada em `ml.*` silenciosamente — reportar primeiro.
- Não implementar a heurística de probabilidade de atingir a meta anual
  nesta tarefa — só a tabela de referência e o lookup de faixa.
- Não fazer merge direto na `main` — está protegida, exige PR com
  squash-merge conforme o restante do projeto.