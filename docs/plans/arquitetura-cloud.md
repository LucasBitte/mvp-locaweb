> Plano original recebido em 10/09/2026. Estado da implementação e correções verificadas: [cloud/README.md](../../cloud/README.md). Os checkboxes abaixo preservam o texto original; não atestam execução.

# Plano — Arquitetura Cloud adequada ao projeto existente

> **Princípio governante (definido pelo usuário, 2026-09-10):**
> **a arquitetura nova cabe no projeto; o projeto não muda para caber na
> arquitetura.** O dashboard React + API com dado real já funciona e está no
> ar — o objetivo é fazer *esse* produto rodar sobre a arquitetura-alvo, não
> reconstruí-lo para se parecer com um diagrama.
>
> **Teste de aceite de todo componente**: ele entra sem exigir mudança no que
> já funciona? Se exige, é redesenhado até caber — ou cai. Cada linha da §3
> passou por esse teste.
>
> **Critério de aceite final (usuário, 2026-09-10): o BI alvo é o dashboard
> React já no ar em `https://fiap.looplyai.com.br/`** — não é o Power BI. O
> plano está cumprido quando *esse* site continuar servindo dado real, agora
> lendo do RDS, com o pipeline orquestrado e os artefatos no S3. Power BI é
> opcional e vai para o Anexo A.
>
> Precedência em conflito: (1) código já mergeado, (2) `CLAUDE.md`,
> (3) `PLAN.md`, (4) este plano, (5) o diagrama.

## 1. A inversão mais importante: o sentido do dado

O diagrama trata o **S3 como origem** (`bronze/` → Glue → RDS). O projeto
tem a origem **dentro do Postgres** (`public.incidentes`, 122.543 linhas), e
todo o pipeline — notebooks 03/04/05, os 4 modelos, a API — nasce de lá.

Seguir o desenho ao pé da letra exigiria reconstruir a ingestão inteira: é o
caso mais claro de "mudar o projeto para caber na arquitetura", e está
vetado pelo princípio.

**Readequação**: o lake vira **destino**, não origem. Postgres/RDS continua
sendo a fonte; Glue exporta para `s3://.../bronze|silver|gold/` como camada
de persistência, arquivamento e leitura analítica. O diagrama entrega "S3
Data Lake + Glue" na apresentação, e nenhuma linha do pipeline muda.

## 2. A alavanca que torna a migração quase gratuita

`etl/db.py` monta a URL de conexão inteiramente de variáveis de ambiente
(`FIAP_DB_USER/PASSWORD/HOST/PORT/NAME`) e é o **único** ponto de conexão do
projeto — 17 arquivos passam por `get_engine()`: 6 notebooks do pipeline, 6
scripts de modelo, `app/api/deps.py`, `etl/transform.py` e 3 de teste.

**Apontar API + pipeline + notebooks + testes para o RDS é trocar 5
variáveis de ambiente. Zero linha de código.** A regra §6 do `CLAUDE.md`
("conexão sempre via `etl/db.py`, nunca hardcodar"), tomada na Sprint 1,
pagou o custo desta migração antecipadamente — e é o melhor argumento de
arquitetura que o projeto tem para apresentar.

## 3. Triagem: o que é aditivo, o que foi readequado, o que cai

| Componente do diagrama | Veredito | Como cabe |
|---|---|---|
| **GitHub Actions (CI)** | ✅ Aditivo | Não existe workflow hoje. Entra sem tocar em código de produto. |
| **Terraform / VPC / IAM** | ✅ Aditivo | Infra nova, vazia. |
| **RDS PostgreSQL** | ✅ Aditivo | Recebe as 30 migrations como estão. **Nomes preservados** (`dw`/`ml`) — ver §4.1. |
| **S3 Data Lake** | 🔧 Readequado | Vira destino alimentado pelo Postgres, não origem (§1). |
| **Glue** | 🔧 Readequado | Job **Python Shell** (0,0625 DPU) fazendo RDS → S3. Não Spark, não ingestão. |
| **Airflow** | ✅ Aditivo | O DAG chama os scripts **como já existem**, na ordem já documentada no `CLAUDE.md` §2. Nenhum script muda. |
| **dbt** | 🔧 Readequado | Só `sources` + `tests` + `docs` sobre as tabelas que já existem. **Não materializa nada, não reescreve os notebooks 03/04/05.** Ver §4.2. |
| **MLflow** | ✅ Aditivo | Tracking em volta dos treinos existentes (poucas linhas de instrumentação, nenhuma mudança de lógica ou de seed). |
| **Azure ML** | 🔧 Readequado | Registry/tracking remoto. **Não** vira executor de treino — mover o treino para lá mudaria o projeto e gastaria egress. |
| **Power BI** | 📦 Anexo A | **Não é o BI alvo** — o dashboard React é. Só se sobrar tempo. Ver §4.3. |
| **Branch `develop`** | ✅ Aditivo | Trivial, e o squash-merge já é convenção. |
| **Docker Swarm** | ❌ **Cai** | Trocaria um deploy que funciona (compose + Traefik, no ar) por outro equivalente, só para casar com o desenho. É a definição do que o princípio proíbe. |
| **`subapp.looplyai.com.br`** | ❌ **Cai** | O domínio em produção é `fiap.looplyai.com.br`, funciona e é o critério de aceite. Trocar é mudar o projeto pelo desenho. |

Resumo: **6 aditivos, 4 readequados, 1 adiado para anexo, 2 caem.** Nada no
produto muda — e o produto é justamente o critério de aceite.

## 4. Decisões fechadas

### 4.1 Nomenclatura: mantida (`dw`/`ml`)
O diagrama pede `raw_incidents_silver`, `gold_bi`, `fct_previsoes`,
`fct_ola_risk`, `fct_cluster_id`. Renomear custaria reescrever 30 migrations,
6 routers, `api.ts`, os notebooks e os testes — semanas, com janela de
divergência, e **zero ganho analítico**. Decidido pelo princípio, não por
preferência: os nomes atuais vão para o RDS como estão.

### 4.2 dbt entra sem reescrever o pipeline
Migrar os notebooks 03/04/05 para models dbt é reescrever a camada de
transformação — invasivo. Mas dbt tem um modo que é puramente aditivo:
declarar as tabelas existentes como `sources` e escrever `tests` sobre elas.
Isso entrega **lineage, testes de dados e documentação navegável** sem
materializar uma única tabela.

Os testes devem codificar as invariantes que hoje são prosa no `CLAUDE.md`
§3: grão 1 linha = 1 incidente em `dw.fct_incidentes`, os filtros da fato
(`status <> 'Sem Intervenção'`, `aberto >= 2025-01-01`), unicidade das
chaves das 6 dimensões, e o caráter leakage-free de `ml.ml_cluster_dataset`
e `ml.ml_sla_classification_dataset`. Prosa vira asserção executável — esse
é o ganho real, e ele não exige reescrever nada.

### 4.3 O BI alvo é o dashboard React, não o Power BI
Decisão do usuário: o BI que precisa estar funcionando sobre esta
arquitetura é `https://fiap.looplyai.com.br/`. Isso rebaixa o Power BI de
fase para **anexo opcional** e resolve, de quebra, o risco de duplicação: os
"5 dashboards" do diagrama recobrem quase exatamente as 6 telas React já no
ar, e duas front-ends contando a mesma história divergem rápido — o projeto
**já tem 2 achados de auditoria** sobre texto contradizendo dado
(`docs/prds/etapa5-api.md` §4.5).

Se sobrar tempo (Anexo A), Power BI entra com escopo que o React não cobre:
**performance dos modelos** (`fct_model_metrics` do próprio diagrama,
alimentado pelo MLflow) e histórico longo. Complementa, nunca compete.

### 4.4 Host do Airflow: VPS Hostinger de um integrante do grupo
Resolve o custo (MWAA está fora, §8) sem coabitar com produção. Três
condições registradas na Fase 6.

### 4.5 Orçamento: AWS Free Tier + US$ 100 Azure
Ver §8. Elimina MWAA e capacidade Fabric; redimensiona Glue.

### 4.6 Região e acesso ao RDS — correção de duas premissas erradas
Levantado em 2026-09-10, ao responder "o que preciso fazer na AWS". Duas
afirmações anteriores deste plano estavam incorretas e teriam causado
retrabalho:

**(a) Latência deixa de ser desprezível.** Hoje a API alcança o Postgres no
próprio host do VPS (`docker-compose.prod.yml`:
`extra_hosts: host.docker.internal:host-gateway`) — na prática, loopback. Os
endpoints fazem **queries sequenciais**, medido no código: `painel` 11,
`alertas` 11, `detalhe` 8, `fatores` 7, `kpi` 6, `clusters` 2. Com o RDS
fora do Brasil (`us-east-1`, RTT ~120ms), `/api/painel` ganharia ~1,3s de
rede pura — regressão visível no site que é o **critério de aceite** deste
plano. Em `sa-east-1` (São Paulo), o mesmo endpoint fica na casa de ~165ms.

Decisão: **`sa-east-1`**, salvo se a verificação de free tier na região
mostrar que a instância elegível não está coberta lá — nesse caso a escolha
vira um trade-off explícito entre custo e latência, a ser registrado aqui.
Alternativa a considerar só se a latência ainda incomodar: reduzir o número
de round-trips por endpoint (consolidar queries), o que é mudança no produto
e portanto precisa de aprovação sob o princípio governante.

**(b) "RDS em subnet privada" estava errado.** A API roda **fora da AWS**
(no VPS), então subnet privada tornaria o banco inalcançável. O desenho
correto é endpoint acessível ao VPS, com **Security Group restrito ao IP
público do VPS** e **TLS obrigatório** (`sslmode=require` na string de
conexão — `etl/db.py` monta a URL de env vars, então isso entra sem código).
Nunca `0.0.0.0/0` no Security Group.

## 5. Estratégia de execução: expand/contract

Com o dashboard no ar, toda fase segue: **expand** (novo em paralelo, sem
tocar o caminho de produção) → **dual-run** (os dois rodam, diferença é
medida) → **cutover** (troca de env var) → **contract** (o antigo sai só
após estabilidade). O Postgres do VPS permanece servível e é rollback de um
comando por toda a Sprint.

## 6. Fases

### Fase 0 — CI, sem tocar em código de produto ⬜
Não existe **nenhum** workflow hoje, e você vai mexer na fundação de dados
com o produto no ar.

Bloqueador: só `test_health` e `tests/test_transform.py` rodam sem banco;
**21 dos 22 testes de API** precisam do `fiap` vivo e asseguram contra
valores correntes (`SELECT MAX(origem)`, `COUNT(*) FROM dw.dim_grupo`).
Rodar isso no CI exigiria expor o Postgres do VPS aos runners — inaceitável.

Solução aditiva (os testes existentes ficam **intactos**): marcar os que
dependem de dado vivo com `@pytest.mark.banco_real` e excluí-los do CI;
subir Postgres efêmero como service container, semeado pelas 30 migrations
+ fixture mínimo, para o resto. Workflows: lint (`oxlint` + `ruff`), test,
build (`tsc -b` + `vite build`). Fechar os **pins de versão** de
`requirements*.txt` — já é checkpoint aberto no `PLAN.md` Anexo A/ML-3, e CI
sem pin quebra sozinho.

Sem cloud, sem custo. Destrava todas as fases seguintes.

### Fase 1 — Terraform: infra vazia ⬜
VPC, S3 (versionado, block-public-access), RDS alcançável pelo VPS com
Security Group restrito ao IP dele e TLS obrigatório (**não** subnet
privada — ver §4.6), IAM least-privilege. State remoto em S3 + lock DynamoDB — **nunca state local**.
`terraform plan` no PR. Alarme de billing criado aqui (§8). **Sem NAT
Gateway** (não é free tier e vira o maior custo fixo silencioso da conta).

### Fase 2 — Carga paralela e dual-run ⬜
Aplicar as 30 migrations no RDS — são idempotentes e versionadas, é
exatamente para isso que existem. Copiar o bronze, rodar o pipeline apontado
ao RDS, e **comparar tabela a tabela contra o VPS**: contagens, checksums
das fatos, e os 6 endpoints respondendo idêntico nas duas origens.
Divergência é achado documentado, não arredondamento aceito.

### Fase 3 — Cutover do serving layer ⬜
Trocar as 5 env vars do `.env.production` da API. Rollback = trocar de
volta. VPS Postgres fica de pé como fallback pelo resto da Sprint.

### Fase 4 — S3 + Glue, no sentido correto ⬜
Job Glue **Python Shell** (0,0625 DPU) exportando RDS → `s3://.../bronze`,
`/silver`, `/gold` em Parquet particionado. Glue Catalog sobre o bucket dá
consulta analítica e a figura de "data lake" do diagrama.

Registro honesto de dimensionamento: 122.543 / 41.441 linhas são dezenas de
MB. Glue não tem free tier e job Spark cobra a partir de 2 DPUs — Python
Shell é a fração que cabe, **e é o dimensionamento correto para o volume**.
Dizer isso na apresentação é mais forte do que exibir Spark ocioso.

### Fase 5 — dbt como camada de teste e lineage ⬜
`sources` + `tests` + `docs` sobre as tabelas existentes, sem materializar
nada (§4.2). `dbt test` no PR passa a rodar contra o Postgres efêmero da
Fase 0. Migrar models de verdade fica fora do escopo desta Sprint.

### Fase 6 — Airflow orquestrando o que já existe ⬜
Hoje o pipeline é *"rode estes 11 comandos nesta ordem"*, com as
dependências (`pressao_equipe` depois de `forecast_equipe`,
`forecast_produto` depois do forecast total) escritas em **prosa** no
`CLAUDE.md` §2. O DAG transforma prosa em grafo verificável — essa é a
fraqueza arquitetural genuína do projeto, e a correção é puramente aditiva:
o DAG chama `jupyter nbconvert ...` e `python notebooks/*.py` **como estão**.

Host: VPS Hostinger de um integrante (§4.4). Três condições:

1. **Verificar RAM e carga atual.** Airflow com LocalExecutor
   (scheduler + webserver + worker + metadados) quer ~4 GB. Confirmar o
   plano contratado e o que a máquina já hospeda — contenção é real.
2. **Credencial cross-cloud em máquina de terceiro.** Esse host guardaria
   acesso a AWS, Azure e ao Postgres de produção. Obrigatório: credencial
   escopada por conexão (nunca admin), rotável e revogável **por você**, sem
   depender do dono. Se não for possível, o Airflow não recebe credencial —
   o DAG chama um endpoint que você controla.
3. **Reprodutibilidade como seguro.** `airflow/` versionado no repo, subida
   via compose. Se a VPS sumir na semana da entrega, você re-sobe em
   qualquer lugar a partir do git.

### Fase 7 — MLflow ⬜
Ataca diretamente as 3 limitações mais graves do projeto (Prophet não bate o
baseline, XGBoost 0,80 vs meta 0,85, K-Means sem `k` defensável): são
problemas de **comparar runs**, que é o que um tracker existe para fazer.
Hoje versão de modelo é uma coluna `modelo_versao_referencia` +
`data_execucao`.

Instrumentação aditiva: `mlflow.log_*` em volta dos treinos, sem alterar
lógica, hiperparâmetro ou seed — os números em produção não podem mudar por
causa disto. Um backend só: metadados no RDS, artefatos em `s3://.../mlflow`.
Azure ML como registry remoto (§3), não como executor.

### Fase 8 — `develop` + higiene de branch ⬜
Único item barato que sobrou do desenho. Swarm e a troca de domínio **não
entram** (§3).

### Critério de aceite final ✅ = plano cumprido
`https://fiap.looplyai.com.br/` no ar, as 6 telas servindo dado real, agora
lendo do **RDS**, com o pipeline orquestrado por **Airflow**, artefatos no
**S3**, runs no **MLflow** e CI verde — sem que nenhuma linha do produto
tenha mudado para isso acontecer.

*(Baseline não verificado desta sessão: a política de rede do ambiente negou
a conexão com o domínio — 403 no CONNECT do proxy. Confirmar o estado atual
do site antes de iniciar a Fase 2.)*

## 7. Segurança

- **GitHub → AWS via OIDC**, nunca access key de longa duração em secret.
- Segredo do RDS em Secrets Manager, não em `.env.production` no VPS.
- Airflow em host de terceiro: escopo mínimo por conexão, rotável por você
  (Fase 6, condição 2).
- `.env.production` e state do Terraform **nunca** versionados — conferir o
  `.gitignore` antes da Fase 1.
- Egress cross-cloud (RDS → Azure) é custo e superfície: mais um motivo para
  Azure ML ser registry, não executor.

## 8. Custo — AWS Free Tier + US$ 100 de crédito Azure

| Componente | Cabe? | Nota |
|---|---|---|
| **S3** | ✅ Folgado | O dado inteiro são dezenas de MB contra os GB da cota. |
| **RDS Postgres** | ✅ Cabe | Menor instância elegível, single-AZ, em `sa-east-1` (§4.6). Confirmar que a cota do free tier cobre a região. |
| **Terraform / IAM / VPC** | ✅ Grátis | **Exceto NAT Gateway** — pago, não é free tier. Desenhar sem. |
| **GitHub Actions** | ✅ Grátis | Cota cobre lint/test/build deste tamanho com folga. |
| **Glue** | ⚠️ Só Python Shell | Sem free tier. Spark cobra a partir de 2 DPUs; Python Shell é 0,0625. |
| **MLflow self-hosted** | ✅ Cabe | Metadados no RDS, artefatos no S3 — reaproveita o já orçado. |
| **Airflow** | ✅ Já pago | VPS Hostinger do grupo (§4.4). |
| **Azure ML** | ⚠️ Com disciplina | US$ 100 duram se o compute **escalar a zero** ocioso. Como registry, o consumo é mínimo. |
| **MWAA** | ❌ Não cabe | Centenas de dólares/mês contra US$ 0 de crédito AWS. |
| **Power BI Fabric** | ❌ Não cabe | Menor capacidade F consome os US$ 100 em menos de um mês; Pro é licença recorrente fora do crédito. |

**Verificar antes da Fase 1, não durante:**
- **Qual free tier é o seu** — a AWS tem duas modalidades conviventes (a
  legada de 12 meses por serviço, e a mais recente baseada em crédito com
  janela de meses). Muda o prazo e o que expira quando. Conferir no console
  de Billing e **anotar aqui a data de expiração**: ela pode cair antes da
  entrega. Os valores acima são ordens de grandeza, não cotação.
- **Alarme de billing** na AWS e alerta de crédito na Azure, criados junto
  com o Terraform na Fase 1.

## 9. Riscos

| Risco | Mitigação |
|---|---|
| Dashboard cair durante a migração | Expand/contract; VPS Postgres como rollback de 1 comando até o fim |
| Dashboard ficar lento pós-cutover (11 queries sequenciais × RTT) | §4.6: RDS em `sa-east-1`; medir latência por endpoint no dual-run da Fase 2, antes do cutover |
| Dois bancos divergindo em silêncio | Fase 2 compara tabela a tabela e endpoint a endpoint antes do cutover |
| Instrumentação do MLflow alterar número em produção | Fase 7: só `log_*`, sem tocar lógica, hiperparâmetro ou seed; conferir contagens depois |
| VPS de terceiro sumir antes da entrega | `airflow/` versionado e re-provisionável do git; credencial escopada e rotável por você |
| Free tier / crédito expirando antes da entrega | Anotar expiração na Fase 1; Fases 0-3 são as que menos dependem de crédito |
| Custo estourando | §8 dimensionado ao orçamento; alarme de billing na Fase 1 |
| Power BI contradizendo as 6 telas | §4.3: escopo distinto definido antes de construir |
| Contradição com `sprint3-apresentacao.md` §1 | Item de trabalho da Fase 0 (§11) |

## 10. Evidência por fase

Engenharia robusta só conta se for demonstrável — cada fase produz artefato
verificável, não slide:

| Fase | Evidência |
|---|---|
| 0 | Workflow verde no PR; suíte rodando sem tocar produção |
| 1 | `terraform plan` no PR; state remoto com lock; alarme de billing ativo |
| 2 | Tabela de comparação RDS × VPS (contagens, checksums, 6 endpoints) + latência medida por endpoint |
| 3 | Cutover com rollback demonstrado; dashboard no ar durante todo o processo |
| 4 | Objetos Parquet no lake + run do Glue + consulta pelo Catalog |
| 5 | Lineage do dbt + testes de dados codificando as invariantes do `CLAUDE.md` §3 |
| 6 | DAG com as dependências reais, execução datada, re-provisionável do git |
| 7 | Comparação de runs endereçando as 3 limitações conhecidas |
| 8 | `develop` em uso; PRs passando pelo CI |
| **Final** | **`fiap.looplyai.com.br` no ar sobre RDS + Airflow + S3, produto inalterado** |

## 11. Pendência de narrativa (não é rodapé)

Parte do alvo é a arquitetura do projeto AWS anterior, removida deste repo
deliberadamente na Sprint 2: **#24** (`5a0404f`, narrativa S3/Glue/dbt/RDS de
6 docs e 4 notebooks; renomeou o notebook 04; apagou a seção que listava
"Airflow, Power BI, dbt tests") e **#26** (`1cd87a2`, código executável —
modos de ingestão `rds` e `parquet` do XGBoost, 98 → 94 células).

E `docs/sprint3-apresentacao.md` §1 hoje apresenta a remoção como virtude:
*"sem dependência de infraestrutura legada AWS/dbt/RDS, removida no início
da Sprint 2"*.

A Sprint 4 precisa de justificativa explícita para a reintrodução, e o §1
precisa ser reconciliado. Contradição interna é o que uma banca encontra
primeiro. **Item de trabalho da Fase 0.**

## 12. O que este plano deliberadamente não faz

- Não renomeia tabelas para os nomes do diagrama (§4.1).
- Não reconstrói a ingestão para tratar S3 como origem (§1).
- Não reescreve os notebooks 03/04/05 como models dbt (§4.2).
- Não recria as 6 telas React em Power BI (§4.3).
- Não move treino de modelo para o Azure ML (§3).
- Não troca compose+Traefik por Swarm (§3).
- Não trata Glue/Spark como necessidade de volume (Fase 4).
- Não troca o domínio de produção por `subapp.looplyai.com.br` (§3).
- Não trata o Power BI como o BI do projeto — o dashboard React é (§4.3).

---
*Criado em 2026-09-09, reescrito em 2026-09-10 sob o princípio "a
arquitetura cabe no projeto". Status: plano, nada executado. Nenhuma fase
acima implica código, migration, retreino ou mudança de infraestrutura nesta
tarefa.*

---

## Anexo A — Power BI (só se sobrar tempo)

Read-only no RDS, escopo distinto das 6 telas (§4.3). **Power BI Desktop
(gratuito)** para construir; trial de Pro apenas para demonstrar o *Publish
to Web* que o próprio diagrama pede. Capacidade Fabric está fora do
orçamento (§8).

Escopo obrigatoriamente distinto das 6 telas React (§4.3): performance de
modelo e histórico longo, alimentados por `fct_model_metrics`/MLflow. Se o
tempo não permitir, o anexo simplesmente não é executado — nada no plano
principal depende dele.
