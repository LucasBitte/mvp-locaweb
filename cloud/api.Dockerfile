FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt boto3==1.40.70
COPY etl etl
COPY app/api app/api
COPY app/__init__.py app/__init__.py
COPY cloud/__init__.py cloud/with_secret.py cloud/
EXPOSE 8000
CMD ["python", "-m", "cloud.with_secret", "--", "python", "-m", "uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
