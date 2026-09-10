FROM python:3.11-slim
WORKDIR /opt/project
COPY cloud/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY cloud/__init__.py cloud/mlflow_server.py cloud/
CMD ["python", "-m", "cloud.mlflow_server"]
