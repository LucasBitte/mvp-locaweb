import pandas as pd

from etl.transform import aplicar_silver, md5_key


def _linha_base(**overrides):
    base = dict(
        numero="INC1",
        prioridade="2 - Alta",
        produto="lhco",
        categoria="cat1",
        subcategoria="sub1",
        grupo_designado="Team01",
        item_configuracao="IC001",
        aberto=pd.Timestamp("2025-06-01 10:00:00"),
        resolvido=pd.Timestamp("2025-06-01 12:00:00"),
        encerrado=pd.Timestamp("2025-06-01 13:00:00"),
        duracao_min=180,
        codigo_fechamento="Falha de Aplicação",
        descricao_resumida="teste",
        solucao=None,
        aberto_por="Manual",
        incidente_pai=None,
        status="Encerrado",
        entrou_kpi=True,
        kpi_violado=False,
    )
    base.update(overrides)
    return base


def test_md5_key_determinismo():
    assert md5_key("a", "b") == md5_key("a", "b")
    assert md5_key("a", "b") != md5_key("b", "a")


def test_filtra_sem_intervencao():
    df = pd.DataFrame(
        [
            _linha_base(numero="INC1", status="Sem Intervenção"),
            _linha_base(numero="INC2", status="Encerrado"),
        ]
    )
    out = aplicar_silver(df)
    assert list(out["numero"]) == ["INC2"]


def test_filtra_antes_de_2025():
    df = pd.DataFrame(
        [
            _linha_base(numero="INC1", aberto=pd.Timestamp("2024-12-31")),
            _linha_base(numero="INC2", aberto=pd.Timestamp("2025-01-01")),
        ]
    )
    out = aplicar_silver(df)
    assert list(out["numero"]) == ["INC2"]


def test_kpi_status_int_isento_quando_nao_entrou_kpi():
    df = pd.DataFrame([_linha_base(entrou_kpi=False, kpi_violado=None)])
    out = aplicar_silver(df)
    assert out["kpi_status_int"].iloc[0] == -1


def test_target_risco_sla_heuristica_p2_acima_de_8h():
    df = pd.DataFrame(
        [_linha_base(entrou_kpi=False, kpi_violado=None, prioridade="2 - Alta", duracao_min=9 * 60)]
    )
    out = aplicar_silver(df)
    assert out["target_risco_sla"].iloc[0] == 1


def test_target_risco_sla_isencao_incidente_filho():
    df = pd.DataFrame(
        [_linha_base(entrou_kpi=True, kpi_violado=True, incidente_pai="INC0")]
    )
    out = aplicar_silver(df)
    assert out["possui_pai"].iloc[0] is True or bool(out["possui_pai"].iloc[0])
    assert out["target_risco_sla"].iloc[0] == 0


def test_fechado_sem_tecnico_vocabulario_local_sempre_false():
    df = pd.DataFrame(
        [_linha_base(codigo_fechamento="Sem retorno do solicitante")]
    )
    out = aplicar_silver(df)
    assert bool(out["fechado_sem_tecnico"].iloc[0]) is False
