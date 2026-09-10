import pytest
from cloud.with_secret import environment


def test_segredo_escapa_credenciais_e_exige_tls():
    base = {'PGSSLMODE': 'disable'}
    result = environment({'username': 'a@b', 'password': 'p:/@%',
                          'host': 'db.example', 'dbname': 'fiap'}, base)
    assert result['FIAP_DB_PASSWORD'] == 'p%3A%2F%40%25'
    assert result['PGSSLMODE'] == 'require'
    assert base == {'PGSSLMODE': 'disable'}


def test_segredo_incompleto_falha_fechado():
    with pytest.raises(ValueError):
        environment({'username': 'admin'}, {})
