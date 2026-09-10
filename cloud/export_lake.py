"""Glue Python Shell 3.9: snapshot consistente RDS -> lake, sem Spark."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from urllib.parse import quote
import uuid


def main():
    import boto3
    import pandas as pd
    from sqlalchemy import inspect, text
    parser = argparse.ArgumentParser()
    parser.add_argument('--bucket', required=True)
    parser.add_argument('--secret-id', required=True)
    args, _ = parser.parse_known_args()
    s3 = boto3.client('s3')
    secret = json.loads(boto3.client('secretsmanager').get_secret_value(
        SecretId=args.secret_id)['SecretString'])
    for suffix, key in [('USER', 'username'), ('PASSWORD', 'password'), ('HOST', 'host'),
                        ('PORT', 'port'), ('NAME', 'dbname')]:
        value = str(secret.get(key, 5432) if key == 'port' else secret[key])
        os.environ[f'FIAP_DB_{suffix}'] = quote(value, safe='') if suffix in ('USER', 'PASSWORD') else value
    os.environ['PGSSLMODE'] = 'require'
    run = datetime.now(timezone.utc).strftime('%Y-%m-%d') + '/' + str(uuid.uuid4())
    manifest = {'run': run, 'tables': {}}
    with tempfile.TemporaryDirectory() as tmp:
        # O módulo de conexão é o próprio etl/db.py versionado no repo.
        # Wheel puro Python no S3: instala sem depender de internet/NAT.
        wheel = str(Path(tmp) / 'python_dotenv-1.0.1-py3-none-any.whl')
        s3.download_file(args.bucket, 'jobs/python_dotenv-1.0.1-py3-none-any.whl', wheel)
        sys.path.insert(0, wheel)
        db_file = str(Path(tmp) / 'db.py')
        s3.download_file(args.bucket, 'jobs/db.py', db_file)
        spec = importlib.util.spec_from_file_location('etl_db', db_file)
        db = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(db)
        engine = db.get_engine()
        try:
            with engine.connect().execution_options(isolation_level='REPEATABLE READ') as conn:
                with conn.begin():
                    conn.execute(text('SET TRANSACTION READ ONLY'))
                    conn.execute(text("SET TIME ZONE 'UTC'"))
                    for schema, layer in [('public', 'bronze'), ('staging', 'silver'), ('dw', 'gold'), ('ml', 'gold')]:
                        for table in inspect(conn).get_table_names(schema=schema):
                            if schema == 'public' and table != 'incidentes':
                                continue
                            q = conn.dialect.identifier_preparer.quote
                            df = pd.read_sql_query(text(f'SELECT * FROM {q(schema)}.{q(table)}'), conn)
                            local = Path(tmp) / 'part.parquet'
                            df.to_parquet(local, index=False)
                            day, run_id = run.split('/')
                            key = f'{layer}/{schema}/{table}/snapshot_date={day}/run_id={run_id}/part.parquet'
                            s3.upload_file(str(local), args.bucket, key)
                            manifest['tables'][f'{schema}.{table}'] = {'rows': len(df), 'key': key}
            # Publicação atômica do manifesto somente após todas as tabelas.
            s3.put_object(Bucket=args.bucket, Key=f'manifests/{run}.json',
                          Body=json.dumps(manifest).encode(), ContentType='application/json')
        finally:
            engine.dispose()


if __name__ == '__main__':
    main()
