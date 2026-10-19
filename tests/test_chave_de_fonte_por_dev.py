"""Quem administra pela dashboard gera a chave da fonte sem digitar a mestra.

Em producao a dashboard fala com a API pelo proxy, que manda o JWT da sessao
-- nunca a mestra. Gerar a chave de uma fonte exigia a mestra, e o botao da
tela de Integracoes respondia 403 para o proprio desenvolvedor (19/10/2026).

Chave de FONTE so escreve conversa naquela fonte: o papel `dev`, que ja
administra integracoes, basta. Chave de ACESSO continua exigindo a mestra.
"""

from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco
from tests.test_auth import CODIGO_DEV, MESTRA, SEGREDO_JWT, MotorFalso, _cadastro


def _cliente(tmp_path):
    banco = Banco(tmp_path / "t.db")
    banco.migrar()
    app = criar_app(
        banco=banco, motor=MotorFalso(), raiz_importacao=tmp_path,
        chave_mestra=MESTRA, jwt_segredo=SEGREDO_JWT, codigo_dev=CODIGO_DEV,
    )
    return TestClient(app)


def _token(cliente, email, dev):
    extra = {"codigo_dev": CODIGO_DEV} if dev else {}
    cliente.post("/auth/registrar", json=_cadastro(email=email, **extra))
    entrada = cliente.post("/auth/entrar", json={"email": email, "senha": "senha-longa-o-bastante"})
    return {"Authorization": f"Bearer {entrada.json()['token']}"}


def _fonte(cliente):
    mestra = {"Authorization": f"Bearer {MESTRA}"}
    resposta = cliente.post("/integracoes/fontes", headers=mestra,
                            json={"nome": "TARS", "tipo": "webhook", "canal": "tars"})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()["id"]


def test_dev_gera_e_revoga_chave_da_fonte(tmp_path):
    cliente = _cliente(tmp_path)
    fonte = _fonte(cliente)
    dev = _token(cliente, "dev@empresa.com", dev=True)
    gerada = cliente.post(f"/integracoes/fontes/{fonte}/chave", headers=dev)
    assert gerada.status_code == 201, gerada.text
    assert gerada.json()["chave"].startswith("frs_")
    assert cliente.delete(f"/integracoes/fontes/{fonte}/chave", headers=dev).status_code == 204


def test_dev_gera_segredo_de_webhook(tmp_path):
    cliente = _cliente(tmp_path)
    fonte = _fonte(cliente)
    dev = _token(cliente, "dev@empresa.com", dev=True)
    assert cliente.post(f"/integracoes/fontes/{fonte}/segredo", headers=dev).status_code == 201


def test_usuario_comum_nao_gera_chave(tmp_path):
    cliente = _cliente(tmp_path)
    fonte = _fonte(cliente)
    usuario = _token(cliente, "ana@empresa.com", dev=False)
    assert cliente.post(f"/integracoes/fontes/{fonte}/chave", headers=usuario).status_code == 403


def test_chave_de_acesso_continua_exigindo_a_mestra(tmp_path):
    cliente = _cliente(tmp_path)
    dev = _token(cliente, "dev@empresa.com", dev=True)
    assert cliente.post("/acesso/chaves", headers=dev, json={"nome": "x"}).status_code == 403
