"""Preflight, what-if, aplicação e evidência do Azure ML Registry."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import uuid

from cloud.azure.cli import assert_account, run

DIRECTORY = Path(__file__).resolve().parent
PROVIDERS = ('Microsoft.MachineLearningServices', 'Microsoft.Storage',
             'Microsoft.ContainerRegistry', 'Microsoft.ManagedIdentity', 'Microsoft.Consumption')


def read_config(path):
    config = json.loads(Path(path).read_text(encoding='utf-8'))
    if any(isinstance(value, str) and 'PREENCHER' in value for value in config.values()):
        raise ValueError('Preencha os valores de exemplo antes de executar.')
    for key in ('subscription_id', 'tenant_id'):
        uuid.UUID(config[key])
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{2,31}', config['registry_name']):
        raise ValueError('Nome do Registry deve ter 3–32 caracteres alfanuméricos, _ ou -.')
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', config['resource_group']):
        raise ValueError('Nome de resource group inválido.')
    if not re.fullmatch(r'[a-z0-9]+', config['location']):
        raise ValueError('Use nome técnico da região, como eastus.')
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', config['alert_email']) or 'PREENCHER' in config['alert_email']:
        raise ValueError('Preencha o email real dos alertas.')
    if type(config['monthly_budget']) is not int or config['monthly_budget'] <= 0:
        raise ValueError('Orçamento deve ser um inteiro positivo na moeda de cobrança.')
    start = datetime.fromisoformat(config['budget_start'].replace('Z', '+00:00'))
    end = datetime.fromisoformat(config['budget_end'].replace('Z', '+00:00'))
    if start.tzinfo is None or end.tzinfo is None or start.day != 1 or end <= start:
        raise ValueError('Datas de orçamento inválidas: início no primeiro dia e fim posterior, com timezone.')
    return config


def parameters(config):
    mapping = {'expectedSubscriptionId': 'subscription_id', 'resourceGroupName': 'resource_group',
               'registryName': 'registry_name', 'location': 'location', 'alertEmail': 'alert_email',
               'monthlyBudget': 'monthly_budget', 'budgetStart': 'budget_start', 'budgetEnd': 'budget_end'}
    return {'$schema': 'https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#',
            'contentVersion': '1.0.0.0',
            'parameters': {name: {'value': config[key]} for name, key in mapping.items()}}


def preflight(config):
    account = assert_account(config['subscription_id'], config['tenant_id'])
    providers = {}
    for namespace in PROVIDERS:
        data = run(['provider', 'show', '--namespace', namespace, '--subscription', account['id']])
        providers[namespace] = data['registrationState']
    return {'account': {key: account[key] for key in ('id', 'name', 'tenantId', 'state')},
            'providers': providers}


def verify(config):
    sub = config['subscription_id']
    registry_id = (f'/subscriptions/{sub}/resourceGroups/{config["resource_group"]}'
                   f'/providers/Microsoft.MachineLearningServices/registries/{config["registry_name"]}')
    registry = run(['resource', 'show', '--ids', registry_id, '--api-version', '2024-04-01', '--subscription', sub])
    budget = run(['rest', '--method', 'get', '--url',
                  f'https://management.azure.com/subscriptions/{sub}/providers/Microsoft.Consumption/budgets/{config["registry_name"]}-monthly?api-version=2024-08-01'])
    resources = run(['resource', 'list', '--subscription', sub, '--resource-group', config['resource_group']])
    managed_id = registry['properties'].get('managedResourceGroup', {}).get('resourceId')
    if managed_id:
        resources += run(['resource', 'list', '--subscription', sub, '--resource-group', managed_id.rsplit('/', 1)[-1]])
    models = run(['ml', 'model', 'list', '--registry-name', config['registry_name'], '--subscription', sub])
    deployment = run(['deployment', 'sub', 'show', '--name', 'locaweb-azure-registry', '--subscription', sub])
    notifications = budget.get('properties', {}).get('notifications', {})
    checks = {
        'deployment_succeeded': deployment['properties']['provisioningState'] == 'Succeeded',
        'registry_location': registry['location'].replace(' ', '').lower() == config['location'],
        'budget_amount': budget['properties']['amount'] == config['monthly_budget'],
        'budget_contacts': all(notifications.get(key, {}).get('enabled') and
                               config['alert_email'] in notifications[key].get('contactEmails', [])
                               for key in ('actual80', 'actual100', 'forecast100')),
        'model_registered': bool(models),
    }
    return {'registry': registry, 'budget': budget, 'resources': resources, 'models': models,
            'checks': checks, 'passed': all(checks.values()),
            'checked_at': datetime.now(timezone.utc).isoformat()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['preflight', 'register-providers', 'plan', 'apply', 'verify'])
    parser.add_argument('--config', default=str(DIRECTORY / 'config.local.json'))
    args = parser.parse_args()
    config = read_config(args.config)
    evidence = DIRECTORY.parent / 'evidence' / 'azure'
    evidence.mkdir(parents=True, exist_ok=True)
    report = preflight(config)
    if args.action == 'preflight':
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    sub = config['subscription_id']
    if args.action == 'register-providers':
        for namespace, status in report['providers'].items():
            if status != 'Registered':
                run(['provider', 'register', '--namespace', namespace, '--subscription', sub, '--wait'], as_json=False)
        return
    if args.action in ('plan', 'apply'):
        missing = [p for p, state in report['providers'].items() if state != 'Registered']
        if missing:
            raise RuntimeError(f'Providers não registrados: {missing}. Execute register-providers.')
        path = evidence / 'parameters.json'
        path.write_text(json.dumps(parameters(config), indent=2), encoding='utf-8')
        result = run(['deployment', 'sub', 'what-if' if args.action == 'plan' else 'create',
                      '--subscription', sub, '--location', config['location'],
                      '--name', 'locaweb-azure-registry', '--template-file', str(DIRECTORY / 'main.bicep'),
                      '--parameters', '@' + str(path)], as_json=True)
    else:
        result = verify(config)
    output = evidence / (args.action + '.json')
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Evidência: {output}')
    if args.action == 'verify' and not result['passed']:
        raise SystemExit('Verificação incompleta: ' + ', '.join(k for k, v in result['checks'].items() if not v))


if __name__ == '__main__':
    main()
