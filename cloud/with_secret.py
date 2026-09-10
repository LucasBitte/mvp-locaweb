"""Injeta segredo apenas no processo filho; nenhum .env é gravado."""
import argparse
import json
import os
import subprocess
from urllib.parse import quote


def environment(secret, base=None):
    env = dict(os.environ if base is None else base)
    if any(not secret.get(k) for k in ('username', 'password', 'host', 'dbname')):
        raise ValueError('Segredo requer username, password, host e dbname')
    env.update({
        'FIAP_DB_USER': quote(secret['username'], safe=''),
        'FIAP_DB_PASSWORD': quote(secret['password'], safe=''),
        'FIAP_DB_HOST': secret['host'],
        'FIAP_DB_PORT': str(secret.get('port', 5432)),
        'FIAP_DB_NAME': secret['dbname'],
        'PGSSLMODE': 'require',
        'DBT_DB_USER': secret['username'],
        'DBT_DB_PASSWORD': secret['password'],
    })
    return env


def main():
    import boto3
    parser = argparse.ArgumentParser()
    parser.add_argument('--secret-id', default=os.getenv('FIAP_DB_SECRET_ID'))
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not args.secret_id or not command:
        parser.error('informe FIAP_DB_SECRET_ID e comando após --')
    secret = json.loads(boto3.client('secretsmanager').get_secret_value(
        SecretId=args.secret_id)['SecretString'])
    raise SystemExit(subprocess.call(command, env=environment(secret)))


if __name__ == '__main__':
    main()
