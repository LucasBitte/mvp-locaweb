"""Publica arquivo de modelo com checksum e verifica cópia baixada do Azure."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile

from cloud.azure.cli import assert_account, run


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def validate_artifact(path):
    artifact = PurePosixPath(path)
    if artifact.is_absolute() or '..' in artifact.parts or '\\' in path or ':' in path or not artifact.name:
        raise ValueError('artifact-path deve ser relativo à raiz do run e não conter ..')


def publish(path, *, subscription, registry, name, version, run_id=None):
    source = Path(path)
    if not source.is_file() or source.is_symlink():
        raise ValueError('Informe um arquivo de modelo real, não diretório ou link.')
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,254}', name):
        raise ValueError('Nome de modelo inválido.')
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}', version):
        raise ValueError('Versão de modelo inválida.')
    checksum = digest(source)
    scope = ['--registry-name', registry, '--subscription', subscription]
    existing = run(['ml', 'model', 'list', '--name', name, '--include-archived', *scope])
    match = next((model for model in existing if str(model.get('version')) == version), None)
    if match and match.get('tags', {}).get('sha256') != checksum:
        raise ValueError('Versão já existe com outro conteúdo; escolha uma nova versão.')
    if not match:
        tags = [f'sha256={checksum}', 'project=mvp-locaweb']
        if run_id:
            tags.append(f'mlflow_run_id={run_id}')
        run(['ml', 'model', 'create', '--name', name, '--version', version,
             '--type', 'custom_model', '--path', str(source.resolve()), '--tags', *tags, *scope])
    model = run(['ml', 'model', 'show', '--name', name, '--version', version, *scope])
    if model.get('tags', {}).get('sha256') != checksum:
        raise RuntimeError('Checksum registrado no Azure não corresponde ao arquivo.')
    with tempfile.TemporaryDirectory() as tmp:
        run(['ml', 'model', 'download', '--name', name, '--version', version,
             '--download-path', tmp, *scope], as_json=False)
        verified = any(digest(p) == checksum for p in Path(tmp).rglob('*') if p.is_file())
        if not verified:
            raise RuntimeError('Download do Azure não contém o arquivo publicado com checksum correto.')
    return {'model_id': model['id'], 'name': name, 'version': version,
            'registry': registry, 'subscription': subscription, 'sha256': checksum,
            'mlflow_run_id': run_id, 'download_verified': True}


def main():
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--run-id')
    source.add_argument('--local-file')
    parser.add_argument('--artifact-path')
    parser.add_argument('--subscription', required=True)
    parser.add_argument('--tenant-id')
    parser.add_argument('--registry-name', required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--output', default='cloud/evidence/azure/model.json')
    args = parser.parse_args()
    if args.run_id and (not args.artifact_path or not os.getenv('MLFLOW_TRACKING_URI')):
        parser.error('Run requer --artifact-path e MLFLOW_TRACKING_URI do servidor real.')
    if args.local_file and args.artifact_path:
        parser.error('--artifact-path só se aplica a --run-id.')
    if args.artifact_path:
        validate_artifact(args.artifact_path)
    assert_account(args.subscription, args.tenant_id)
    with tempfile.TemporaryDirectory() as tmp:
        if args.run_id:
            import mlflow
            path = mlflow.artifacts.download_artifacts(
                artifact_uri=f'runs:/{args.run_id}/{args.artifact_path}', dst_path=tmp)
        else:
            source_file = Path(args.local_file)
            if not source_file.is_file() or source_file.is_symlink():
                parser.error('--local-file deve apontar para um arquivo regular.')
            path = shutil.copy2(source_file, Path(tmp) / source_file.name)
        report = publish(path, subscription=args.subscription, registry=args.registry_name,
                         name=args.name, version=args.version, run_id=args.run_id)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(f'Modelo registrado e download verificado. Evidência: {output}')


if __name__ == '__main__':
    main()
