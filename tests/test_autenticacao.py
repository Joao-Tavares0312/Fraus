"""Autenticacao da API: liga quando ha chave mestra, e nada muda sem ela.

O motor falso respeita o contrato minimo que as rotas usadas aqui exigem.
"""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco

MESTRA = "segredo-de-teste-com-entropia-suficiente"


class MotorFalso:
    def pontuar_conversa(self, conversa):
        return 50.0

    def importancias(self):
        return None


def _cliente(tmp_path, chave_mestra=None):
    banco = Banco(tmp_path / "t.db")
    banco.migrar()
    app = criar_app(
        banco=banco, motor=MotorFalso(), raiz_importacao=tmp_path,
        chave_mestra=chave_mestra,
    )
    return TestClient(app)


def test_sem_chave_mestra_a_api_continua_aberta(tmp_path):
    cliente = _cliente(tmp_path)
    assert cliente.get("/conversas").status_code == 200


def test_com_chave_mestra_leitura_sem_header_e_401(tmp_path):
    cliente = _cliente(tmp_path, chave_mestra=MESTRA)
    resposta = cliente.get("/conversas")
    assert resposta.status_code == 401
    assert resposta.headers["WWW-Authenticate"] == "Bearer"


def test_chave_mestra_autentica_qualquer_rota(tmp_path):
    cliente = _cliente(tmp_path, chave_mestra=MESTRA)
    resposta = cliente.get(
        "/conversas", headers={"Authorization": f"Bearer {MESTRA}"}
    )
    assert resposta.status_code == 200


def test_chave_errada_e_401_com_mensagem_uniforme(tmp_path):
    cliente = _cliente(tmp_path, chave_mestra=MESTRA)
    resposta = cliente.get(
        "/conversas", headers={"Authorization": "Bearer fra_1_deadbeef"}
    )
    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "chave invalida"


def test_chave_mestra_vazia_e_o_mesmo_que_ausente(tmp_path):
    cliente = _cliente(tmp_path, chave_mestra="")
    assert cliente.get("/conversas").status_code == 200
