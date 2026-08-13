import pytest
from fastapi.testclient import TestClient

from dolos.api.main import criar_app
from dolos.db import Banco

CSV = (
    "conversa_id,canal,autor,texto,enviada_em,escalou_para_humano\n"
    "c1,csv,cliente,otimo,2026-08-13T10:00:00+00:00,false\n"
    "c1,csv,bot,de nada,2026-08-13T10:00:08+00:00,false\n"
    "c1,csv,cliente,valeu,2026-08-13T10:00:15+00:00,false\n"
)


class MotorFalso:
    def pontuar_conversa(self, conversa):
        return 90.0


@pytest.fixture
def cliente(tmp_path):
    banco = Banco(tmp_path / "dolos.db")
    banco.migrar()
    return TestClient(criar_app(banco=banco, motor=MotorFalso()))


def test_saude_responde_ok(cliente):
    resposta = cliente.get("/saude")
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "ok"


def test_importar_csv_persiste_e_pontua(cliente, tmp_path):
    caminho = tmp_path / "entrada.csv"
    caminho.write_text(CSV, encoding="utf-8")

    resposta = cliente.post("/conversas/importar", json={"caminho": str(caminho)})
    assert resposta.status_code == 200
    assert resposta.json() == {"importadas": 1, "rejeitadas": 0}

    listagem = cliente.get("/conversas").json()
    assert len(listagem) == 1
    assert listagem[0]["score"] == 90.0
    assert listagem[0]["categoria"] == "promotor"


def test_categoria_enviada_pelo_cliente_e_ignorada(cliente, tmp_path):
    caminho = tmp_path / "entrada.csv"
    caminho.write_text(CSV, encoding="utf-8")
    cliente.post(
        "/conversas/importar",
        json={"caminho": str(caminho), "categoria": "detrator", "score": 0},
    )
    assert cliente.get("/conversas").json()[0]["categoria"] == "promotor"


def test_detalhe_traz_a_transcricao(cliente, tmp_path):
    caminho = tmp_path / "entrada.csv"
    caminho.write_text(CSV, encoding="utf-8")
    cliente.post("/conversas/importar", json={"caminho": str(caminho)})

    detalhe = cliente.get("/conversas/c1").json()
    assert len(detalhe["mensagens"]) == 3
    assert detalhe["mensagens"][0]["texto"] == "otimo"


def test_detalhe_de_conversa_inexistente_e_404(cliente):
    assert cliente.get("/conversas/nao-existe").status_code == 404


def test_indicadores_agregam_o_que_foi_importado(cliente, tmp_path):
    caminho = tmp_path / "entrada.csv"
    caminho.write_text(CSV, encoding="utf-8")
    cliente.post("/conversas/importar", json={"caminho": str(caminho)})

    indicadores = cliente.get("/indicadores").json()
    assert indicadores["nps"] == 100.0
    assert indicadores["csat"] == 100.0
    assert indicadores["containment_rate"] == 100.0
    assert indicadores["total_conversas"] == 1


def test_indicadores_sem_dado_nao_quebra(cliente):
    indicadores = cliente.get("/indicadores").json()
    assert indicadores["total_conversas"] == 0
    assert indicadores["nps"] == 0.0
