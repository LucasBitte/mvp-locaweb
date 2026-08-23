from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)

_REGRAS_VALIDAS = {
    "pico_volume_d1",
    "pressao_operacional_equipe",
    "cluster_alta_violacao",
    "concentracao_categoria",
    "recorrencia_operacional",
}


def test_alertas_regra_origem_sempre_presente_e_valida():
    r = client.get("/api/alertas")
    assert r.status_code == 200
    body = r.json()
    assert len(body["alertas"]) > 0
    for alerta in body["alertas"]:
        assert alerta["regra_origem"] in _REGRAS_VALIDAS
        assert alerta["tipo"] in {"critico", "atencao", "info"}


def test_recomendacoes_rastreiam_regra_que_gerou():
    r = client.get("/api/alertas")
    body = r.json()
    regras_dos_alertas = {a["regra_origem"] for a in body["alertas"]}
    for rec in body["recomendacoes"]:
        assert rec["regra_origem"] in _REGRAS_VALIDAS
        assert rec["regra_origem"] in regras_dos_alertas


def test_alertas_nunca_menciona_item_de_configuracao():
    r = client.get("/api/alertas")
    payload_str = r.text.lower()
    assert "item de configura" not in payload_str
    assert " ci " not in payload_str
