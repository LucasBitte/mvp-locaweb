# Execute pessoalmente em um terminal. Nunca cole credenciais no chat.
$ErrorActionPreference = 'Stop'
$awsPython = Join-Path $env:APPDATA 'uv\tools\awscli\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $awsPython)) {
    throw 'AWS CLI isolada não encontrada. Instale com: python -m uv tool install awscli'
}
& $awsPython -m awscli configure --profile locaweb
if ($LASTEXITCODE -ne 0) { throw 'Configuração AWS não concluída.' }
& $awsPython -m awscli configure set region sa-east-1 --profile locaweb
& $awsPython -m awscli sts get-caller-identity --profile locaweb
if ($LASTEXITCODE -ne 0) { throw 'Não foi possível autenticar o perfil locaweb.' }
