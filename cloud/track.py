"""Tracking externo ao treino: preserva comando, sementes e hiperparâmetros."""
import argparse
import os
from pathlib import Path
import subprocess
import time

from cloud.pipeline import STEPS


def main():
    import mlflow
    parser = argparse.ArgumentParser()
    parser.add_argument('step', choices=STEPS)
    args = parser.parse_args()
    if not os.getenv('MLFLOW_TRACKING_URI'):
        parser.error('MLFLOW_TRACKING_URI obrigatório: não criar backend local por acidente')
    mlflow.set_experiment('locaweb-pipeline')
    command = STEPS[args.step][0]
    before = {str(p): p.stat().st_mtime_ns for p in Path('data/ml').rglob('*') if p.is_file()}
    with mlflow.start_run(run_name=args.step):
        mlflow.set_tag('git_commit', subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip())
        mlflow.set_tag('airflow_run', os.getenv('AIRFLOW_CTX_DAG_RUN_ID', 'manual'))
        mlflow.log_param('command', ' '.join(command))
        start = time.monotonic()
        subprocess.run(command, check=True)
        mlflow.log_metric('duration_seconds', time.monotonic() - start)
        for path in Path('data/ml').rglob('*'):
            if path.is_file() and before.get(str(path)) != path.stat().st_mtime_ns:
                mlflow.log_artifact(str(path), artifact_path=str(path.parent.relative_to('data/ml')))
        # Métricas já calculadas pelo Prophet, sem reavaliar nem arredondar.
        if args.step == 'forecast_total':
            import pandas as pd
            for file in Path('data/ml').rglob('metricas_avaliacao_final.csv'):
                if before.get(str(file)) == file.stat().st_mtime_ns:
                    continue
                for row in pd.read_csv(file).to_dict('records'):
                    model = str(row.pop('modelo'))
                    for metric, value in row.items():
                        if isinstance(value, (float, int)):
                            mlflow.log_metric(f'{model}/{metric}', value)
        if args.step == 'diagnostico':
            import pandas as pd
            path = Path('data/ml/kmeans/diagnostico_k_2_a_8.csv')
            if path.exists() and before.get(str(path)) != path.stat().st_mtime_ns:
                for row in pd.read_csv(path).to_dict('records'):
                    k = int(row.pop('k'))
                    for metric, value in row.items():
                        if isinstance(value, (float, int)):
                            mlflow.log_metric(f'k_{k}/{metric}', value)


if __name__ == '__main__':
    main()
