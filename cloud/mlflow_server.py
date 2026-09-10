"""Backend MLflow isolado no RDS, artefatos via proxy em S3."""
import json
import os
import subprocess
from urllib.parse import quote


def main():
    import boto3
    secret = json.loads(boto3.client('secretsmanager').get_secret_value(
        SecretId=os.environ['MLFLOW_DB_SECRET_ID'])['SecretString'])
    url = ('postgresql+psycopg2://' + quote(secret['username'], safe='') + ':'
           + quote(secret['password'], safe='') + '@' + secret['host'] + ':'
           + str(secret.get('port', 5432)) + '/' + secret['dbname'] + '?sslmode=require')
    # URI somente no ambiente do processo, nunca em linha de comando/log.
    env = dict(os.environ, MLFLOW_BACKEND_STORE_URI=url)
    subprocess.run(['mlflow', 'server', '--host', '0.0.0.0', '--port', '5000',
                    '--serve-artifacts', '--artifacts-destination',
                    f"s3://{os.environ['LAKE_BUCKET']}/mlflow",
                    '--allowed-hosts', os.environ['MLFLOW_ALLOWED_HOSTS']], env=env, check=True)


if __name__ == '__main__':
    main()
