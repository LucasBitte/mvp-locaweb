from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)


def test_clusters_cobre_a_d():
    r = client.get("/api/clusters")
    assert r.status_code == 200
    body = r.json()
    assert {c["cluster_id"] for c in body["clusters"]} == {"A", "B", "C", "D"}


def test_clusters_soma_pct_volume_proxima_de_100():
    r = client.get("/api/clusters")
    body = r.json()
    total = sum(c["pct_volume"] for c in body["clusters"])
    assert 99 <= total <= 101


def test_clusters_tags_e_lista():
    r = client.get("/api/clusters")
    body = r.json()
    for c in body["clusters"]:
        assert isinstance(c["tags"], list)
        assert all(isinstance(t, str) for t in c["tags"])


def test_clusters_metrica_de_sla_renomeada_e_documentada():
    r = client.get("/api/clusters")
    body = r.json()
    for c in body["clusters"]:
        assert "taxa_sla_violado_pct" not in c
        assert "taxa_excedeu_tempo_esperado_pct" in c
    assert "nota_metrica_sla" in body
    assert "kpi_status_int" in body["nota_metrica_sla"]
