"""Azure CLI com contexto explícito e sem shell/interpolação de credenciais."""
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def command():
    configured = os.getenv('AZURE_CLI_PYTHON')
    if configured:
        return [configured, '-m', 'azure.cli']
    local = ROOT / '.venv-azure' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if local.is_file():
        return [str(local), '-m', 'azure.cli']
    binary = shutil.which('az')
    if binary:
        return [binary]
    raise RuntimeError('Instale Azure CLI ou configure AZURE_CLI_PYTHON.')


def run(args, *, as_json=True):
    result = subprocess.run(command() + list(args) +
                            (['--output', 'json', '--only-show-errors'] if as_json else []),
                            check=True, text=True, capture_output=as_json)
    return json.loads(result.stdout) if as_json and result.stdout.strip() else None


def assert_account(subscription, tenant=None):
    account = run(['account', 'show', '--subscription', subscription])
    if account['id'].lower() != subscription.lower() or account.get('state') != 'Enabled':
        raise RuntimeError('Assinatura não corresponde à configuração ou não está ativa.')
    if tenant and account['tenantId'].lower() != tenant.lower():
        raise RuntimeError('Tenant diferente do configurado.')
    return account
