# Execução cloud sobre o produto existente

Implementação na branch `abner`, baseada em `main` (`594842f`). O dashboard,
routers, `etl/db.py`, migrations e modelos existentes foram preservados.
O plano original está em `docs/plans/arquitetura-cloud.md`.

## Estado e dependências externas

Código disponível: CI isolado, Terraform com backend remoto, RDS com TLS,
lake S3 + exportador Glue, Catalog, dbt sources/tests/docs, DAG dos 11 comandos,
tracking MLflow, promoção de artefato para registry Azure e comparação dual-run.
Arquivos de configuração não constituem evidência de execução em cloud.

Conta informada pelo usuário: `259081046223`, IAM `abner-admin`.
Em 10/09/2026: crédito AWS **US$ 94,77**, validade informada **84 dias**
(aproximadamente 03/12/2026; confirmar a data exata no console). Região alvo:
`sa-east-1`. Ainda faltam perfil AWS autenticado, IPs /32, acesso e capacidade
da VPS Airflow, identidades de serviço, email de orçamento e Azure Registry.

Não houve apply, cópia de dados, retreino, cutover ou validação do site sobre RDS.
Não há alegação de CI verde no GitHub antes de publicar a branch e executar o workflow.

## Correções necessárias ao plano

- `PGSSLMODE=require` é a configuração TLS da libpq, respeitada pelo psycopg2.
  As cinco variáveis FIAP sozinhas não acrescentam `sslmode` à URL existente.
- O mart SLA contém `duracao_horas` para auditoria/rótulo. A função real
  `construir_features` a exclui. Testamos essa função isolada com alterações
  nos rótulos/duração e truncamento do futuro. O clustering é descritivo e usa
  duração legitimamente. dbt verifica grão, população, campos e filtros, sem
  prometer que inspeção de uma tabela prova ausência de todo leakage.
- Glue em VPC não recebe IP público. Sem NAT, usa gateway S3 e endpoints
  privados de Secrets Manager e Logs. **Endpoints, RDS, IPv4 público, backup,
  Secrets Manager e Glue podem consumir créditos**. O orçamento de US$ 15/mês
  é alerta, não cotação nem teto de cobrança. Calcular custo e duração antes
  de aplicar; saldo de crédito não garante que 84 dias de infra caibam nele.
- Pins foram resolvidos a partir do ambiente local, com locks universais
  Python 3.11. São candidatos validados em CI, não um `pip freeze` da VPS.
  Comparar o ambiente de treino da VPS antes de ativar o DAG para evitar
  mudança numérica por dependências. Não se realizou treino para validar pins.

## 0. Validar localmente

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -m 'not banco_real and not integration'
python -m ruff check app/api etl tests scripts cloud airflow/dags
cd app/web
npm ci
npm run lint
npm run build
```

O workflow CI sobe Postgres efêmero `fiap_ci`, aplica as 30 migrations,
semeia fixture sintético, roda integração e dbt. Os 21 contratos de API
existentes permanecem intactos e recebem marker `banco_real` na coleta.
Rodar esses contratos explicitamente no dual-run: `python -m pytest -m banco_real`.
O fixture recusa banco sem sufixo `_ci` ou sem `CI=true`.
Regenerar locks: `uv pip compile requirements-dev.in --universal --python-version 3.11 -o requirements-dev.txt`
(repetir para requirements e requirements-notebooks).

## 1. Bootstrap e plan

Autenticar perfil local sem enviar credenciais pelo chat; preferir sessões
temporárias. Validar a conta com `aws sts get-caller-identity --profile locaweb`.
Terraform também recusa contas diferentes da informada.

```sh
aws cloudformation deploy --profile locaweb --region sa-east-1 \
  --stack-name locaweb-state --template-file infra/bootstrap.yaml \
  --parameter-overrides StateBucketName=SEU-BUCKET-locaweb-state
python -m pip download --no-deps --only-binary=:all: python-dotenv==1.0.1 -d infra/.artifacts
cp infra/backend.hcl.example infra/backend.hcl
cp infra/terraform.tfvars.example infra/terraform.tfvars
# Preencher bucket, IPs /32, email e ARN de segredo reader (sem valor secreto).
terraform -chdir=infra init -backend-config=backend.hcl
terraform -chdir=infra plan
```

O CloudFormation cria o backend antes do Terraform: nenhum state local de
infra é necessário. `terraform init -backend=false` é apenas validação estática.
Bucket e lock têm retenção; state/plan/tfvars/env não entram no git.
O ARN reader pode existir antes do RDS; seu valor é preenchido depois de criar
o banco e provisionar o usuário SQL. Não executar o Glue antes disso.

Para PRs: criar/reutilizar provider IAM OIDC `token.actions.githubusercontent.com`
com audience `sts.amazonaws.com`, aplicar `infra/oidc.yaml` e configurar o
environment GitHub `cloud-plan` com revisão obrigatória e branches permitidas.
Variáveis: `AWS_PLAN_ROLE_ARN`, `VPS_CIDRS_JSON`, `LAKE_BUCKET`, `BUDGET_EMAIL`,
`GLUE_READER_SECRET_ARN`, `TF_STATE_BUCKET`. O role lê infra/state e escreve
somente locks; não faz apply nem lê senhas. Forks não recebem esse acesso.
Informar os nomes exatos dos buckets state e lake ao criar o role OIDC.

## 2. Carga paralela

Manter o VPS como origem servível. Congelar escritas durante captura e comparação.
Usar `pg_dump --format=custom --table=public.incidentes` na origem e
`pg_restore --no-owner --no-acl --exit-on-error` no RDS vazio, com libpq configurada
por ambiente (senha nunca na linha de comando). Aplicar `python -m scripts.migrate`
no RDS usando `get_engine()`. Nenhuma opção `--clean`, DROP ou TRUNCATE na origem.
Rodar o pipeline somente no destino, após registrar versões e baseline.

Para um primeiro ensaio de fidelidade, copiar também os resultados existentes;
para o dual-run de treino, datas de execução e possíveis diferenças numéricas
serão achados reais. O comparador não elimina colunas voláteis nem arredonda.
Resolver/documentar cada divergência; resultado divergente bloqueia cutover.

```sh
# SOURCE_FIAP_DB_{USER,PASSWORD,HOST,PORT,NAME} e TARGET_FIAP_DB_* em memória.
# Senhas/user URL-encoded, conforme contrato atual de etl/db.py.
PGSSLMODE=require python -m cloud.compare \
  --source-api https://fiap.looplyai.com.br --target-api http://localhost:8001
```

Compara todas as tabelas dos quatro schemas (public limitado a incidentes),
contagens, SHA-256 por multiconjunto de linhas, seis payloads e latências.
Cada banco tem snapshot repeatable-read; como os snapshots não são sincronizados
entre servidores, congelar escritas é indispensável. Saída é JSON local ignorado
pelo git; código de saída 1 em qualquer divergência.

## 3. Serving e rollback

Depois de migrations/carga, aplicar `cloud/roles.sql` no RDS. Criar logins
separados para API e Glue membros de `fiap_reader`; pipeline precisa ser dono
das tabelas recriadas (login `fiap_pipeline`, sem superuser). Senhas únicas no
Secrets Manager, no formato `username,password,host,port,dbname`.
Metadados MLflow usam **database separado `mlflow`**, com proprietário próprio.
Não conceder papel admin à API, Glue, Airflow ou MLflow.

Identidades AWS da VPS: cada processo só lê seu SecretId; MLflow acrescenta
Get/Put/List no prefixo `mlflow/`; Airflow só Start/GetJobRun no job exportador
e Start/GetCrawler no crawler `locaweb-lake`,
além de seu segredo SQL. Usar perfil temporário/credential_process ou Roles
Anywhere, rotável/revogável pelo dono da conta. Não copiar perfil admin à VPS.

Configurar `FIAP_DB_SECRET_ID`, `AWS_CONFIG_DIR`, `AWS_PROFILE` sem senha RDS
em `.env.production`. O launcher lê Secrets Manager e injeta env em memória.
Preservar o env original como rollback, com acesso restrito no host.

```sh
docker compose -f docker-compose.prod.yml -f cloud/serving-compose.yml up -d --build api
# Confirmar as seis telas e medir latência antes de retirar qualquer fallback.
# Rollback (compose original; env original do VPS permanece):
docker compose -f docker-compose.prod.yml up -d --build --force-recreate api
```

O compose/Traefik e `fiap.looplyai.com.br` continuam sendo o serving layer.
Há recriação do container API durante cutover: medir a interrupção; o código
não promete zero downtime. O banco antigo permanece até estabilidade comprovada.

## 4–6. Lake, qualidade e Airflow

Glue Python Shell 3.9 usa analytics preinstalado e wheel dotenv no S3,
sem instalar da internet. Lê o próprio `etl/db.py` publicado, exporta snapshot
read-only em `bronze|silver|gold/schema/tabela/snapshot_date=.../run_id=...`.
Somente um manifesto final indica snapshot completo. Falha deixa objetos
parciais sem manifesto, que não devem ser usados como snapshot válido.
O DAG roda o crawler `locaweb-lake` após export bem-sucedido; consultas devem selecionar
um run do manifesto, nunca somar todos os snapshots históricos.

dbt é apenas sources/tests/docs: `dbt test --project-dir dbt --profiles-dir dbt`.
Não executar `dbt run` nem reescrever os notebooks como models.

Na VPS Airflow: confirmar RAM disponível (referência ~4 GB), espaço e carga.
Clonar o repo para o usuário de serviço com permissão de escrita nos notebooks
executados e `data/ml`. Configurar as variáveis exigidas por `airflow/compose.yml`
e senhas fortes URL-safe para metadados, Fernet e webserver. Credenciais AWS
são somente perfis de serviço montados read-only.

```sh
docker compose -f airflow/compose.yml --profile setup run --rm init
docker compose -f airflow/compose.yml run --rm webserver users create \
  --username operador --firstname Operador --lastname FIAP --role Admin --email SEU-EMAIL
docker compose -f airflow/compose.yml up -d scheduler webserver
```

UI restrita a loopback; acessar por túnel SSH. DAG nasce pausado, schedule=None,
sem catchup/retries, max_active_runs/tasks=1 para evitar duplicar append ou
competir por RAM. Disparar manualmente só após liberar o RDS de destino.
Runtime de treino fica num venv separado das dependências do Airflow.
O DAG não faz migrations automaticamente em produção.

## 7. Tracking e registry

Subir `cloud/mlflow-compose.yml` com segredo do database `mlflow`, bucket,
perfil dedicado e allowed-hosts. Porta só loopback; fornecer ao Airflow um
túnel SSH ou proxy autenticado. Não expor tracking anônimo à internet.
O wrapper registra commit/comando/tempo, artefatos novos e métricas existentes
do Prophet. O XGBoost já possui seu próprio log de parâmetros/métricas/bundle;
ele usa o mesmo MLFLOW_TRACKING_URI. A falha de tracking interno hoje é capturada
pelo notebook: verificar presença do run do modelo, não apenas do wrapper.
Clustering: artefatos/diagnóstico preservados; comparação de métricas entre runs
ainda precisa de uma execução real validada, não há números fabricados.

Azure é promoção explícita, fora do DAG de treino:

Procedimento completo, configuração da assinatura, Bicep e verificação de
upload/download: [`azure/README.md`](azure/README.md).

```sh
az login
az extension add --name ml
python -m cloud.register_azure --run-id RUN --artifact-path model/bundle.pkl \
  --subscription SUBSCRIPTION-ID --registry-name REGISTRY --name risco-sla --version 1
```

Artefato custom_model, sem executor/compute Azure e sem upload do dataset.
Configurar alertas de crédito na assinatura Azure antes da promoção.

## Aceite que ainda exige evidência

Plan revisado e apply datado, alertas recebidos, dual-run sem diferenças,
seis telas sobre RDS, rollback demonstrado, objetos e consulta Catalog,
dbt contra dados reais, execução Airflow datada e runs MLflow/Azure verificáveis.
Somente após isso o plano completo pode ser marcado como concluído.

Validação local em 10/09/2026: 15 testes sem banco passaram; ruff limpo;
React compilou (dois avisos de lint preexistentes); Terraform validate e dbt
parse passaram. Docker Desktop não disponibilizou engine neste ambiente: não
foram executados containers, integração Postgres/dbt test ou DagBag Airflow.
Branch develop criada localmente; publicação e política de PR pendentes.

Referências de implementação: [Glue Python Shell](https://docs.aws.amazon.com/glue/latest/dg/add-job-python.html),
[rede Glue](https://docs.aws.amazon.com/glue/latest/dg/start-connecting.html),
[RDS Terraform](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/db_instance),
[MLflow Tracking](https://mlflow.org/docs/latest/tracking).
