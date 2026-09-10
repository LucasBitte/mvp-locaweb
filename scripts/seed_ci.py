"""Fixture sintético, permitido exclusivamente em banco efêmero *_ci."""
import os

from sqlalchemy import MetaData, Table, Boolean, Date, DateTime, Numeric, Integer
from datetime import date, datetime

from etl.db import get_engine


def main():
    if os.getenv("CI") != "true" or not os.getenv("FIAP_DB_NAME", "").endswith("_ci"):
        raise RuntimeError("Fixture permitido somente com CI=true e banco *_ci")
    engine = get_engine()
    names = [
        *(('dw', f'dim_{n}') for n in (
            'produto_categoria', 'grupo', 'tempo', 'status', 'prioridade', 'abertura')),
        ('dw', 'fct_incidentes'), ('ml', 'ml_base_features'),
        ('ml', 'ml_cluster_dataset'), ('ml', 'ml_sla_classification_dataset'),
    ]
    with engine.begin() as conn:
        for schema, name in names:
            table = Table(name, MetaData(), schema=schema, autoload_with=conn)
            values = {}
            for col in table.columns:
                if col.nullable:
                    continue
                if isinstance(col.type, Boolean):
                    value = True
                elif isinstance(col.type, DateTime):
                    value = datetime(2025, 1, 2, 10)
                elif isinstance(col.type, Date):
                    value = date(2025, 1, 2)
                elif isinstance(col.type, (Integer, Numeric)):
                    value = 1
                else:
                    value = 'ci'
                values[col.name] = value
            conn.execute(table.insert().values(**values))
    engine.dispose()


if __name__ == '__main__':
    main()
