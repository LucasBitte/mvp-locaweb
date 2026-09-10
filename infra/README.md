# Infraestrutura

Procedimento completo, orçamento, dependências e limitações em
[`cloud/README.md`](../cloud/README.md). Este diretório não implica que os
recursos foram aplicados.

Validar sem credenciais e sem backend:

```sh
python -m pip download --no-deps --only-binary=:all: python-dotenv==1.0.1 -d infra/.artifacts
terraform -chdir=infra init -backend=false
terraform -chdir=infra fmt -check -recursive
terraform -chdir=infra validate
```

Aplicações usam obrigatoriamente o backend S3 configurado por `backend.hcl`.
Nunca remover o bloco backend para contornar erro de configuração.
