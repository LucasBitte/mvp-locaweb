import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

load_dotenv()


def get_engine() -> Engine:
    user = os.environ["FIAP_DB_USER"]
    password = os.environ["FIAP_DB_PASSWORD"]
    host = os.environ["FIAP_DB_HOST"]
    port = os.getenv("FIAP_DB_PORT", "5432")
    database = os.getenv("FIAP_DB_NAME", "fiap")
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
    return create_engine(url, pool_pre_ping=True)
