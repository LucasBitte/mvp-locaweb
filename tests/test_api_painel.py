from fastapi.testclient import TestClient

from app.api.main import app
from etl.db import get_engine
from sqlalchemy import text

client = TestClient(app)


def test_painel_todas_prioridades():
    r = client.get("/api/painel")
    assert r.status_code == 200
    body = r.json()

    engine = get_engine()
    with engine.connect() as conn:
        origem = conn.execute(text("SELECT MAX(origem) FROM ml.fct_previsao_diaria_total")).scalar_one()
        yhat_d1 = conn.execute(
            text("SELECT yhat FROM ml.fct_previsao_diaria_total WHERE origem = :o AND horizonte = 'D+1'"),
            {"o": origem},
        ).scalar_one()

    assert body["previsao_d1"]["valor"] == round(float(yhat_d1))
    assert body["metodologia"] is None
    assert len(body["serie"]) == 30 + 7
    assert sum(1 for p in body["serie"] if p["tipo"] == "historico") == 30
    assert sum(1 for p in body["serie"] if p["tipo"] == "previsao") == 7
    assert body["risco_ola"]["nivel"] in {"baixo", "medio", "alto"}


def test_painel_prioridade_filtrada_marca_metodologia():
    r = client.get("/api/painel", params={"prioridade": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["previsao_d1"]["metodologia"] == "proporcao_historica"
    assert body["previsao_d1"]["share_historico"] is not None
    for ponto in body["serie"]:
        if ponto["tipo"] == "previsao":
            assert ponto["metodologia"] == "proporcao_historica"
            assert ponto["share_historico"] is not None


def test_painel_pressao_equipes_cobre_todas_as_equipes():
    r = client.get("/api/painel")
    body = r.json()
    engine = get_engine()
    with engine.connect() as conn:
        n_equipes = conn.execute(text("SELECT COUNT(*) FROM dw.dim_grupo")).scalar_one()
    assert len(body["pressao_equipes"]) == n_equipes
    pcts = [p["pressao_relativa_pct"] for p in body["pressao_equipes"]]
    assert pcts == sorted(pcts, reverse=True)
    for equipe in body["pressao_equipes"]:
        assert equipe["nivel_pressao"] in {"normal", "atencao", "critico"}
