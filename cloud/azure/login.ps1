# Execute no seu terminal; login e MFA acontecem na página da Microsoft.
param([string]$TenantId)
$ErrorActionPreference = 'Stop'
$projectDir = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$azurePython = Join-Path $projectDir '.venv-azure\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $azurePython)) {
    throw 'Instale primeiro: python -m uv venv .venv-azure; python -m uv pip install --python .venv-azure/Scripts/python.exe -r cloud/azure/requirements-tools.txt --prerelease=allow'
}
$loginArgs = @('-m', 'azure.cli', 'login', '--use-device-code')
if ($TenantId) { $loginArgs += @('--tenant', $TenantId) }
& $azurePython @loginArgs
if ($LASTEXITCODE -ne 0) { throw 'Login Azure não concluído.' }
& $azurePython -m azure.cli account list --query '[].{Assinatura:name,Id:id,Tenant:tenantId,Estado:state}' --output table
if ($LASTEXITCODE -ne 0) { throw 'Não foi possível listar assinaturas.' }
