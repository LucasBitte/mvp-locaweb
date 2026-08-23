from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)


def test_fatores_granularidade_conceito_quando_disponivel():
    r = client.get("/api/fatores")
    assert r.status_code == 200
    body = r.json()
    assert body["granularidade"] in {"conceito", "coluna"}
    if body["granularidade"] == "conceito":
        assert all(item["conceito"] is not None for item in body["importancia_conceitos"])
    else:
        assert all(item["feature"] is not None for item in body["importancia_conceitos"])
    ranks = [item["rank"] for item in body["importancia_conceitos"]]
    assert ranks == sorted(ranks)


def test_fatores_shap_cobre_todos_incidentes_da_execucao_sem_mencionar_previsao():
    r = client.get("/api/fatores")
    body = r.json()
    incidentes = {item["incident_id"] for item in body["shap_top_risco"]}
    assert 1 <= len(incidentes) <= 30
    payload_str = r.text.lower()
    assert "previsão" not in payload_str
    assert "amanhã" not in payload_str


def test_fatores_heatmap_sem_celulas_vazias():
    r = client.get("/api/fatores")
    body = r.json()
    assert len(body["heatmap_categoria_dia"]) > 0
    for celula in body["heatmap_categoria_dia"]:
        assert celula["volume_medio"] > 0
