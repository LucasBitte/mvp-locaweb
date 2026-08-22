import pytest

from etl.db import get_engine
from etl.ref_meta_sla import faixa_meta_sla


@pytest.fixture(scope="module")
def engine():
    return get_engine()


def test_faixa_inicial_melhor_atingimento(engine):
    faixa = faixa_meta_sla(engine, prioridade_num=2, indicador="ola_quebrado", contagem_acumulada=0)
    assert faixa["ordem_faixa"] == 1
    assert faixa["pct_atingimento"] == 150


def test_faixa_limite_superior_da_primeira_banda(engine):
    # faixa_max=30 na primeira banda ("< 31") -- 30 ainda cai nela, 31 não.
    faixa = faixa_meta_sla(engine, prioridade_num=2, indicador="ola_quebrado", contagem_acumulada=30)
    assert faixa["ordem_faixa"] == 1

    faixa = faixa_meta_sla(engine, prioridade_num=2, indicador="ola_quebrado", contagem_acumulada=31)
    assert faixa["ordem_faixa"] == 2


def test_faixa_pior_atingimento_zero_por_cento(engine):
    faixa = faixa_meta_sla(engine, prioridade_num=2, indicador="ola_quebrado", contagem_acumulada=54)
    assert faixa["ordem_faixa"] == 6
    assert faixa["pct_atingimento"] == 0


def test_faixa_aberta_no_topo_cobre_qualquer_valor_alto(engine):
    faixa = faixa_meta_sla(engine, prioridade_num=2, indicador="ola_quebrado", contagem_acumulada=999_999)
    assert faixa["ordem_faixa"] == 6


def test_p3_volume_tratado_faixa_intermediaria(engine):
    faixa = faixa_meta_sla(engine, prioridade_num=3, indicador="volume_tratado", contagem_acumulada=22200)
    assert faixa["ordem_faixa"] == 3
    assert faixa["pct_atingimento"] == 100


def test_indicador_invalido_leva_a_value_error(engine):
    with pytest.raises(ValueError):
        faixa_meta_sla(engine, prioridade_num=2, indicador="inexistente", contagem_acumulada=0)


def test_contagem_negativa_leva_a_value_error(engine):
    with pytest.raises(ValueError):
        faixa_meta_sla(engine, prioridade_num=2, indicador="ola_quebrado", contagem_acumulada=-1)


def test_prioridade_sem_meta_definida_leva_a_lookup_error(engine):
    # Só P2/P3 têm meta anual definida -- P1/P4/P5 não têm faixa cadastrada.
    with pytest.raises(LookupError):
        faixa_meta_sla(engine, prioridade_num=1, indicador="ola_quebrado", contagem_acumulada=0)
