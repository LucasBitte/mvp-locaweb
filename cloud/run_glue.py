"""Airflow só conclui após o Glue terminar com sucesso."""
import os
import time


def main():
    import boto3
    client = boto3.client('glue')
    name = os.environ['GLUE_JOB_NAME']
    run_id = client.start_job_run(JobName=name)['JobRunId']
    deadline = time.monotonic() + 2400
    while time.monotonic() < deadline:
        state = client.get_job_run(JobName=name, RunId=run_id)['JobRun']['JobRunState']
        if state == 'SUCCEEDED':
            break
        if state in {'FAILED', 'STOPPED', 'TIMEOUT', 'ERROR', 'EXPIRED'}:
            raise RuntimeError(f'Glue {run_id}: {state}')
        time.sleep(30)
    else:
        raise TimeoutError(f'Glue {run_id} excedeu 40 minutos; verificar antes de repetir')
    crawler = os.environ.get('GLUE_CRAWLER_NAME', 'locaweb-lake')
    client.start_crawler(Name=crawler)
    deadline = time.monotonic() + 1800
    while time.monotonic() < deadline:
        status = client.get_crawler(Name=crawler)['Crawler']
        if status['State'] == 'READY':
            if status.get('LastCrawl', {}).get('Status') != 'SUCCEEDED':
                raise RuntimeError('Crawler não concluiu com sucesso')
            return
        time.sleep(30)
    raise TimeoutError('Crawler excedeu 30 minutos')


if __name__ == '__main__':
    main()
