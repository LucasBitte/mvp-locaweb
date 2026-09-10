import pytest
from sqlalchemy import text
from etl.db import get_engine


@pytest.mark.integration
def test_migrations_e_fixture():
    with get_engine().connect() as conn:
        assert conn.execute(text('SELECT COUNT(*) FROM dw.ref_meta_sla_anual')).scalar_one() == 24
        assert conn.execute(text('SELECT COUNT(*) FROM dw.fct_incidentes')).scalar_one() > 0
