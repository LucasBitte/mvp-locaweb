"""Aplica as migrations existentes, sem reescrever DDL ou apagar dados."""
from pathlib import Path

from etl.db import get_engine


def main():
    engine = get_engine()
    with engine.begin() as conn:
        conn.exec_driver_sql("SELECT pg_advisory_xact_lock(472601)")
        for path in sorted(Path("db/migrations").glob("*.sql")):
            conn.exec_driver_sql(path.read_text(encoding="utf-8"))
            print(path.name)
    engine.dispose()


if __name__ == "__main__":
    main()
