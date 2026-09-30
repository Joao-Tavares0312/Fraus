"""Upload -> banco -> filtros, indicadores e grafo, sem depender de pesos."""
import pytest
from fastapi.testclient import TestClient
from fraus.api.main import criar_app
from fraus.db import Banco
from tests.test_api import MotorRespeitandoSinal, CSV, CSV_SEM_CLIENTE


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    banco = Banco(tmp_path / "dados.db")
    banco.migrar()
    # So substitui a verificacao de tipo; em runtime ela recusa o duble.
    monkeypatch.setattr("fraus.api.rotas.analise.motor_e_real", lambda motor: True)
    cliente = TestClient(criar_app(banco, MotorRespeitandoSinal(), raiz_importacao=tmp_path))
    return cliente, banco


def enviar(cliente, csv=CSV, rota="/analisar/registrar"):
    return cliente.post(rota, files={"arquivo": ("conversa.csv", csv, "text/csv")})


def test_upload_salvo_compartilha_o_recorte_e_o_grafo(ambiente):
    cliente, banco = ambiente
    resultado = enviar(cliente)
    assert resultado.status_code == 200, resultado.text
    gravacao = resultado.json()["gravacao"]
    identificador = gravacao["ids"][0]
    assert banco.buscar(identificador) is not None
    indicadores = cliente.get("/indicadores?de=2026-08-13&ate=2026-08-13").json()
    assert indicadores["total_conversas"] == 1
    assert indicadores["nps"] == 100
    assert cliente.get("/indicadores?de=2026-08-14").json()["total_conversas"] == 0
    grafo = cliente.get("/grafo?de=2026-08-13&ate=2026-08-13").json()
    assert any(n["id"] == f"conversa:{identificador}" for n in grafo["nos"])
    assert cliente.get(f"/conversas/{identificador}").json()["score"] == resultado.json()["analises"][0]["score"]


def test_reenvio_identico_nao_duplica(ambiente):
    cliente, banco = ambiente
    primeiro = enviar(cliente).json()
    segundo = enviar(cliente).json()
    assert primeiro["gravacao"]["ids"] == segundo["gravacao"]["ids"]
    assert len(banco.todas()) == 1


def test_avulsa_preserva_contrato_sem_gravar(ambiente):
    cliente, banco = ambiente
    assert enviar(cliente, rota="/analisar/arquivo").status_code == 200
    assert banco.todas() == []


def test_sem_cliente_e_salvo_com_score_nulo(ambiente):
    cliente, banco = ambiente
    assert enviar(cliente, CSV_SEM_CLIENTE).status_code == 200
    assert banco.todas()[0][1] is None
    assert cliente.get("/indicadores").json()["nps"] is None


def test_sem_horarios_nao_inventa_medicao(ambiente):
    cliente, banco = ambiente
    resposta = cliente.post("/analisar/registrar", files={"arquivo": ("c.txt", "Cliente: demorou demais\nBot: desculpe", "text/plain")})
    assert resposta.status_code == 422
    assert banco.todas() == []


def test_duble_nao_publica_estimativa(tmp_path):
    banco = Banco(tmp_path / "dados.db")
    banco.migrar()
    cliente = TestClient(criar_app(banco, MotorRespeitandoSinal()))
    assert enviar(cliente).status_code == 503
    assert banco.todas() == []


def test_falha_no_fim_da_analise_nao_publica_metade(ambiente, monkeypatch):
    cliente, banco = ambiente
    motor = cliente.app.state.contexto.motor
    original = motor.analisar_conversa
    chamadas = []
    def falhar(conversa, referencia=None, curadoria=None):
        chamadas.append(1)
        if len(chamadas) == 2:
            raise RuntimeError("falha de inferencia")
        return original(conversa, referencia, curadoria)
    monkeypatch.setattr(motor, "analisar_conversa", falhar)
    lote = CSV + CSV_SEM_CLIENTE.split("\n", 1)[1]
    with pytest.raises(RuntimeError, match="falha de inferencia"):
        enviar(cliente, lote)
    assert banco.todas() == []
