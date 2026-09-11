import json
from pathlib import Path

import pytest

from cloud.azure.manage import parameters, read_config
from cloud.azure.cli import assert_account
from cloud.register_azure import digest, publish, validate_artifact


def config():
    return {'subscription_id': '11111111-1111-1111-1111-111111111111',
            'tenant_id': '22222222-2222-2222-2222-222222222222',
            'resource_group': 'rg-locaweb-ml', 'registry_name': 'locaweb-test',
            'location': 'eastus', 'alert_email': 'owner@example.com', 'monthly_budget': 10,
            'budget_start': '2026-09-01T00:00:00Z', 'budget_end': '2026-12-01T00:00:00Z'}


@pytest.mark.parametrize('key,value', [('monthly_budget', -1), ('monthly_budget', True),
                                      ('subscription_id', 'invalid'), ('alert_email', 'missing'),
                                      ('budget_end', '2026-08-01T00:00:00Z')])
def test_config_invalida_recusada(tmp_path, key, value):
    value_config = config()
    value_config[key] = value
    path = tmp_path / 'config.json'
    path.write_text(json.dumps(value_config))
    with pytest.raises(ValueError):
        read_config(path)


def test_contexto_assinatura_explicito():
    assert parameters(config())['parameters']['expectedSubscriptionId']['value'] == config()['subscription_id']


def test_tenant_incorreto_interrompe_operacao(monkeypatch):
    monkeypatch.setattr('cloud.azure.cli.run', lambda args: {'id': 'sub', 'state': 'Enabled', 'tenantId': 'outro'})
    with pytest.raises(RuntimeError, match='Tenant'):
        assert_account('sub', 'esperado')


@pytest.mark.parametrize('path', ['../data.csv', '/secrets', 'model/../../secret', 'C:\\secret'])
def test_artifact_nao_escapa_run(path):
    with pytest.raises(ValueError):
        validate_artifact(path)


def test_versao_existente_nao_sobrescrita(tmp_path, monkeypatch):
    artifact = tmp_path / 'model.pkl'
    artifact.write_bytes(b'model bytes')
    monkeypatch.setattr('cloud.register_azure.run', lambda *args, **kw: [{'version': '1', 'tags': {'sha256': 'different'}}])
    with pytest.raises(ValueError, match='outro conteúdo'):
        publish(artifact, subscription='sub', registry='reg', name='model', version='1')


def test_publicacao_verifica_download(tmp_path, monkeypatch):
    artifact = tmp_path / 'model.pkl'
    artifact.write_bytes(b'model bytes')
    calls = []
    def fake_run(args, **kwargs):
        calls.append(args)
        if args[:3] == ['ml', 'model', 'list']:
            return []
        if args[:3] == ['ml', 'model', 'show']:
            return {'id': 'azureml://registries/reg/models/model/versions/1', 'tags': {'sha256': digest(artifact)}}
        if args[:3] == ['ml', 'model', 'download']:
            Path(args[args.index('--download-path') + 1], 'model.pkl').write_bytes(artifact.read_bytes())
    monkeypatch.setattr('cloud.register_azure.run', fake_run)
    result = publish(artifact, subscription='sub', registry='reg', name='model', version='1')
    assert result['download_verified']
    assert all('--subscription' in call for call in calls)
