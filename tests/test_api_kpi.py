from fastapi.testclient import TestClient

from app.api.main import app
from etl.db import get_engine
from sqlalchemy import text

client = TestClient(app)


def test_kpi_tem_exatamente_quatro_indicadores():
    r = client.get("/api/kpi")
    assert r.status_code == 200
    body = r.json()
    combos = {(i["prioridade_num"], i["indicador"]) for i in body["indicadores"]}
    assert combos == {(2, "ola_quebrado"), (2, "volume_tratado"), (3, "ola_quebrado"), (3, "volume_tratado")}


def test_kpi_contagem_bate_com_dw_fct_incidentes():
    r = client.get("/api/kpi")
    body = r.json()
    ano = body["ano"]
    engine = get_engine()
    with engine.connect() as conn:
        for item in body["indicadores"]:
            if item["indicador"] == "ola_quebrado":
                esperado = conn.execute(
                    text(
                        """
                        SELECT COUNT(*) FROM dw.fct_incidentes fi
                        JOIN dw.dim_prioridade dp ON fi.dim_prioridade_sk = dp.dim_prioridade_sk
                        JOIN dw.dim_tempo dt ON fi.dim_tempo_sk = dt.dim_tempo_sk
                        WHERE dp.prioridade_num = :p AND dt.ano = :ano AND fi.kpi_status_int = 1
                        """
                    ),
                    {"p": item["prioridade_num"], "ano": ano},
                ).scalar_one()
            else:
                esperado = conn.execute(
                    text(
                        """
                        SELECT COUNT(*) FROM dw.fct_incidentes fi
                        JOIN dw.dim_prioridade dp ON fi.dim_prioridade_sk = dp.dim_prioridade_sk
                        JOIN dw.dim_tempo dt ON fi.dim_tempo_sk = dt.dim_tempo_sk
                        WHERE dp.prioridade_num = :p AND dt.ano = :ano
                        """
                    ),
                    {"p": item["prioridade_num"], "ano": ano},
                ).scalar_one()
            assert item["contagem_acumulada_ano"] == esperado


def test_kpi_status_derivado_so_do_observado():
    r = client.get("/api/kpi")
    body = r.json()
    for item in body["indicadores"]:
        pct = item["faixa"]["pct_atingimento"]
        if pct >= 100:
            assert item["status"] == "dentro_da_meta"
        elif pct >= 50:
            assert item["status"] == "atencao"
        else:
            assert item["status"] == "critico"
        assert item["metodologia_probabilidade"] == "projecao_linear"


def test_kpi_nunca_expoe_metrica_de_modelo():
    r = client.get("/api/kpi")
    payload_str = r.text.lower()
    for termo_proibido in ["roc-auc", "roc_auc", "pr-auc", "pr_auc", "brier", "silhouette"]:
        assert termo_proibido not in payload_str
