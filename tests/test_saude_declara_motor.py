"""`/saude` precisa dizer QUAL motor esta servindo, nao so que respondeu.

O DEFEITO QUE ISTO TRANCA, pago em 04/09/2026: a rota devolvia
`{"status": "ok"}` e nada mais. Com o `scripts/api_demo.py` no dublê, a
dashboard escreveu "API no ar" o dia inteiro no rodape enquanto todo numero da
tela era sintetico -- inclusive as importancias por feature, que sairam numa
progressao 0,2 / 0,25 / 0,3 e passaram por peso de regressao.

"Respondeu" e "esta medindo" sao afirmacoes diferentes. Numa ferramenta
batizada com o nome do daimon do engano, anunciar a segunda quando so a
primeira e verdade e a pior falha possivel.
"""

import pytest
from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco
from fraus.motor import Motor


class MotorQualquer:
    """Um motor que nao e o `Motor` real -- o caso do dublê da demo."""


class MotorRealFalsificado(Motor):
    """Herda do `Motor` real sem rodar o __init__ dele (que carregaria BERTimbau)."""

    def __init__(self):  # noqa: D107 - de proposito, nao chama super()
        pass


@pytest.fixture
def banco(tmp_path):
    return Banco(tmp_path / "t.db")


def _cliente(banco, motor, tmp_path):
    return TestClient(criar_app(banco=banco, motor=motor, raiz_importacao=tmp_path))


def test_saude_declara_motor_real(banco, tmp_path):
    resposta = _cliente(banco, MotorRealFalsificado(), tmp_path).get("/saude")
    assert resposta.status_code == 200
    assert resposta.json()["motor"] == "real"


def test_saude_declara_duble(banco, tmp_path):
    resposta = _cliente(banco, MotorQualquer(), tmp_path).get("/saude")
    assert resposta.status_code == 200
    assert resposta.json()["motor"] == "duble"


def test_status_continua_ok(banco, tmp_path):
    """O campo antigo nao muda de significado -- quem so olha `status` nao quebra."""
    resposta = _cliente(banco, MotorQualquer(), tmp_path).get("/saude")
    assert resposta.json()["status"] == "ok"


def test_motor_desconhecido_nao_e_anunciado_como_real(banco, tmp_path):
    """A duvida cai para `duble`, nunca para `real`.

    Um motor que ninguem reconhece pode ser qualquer coisa. Errar para o lado
    de "isto pode ser sintetico" custa uma etiqueta a mais na tela; errar para
    o outro lado apresenta invencao como medicao numa banca.
    """

    class MotorDeOutroLugar:
        pass

    resposta = _cliente(banco, MotorDeOutroLugar(), tmp_path).get("/saude")
    assert resposta.json()["motor"] == "duble"
