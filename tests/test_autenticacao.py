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


def _criar_chave_de_acesso(cliente, nome="dashboard"):
    resposta = cliente.post(
        "/acesso/chaves",
        json={"nome": nome},
        headers={"Authorization": f"Bearer {MESTRA}"},
    )
    assert resposta.status_code == 201
    return resposta.json()


def test_chave_de_acesso_criada_pela_mestra_autentica_leitura(tmp_path):
    cliente = _cliente(tmp_path, chave_mestra=MESTRA)
    corpo = _criar_chave_de_acesso(cliente)
    assert corpo["chave"].startswith("fra_")
    resposta = cliente.get(
        "/conversas", headers={"Authorization": f"Bearer {corpo['chave']}"}
    )
    assert resposta.status_code == 200


def test_chave_de_acesso_nao_gerencia_chaves(tmp_path):
    cliente = _cliente(tmp_path, chave_mestra=MESTRA)
    corpo = _criar_chave_de_acesso(cliente)
    autorizacao = {"Authorization": f"Bearer {corpo['chave']}"}
    assert cliente.post("/acesso/chaves", json={"nome": "x"}, headers=autorizacao).status_code == 403
    assert cliente.get("/acesso/chaves", headers=autorizacao).status_code == 403
    assert cliente.delete(f"/acesso/chaves/{corpo['id']}", headers=autorizacao).status_code == 403


def test_revogacao_vale_na_chamada_seguinte(tmp_path):
    cliente = _cliente(tmp_path, chave_mestra=MESTRA)
    corpo = _criar_chave_de_acesso(cliente)
    mestra = {"Authorization": f"Bearer {MESTRA}"}
    assert cliente.delete(f"/acesso/chaves/{corpo['id']}", headers=mestra).status_code == 204
    resposta = cliente.get(
        "/conversas", headers={"Authorization": f"Bearer {corpo['chave']}"}
    )
    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "chave invalida"


def _criar_fonte(cliente, cabecalhos):
    resposta = cliente.post(
        "/integracoes/fontes",
        json={"nome": "totalk", "canal": "whatsapp", "tipo": "webhook"},
        headers=cabecalhos,
    )
    assert resposta.status_code == 201
    return resposta.json()


def test_gerar_chave_de_fonte_exige_a_mestra(tmp_path):
    cliente = _cliente(tmp_path, chave_mestra=MESTRA)
    mestra = {"Authorization": f"Bearer {MESTRA}"}
    fonte = _criar_fonte(cliente, mestra)
    corpo_acesso = _criar_chave_de_acesso(cliente)
    leitura = {"Authorization": f"Bearer {corpo_acesso['chave']}"}
    assert cliente.post(f"/integracoes/fontes/{fonte['id']}/chave", headers=leitura).status_code == 403
    assert cliente.post(f"/integracoes/fontes/{fonte['id']}/chave", headers=mestra).status_code == 201
    assert cliente.delete(f"/integracoes/fontes/{fonte['id']}/chave", headers=leitura).status_code == 403


def test_ingestao_segue_regida_pela_chave_de_fonte(tmp_path):
    cliente = _cliente(tmp_path, chave_mestra=MESTRA)
    mestra = {"Authorization": f"Bearer {MESTRA}"}
    fonte = _criar_fonte(cliente, mestra)
    chave_da_fonte = cliente.post(
        f"/integracoes/fontes/{fonte['id']}/chave", headers=mestra
    ).json()["chave"]

    pedido = {
        "id": "abc-1",
        "mensagens": [
            {
                "autor": "cliente",
                "texto": "obrigado",
                "enviada_em": "2026-08-14T12:00:00+00:00",
            }
        ],
    }
    # A MESTRA nao autoriza a ingestao: uma credencial por rota.
    recusada = cliente.post(
        "/ingestao", json=pedido, headers=mestra
    )
    assert recusada.status_code == 401
    aceita = cliente.post(
        "/ingestao", json=pedido,
        headers={"Authorization": f"Bearer {chave_da_fonte}"},
    )
    assert aceita.status_code == 201


def test_listagem_nunca_expoe_hash(tmp_path):
    cliente = _cliente(tmp_path, chave_mestra=MESTRA)
    _criar_chave_de_acesso(cliente)
    resposta = cliente.get(
        "/acesso/chaves", headers={"Authorization": f"Bearer {MESTRA}"}
    )
    assert resposta.status_code == 200
    for item in resposta.json():
        assert "chave_hash" not in item
        assert "chave" not in item
