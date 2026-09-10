"""Promove artefato de um run ao Azure ML Registry; nunca executa treino."""
import argparse
import subprocess
import tempfile


def main():
    import mlflow
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--artifact-path', required=True)
    parser.add_argument('--registry-name', required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--version', required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        path = mlflow.artifacts.download_artifacts(
            artifact_uri=f'runs:/{args.run_id}/{args.artifact_path}', dst_path=tmp)
        subprocess.run(['az', 'ml', 'model', 'create', '--registry-name', args.registry_name,
                        '--name', args.name, '--version', args.version, '--type', 'custom_model',
                        '--path', path, '--tags', f'mlflow_run_id={args.run_id}'], check=True)


if __name__ == '__main__':
    main()
