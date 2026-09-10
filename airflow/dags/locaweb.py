"""DAG manual até concluir dual-run; nenhum catchup ou retentativa de append."""
from datetime import datetime, timezone
import os

from airflow import DAG
from airflow.operators.bash import BashOperator
from cloud.pipeline import STEPS

with DAG('locaweb_pipeline', start_date=datetime(2026, 9, 10, tzinfo=timezone.utc),
         schedule=None, catchup=False, max_active_runs=1, max_active_tasks=1,
         default_args={'retries': 0}, tags=['locaweb']) as dag:
    tasks = {}
    for name in STEPS:
        tasks[name] = BashOperator(
            task_id=name,
            bash_command=f'/opt/airflow/pipeline-venv/bin/python -m cloud.with_secret -- /opt/airflow/pipeline-venv/bin/python -m cloud.track {name}',
            cwd='/opt/project',
        )
    for name, (_, upstream) in STEPS.items():
        for dependency in upstream:
            tasks[dependency] >> tasks[name]
    export = BashOperator(
        task_id='export_lake',
        bash_command='/opt/airflow/pipeline-venv/bin/python -m cloud.run_glue', cwd='/opt/project',
        env={'GLUE_JOB_NAME': os.environ.get('GLUE_JOB_NAME', 'locaweb-rds-to-s3')},
        append_env=True,
    )
    for task in tasks.values():
        task >> export
