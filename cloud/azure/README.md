# Azure: catálogo de modelos do MVP Locaweb

Escopo: Azure ML Registry, armazenamento gerenciado, permissões e orçamento;
publicação de arquivos reais de modelos com rastreabilidade e verificação de
download. Treino continua nos scripts existentes e tracking no MLflow do projeto.
O dashboard `fiap.looplyai.com.br` continua consumindo FastAPI/Postgres.

## Estado

Arquivos de infraestrutura e scripts preparados em `abner`. Sem evidência de
provisionamento, alerta recebido ou modelo registrado até executar os passos
abaixo na assinatura do usuário. Não existem modelos treinados na pasta local
`data/` desta máquina; é necessário obter um artefato da VPS ou um run MLflow.

## Ferramentas e login

```powershell
python -m uv venv .venv-azure
python -m uv pip install --python .venv-azure/Scripts/python.exe -r cloud/azure/requirements-tools.txt --prerelease=allow
.\cloud\azure\login.ps1
.venv-azure/Scripts/python.exe -m azure.cli bicep install --version v0.47.16
.venv-azure/Scripts/python.exe -m azure.cli extension add --name ml --version 2.44.1 --yes
```

Azure CLI isolada do ambiente de modelos. A CLI oficial fixada usa uma
dependência azure-batch prerelease; o sinalizador é necessário para o resolvedor
uv, não altera o treino. Login/MFA apenas na página Microsoft. O CLI armazena
tokens no perfil local do usuário, fora do git; nunca copiar esse perfil à VPS.

## Configuração explícita

Copiar `config.example.json` para `config.local.json` (ignorado pelo git).
Preencher subscription_id, tenant_id, resource_group, registry_name, location,
alert_email, monthly_budget e datas. O nome do Registry precisa ser único no
tenant. `eastus` no exemplo é candidato; verificar regiões permitidas pela
assinatura antes de escolher. Início do orçamento deve ser o primeiro dia do mês
e o fim deve cobrir a janela de uso autorizada.

```powershell
python -m cloud.azure.manage preflight
python -m cloud.azure.manage register-providers
python -m cloud.azure.manage plan
```

`preflight` é leitura de assinatura/tenant e providers. `register-providers`
registra os providers necessários; não cria instâncias. `plan` usa ARM what-if
e grava evidência em `cloud/evidence/azure/plan.json`.

## Custo e aplicação

O Azure ML Registry cria recursos de Storage e Container Registry gerenciados.
O template usa uma região, ACR Basic e Storage Standard_LRS. Não configura
replicação entre regiões. Na consulta pública de 11/09/2026, a unidade ACR
Basic em eastus custava US$ 0,1666/dia (~US$ 5/30 dias); o valor não inclui
Storage, operações ou transferência, nem é garantia de preço na assinatura.
Mesmo sem compute de treino, esses recursos podem ter cobrança. Conferir SKUs,
preço regional e saldo/validade do crédito antes do apply. O orçamento é expresso
na **moeda de cobrança da assinatura**, não se deve presumir USD. É um alerta,
não um teto que interrompe consumo.

O budget do template cobre a assinatura inteira (inclusive outros projetos),
para não deixar de fora custos do resource group gerenciado do Azure ML.
Emite alertas de consumo em 80%/100% e de projeção em 100%. Configurar também
o acompanhamento do crédito no Education Hub/Sponsorships, conforme a oferta:
budget de custo não representa o saldo promocional nem avisa sua expiração.

Após revisar o what-if e aprovar os custos:

```powershell
python -m cloud.azure.manage apply
```

O template cria o budget antes do Registry e não cria VMs, clusters de treino,
endpoints de inferência nem workspace de tracking. O endpoint do Registry fica
acessível pela internet com autenticação Entra/RBAC; os blobs não têm acesso
anônimo. Se a assinatura exigir isolamento por rede privada, revisar a rede
e seus custos antes de aplicar.

## Permissões

Implantação: a identidade precisa criar resource groups, deployments, Registry,
recursos gerenciados, registrar providers e administrar budgets na assinatura.
Verificar essas permissões no preflight e no what-if; não criar access keys.

Publicação posterior: atribuir o papel **AzureML Registry User** somente no
recurso Registry à identidade publicadora, ou papel customizado mais restrito
após testar as operações de upload/download. Leitores recebem Reader no Registry.
Quem aplica a atribuição precisa de roleAssignments/write; Contributor sozinho
não concede essa permissão. Não conceder Owner da assinatura a um job de modelo.

```powershell
# Executar por um administrador RBAC, com IDs reais (nenhuma senha no comando).
.venv-azure/Scripts/python.exe -m azure.cli role assignment create --assignee-object-id PRINCIPAL-ID --assignee-principal-type User --role "AzureML Registry User" --scope REGISTRY-RESOURCE-ID --subscription SUBSCRIPTION-ID
```

Para uma automação futura no GitHub, usar identidade federada OIDC com subject
restrito ao environment de publicação e aprovação nesse environment. Nenhum
segredo de client_credentials é necessário. A primeira publicação pode usar
o login interativo sem adicionar dependência do Airflow/AWS.

## Publicar um modelo real

É possível concluir a primeira publicação antes de ter MLflow/S3 operacionais:
obter do responsável pela VPS o arquivo de modelo já treinado (exemplo: bundle
XGBoost). Não registrar CSV de previsões como se fosse um modelo executável.
O script transfere bytes sem desserializar pickle nem executar treino.

```powershell
python -m cloud.register_azure --subscription SUBSCRIPTION-ID --tenant-id TENANT-ID --registry-name REGISTRY --name risco-sla --version 1 --local-file CAMINHO-DO-BUNDLE.pkl
```

Ou, quando houver um run no tracking existente:

```powershell
# MLFLOW_TRACKING_URI precisa apontar para o servidor real acessível.
python -m cloud.register_azure --subscription SUBSCRIPTION-ID --tenant-id TENANT-ID --registry-name REGISTRY --name risco-sla --version 1 --run-id RUN-ID --artifact-path model/bundle.pkl
```

Nesse modo o ambiente que executa o script precisa também de `mlflow` e das
credenciais do tracking/artefatos; a Azure CLI pode continuar no venv isolado.
O script publica um arquivo por versão como custom_model, grava SHA-256 e
run-id quando houver, recusa substituição de versão com outro hash, baixa o
modelo e verifica o conteúdo. Diretórios de modelo MLflow não estão suportados
por este publicador de arquivo; não enviar um diretório inteiro por engano.

## Verificação e aceite

```powershell
python -m cloud.azure.manage verify
```

Consultar `cloud/evidence/azure/verify.json` (recursos gerenciados, budget,
modelos) e `model.json` (ID, versão, SHA-256 e download verificado). `verify`
retorna erro se não houver modelo publicado. Conferir também no portal:
provisionamento concluído, email correto dos alertas, papel RBAC da identidade
e um modelo real visível com versão e origem. A existência do budget não prova
que um email foi entregue; acompanhar o evento de alerta na assinatura.

Aceite Azure: Registry provisionado na conta correta, custos revisados,
permissões verificadas, budget ativo e um modelo real publicado/baixado íntegro.
Sem assinatura autenticada ou artefato real, a etapa permanece incompleta.

## Retenção e encerramento

Manter cópia independente dos modelos no armazenamento original. Identificar
o grupo gerenciado a partir de `managedResourceGroup.resourceId` no Registry.
Ao encerrar o projeto, revisar retenção e solicitar exclusão explícita dos
recursos deste projeto, verificando que nenhum armazenamento compartilhado é
removido e que não restaram custos. Não há exclusão automática no script.

## Fontes

- [Criação de registries e recursos gerenciados](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-manage-registries?view=azureml-api-2)
- [Schema ARM do Registry](https://learn.microsoft.com/en-us/azure/templates/microsoft.machinelearningservices/2024-04-01/registries)
- [Budgets](https://learn.microsoft.com/en-us/azure/templates/microsoft.consumption/2024-08-01/budgets)
- [Modelos: create/show/download](https://learn.microsoft.com/en-us/cli/azure/ml/model?view=azure-cli-latest)
- [Custos e budgets para estudantes](https://learn.microsoft.com/en-us/azure/education-hub/navigate-costs)
