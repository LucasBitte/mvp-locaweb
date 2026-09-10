FROM apache/airflow:2.10.5-python3.11
USER root
RUN apt-get update && apt-get install -y --no-install-recommends git libgomp1 && rm -rf /var/lib/apt/lists/*
USER airflow
COPY requirements-notebooks.txt /tmp/requirements-notebooks.txt
# Runtime de treino isolado das dependências do scheduler Airflow.
RUN python -m venv /opt/airflow/pipeline-venv && /opt/airflow/pipeline-venv/bin/pip install --no-cache-dir -r /tmp/requirements-notebooks.txt boto3==1.40.70
ENV PYTHONPATH=/opt/project
