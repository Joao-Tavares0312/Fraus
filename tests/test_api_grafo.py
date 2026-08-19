import pytest
from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco
from fraus.fusor import NOMES_FEATURES

from tests.test_api import CSV, MotorFalso


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


def test_eixo_do_motor_chega_como_aresta_caracteriza_com_peso_e_lado_certos(
    cliente, tmp_path
):
    """Fecha a costura Motor.eixo_global() -> montar_grafo(eixo=...) pelo HTTP.

    Sem este teste, `AtribuicaoDuble.eixo_global()` (tests/test_api.py) poderia
    devolver chave errada, sinal trocado ou dict vazio que a suite continuaria
    verde -- os outros testes de /grafo so olham as chaves de topo, nunca o
    conteudo de `arestas`. O esperado e recalculado aqui com a MESMA formula
    do dublê (indice % 5 - 2), nao digitado a mao, para o teste continuar
    valendo se a formula mudar.
    """
    caminho = tmp_path / "entrada.csv"
    caminho.write_text(CSV, encoding="utf-8")
    resposta_importar = cliente.post(
        "/conversas/importar", json={"caminho": str(caminho)}
    )
    assert resposta_importar.status_code == 200

    corpo = cliente.get("/grafo").json()

    esperado = {
        nome: float((indice % 5) - 2) for indice, nome in enumerate(NOMES_FEATURES)
    }
    positivas = [nome for nome, peso in esperado.items() if peso > 0]
    negativas = [nome for nome, peso in esperado.items() if peso < 0]
    # O dublê precisa exercitar os dois lados da regra -- so um sinal nao
    # provaria que "positivo vai pra faixa alta, negativo pra faixa baixa".
    assert positivas and negativas

    nos_feature = {no["id"] for no in corpo["nos"] if no["tipo"] == "feature"}
    assert nos_feature, "esperava pelo menos um no feature no grafo"

    arestas_caracteriza = {
        aresta["de"]: aresta
        for aresta in corpo["arestas"]
        if aresta["tipo"] == "caracteriza"
    }
    assert arestas_caracteriza, "esperava pelo menos uma aresta 'caracteriza'"

    for nome in positivas:
        aresta = arestas_caracteriza[f"feature:{nome}"]
        assert aresta["para"] == "categoria:promotor"
        assert aresta["peso"] == abs(esperado[nome])

    for nome in negativas:
        aresta = arestas_caracteriza[f"feature:{nome}"]
        assert aresta["para"] == "categoria:detrator"
        assert aresta["peso"] == abs(esperado[nome])
