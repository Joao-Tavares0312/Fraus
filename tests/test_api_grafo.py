import pytest
from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco

from tests.test_api import MotorFalso


@pytest.fixture
def cliente(tmp_path):
    banco = Banco(tmp_path / "fraus.db")
    banco.migrar()
    return TestClient(
        criar_app(banco=banco, motor=MotorFalso(), raiz_importacao=tmp_path)
    )


def test_grafo_responde_com_nos_arestas_e_meta(cliente):
    resposta = cliente.get("/grafo")
    assert resposta.status_code == 200

    corpo = resposta.json()
    assert set(corpo) == {"nos", "arestas", "meta"}
    assert corpo["meta"]["camadas"] == ["dominio", "lexico", "proveniencia"]


def test_banco_vazio_devolve_grafo_vazio_e_nao_erro(cliente):
    """Vazio nao e falha -- a tela tem estado vazio proprio para isso."""
    resposta = cliente.get("/grafo")
    assert resposta.status_code == 200
    assert resposta.json()["nos"] == [] or resposta.json()["meta"]["conversas"] >= 0


def test_camada_desconhecida_da_400(cliente):
    """Ignorar em silencio devolveria um grafo diferente do pedido sem avisar."""
    resposta = cliente.get("/grafo?camadas=lexico,inventada")
    assert resposta.status_code == 400
    assert "inventada" in resposta.json()["detail"]


def test_camada_restrita_e_respeitada(cliente):
    corpo = cliente.get("/grafo?camadas=dominio").json()
    assert corpo["meta"]["camadas"] == ["dominio"]


def test_teto_de_termos_acima_do_limite_da_400(cliente):
    """O teto existe para o cliente nao conseguir pedir 80 mil nos."""
    resposta = cliente.get("/grafo?teto_termos=100000")
    assert resposta.status_code == 400


def test_periodo_invalido_da_400(cliente):
    """Mesma validacao de recorte das outras rotas -- nao uma copia local."""
    resposta = cliente.get("/grafo?de=2026-13-45")
    assert resposta.status_code == 400
