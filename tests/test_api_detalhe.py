from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)


def test_detalhe_categoria_default():
    r = client.get("/api/detalhe")
    assert r.status_code == 200
    body = r.json()
    assert body["agrupamento"] == "categoria"
    assert len(body["top_entidades"]) <= 5
    for prio in body["prioridades"]:
        assert prio["is_placeholder_limite"] is True
        assert prio["pct_limite_mensal"] is None
        assert prio["metodologia"] == "proporcao_historica"
    for ent in body["top_entidades"]:
        assert ent["metodologia"] == "proporcao_historica"
    valores = [e["yhat"] for e in body["top_entidades"]]
    assert valores == sorted(valores, reverse=True)


def test_detalhe_agrupamento_produto():
    r = client.get("/api/detalhe", params={"agrupamento": "produto"})
    assert r.status_code == 200
    body = r.json()
    assert body["agrupamento"] == "produto"
    assert body["recorrencia"]["granularidade"] == "produto"


def test_detalhe_threshold_sla_vem_de_dim_prioridade():
    r = client.get("/api/detalhe")
    body = r.json()
    thresholds = {p["prioridade_num"]: p["threshold_sla_horas"] for p in body["prioridades"]}
    assert thresholds[2] == 4
    assert thresholds[3] == 12


def test_detalhe_recorrencia_exclui_status_irrelevantes():
    r = client.get("/api/detalhe")
    body = r.json()
    status_proibidos = {"volume_insuficiente", "sem_padrao_claro", "pico_pontual", "recorrente_em_queda", "novo_padrao"}
    for entidade in body["recorrencia"]["entidades"]:
        assert entidade["status_recorrencia"] not in status_proibidos
