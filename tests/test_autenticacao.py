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


def test_esquema_bearer_e_case_insensitive(tmp_path):
    """RFC 7235: o esquema de autenticacao nao distingue caixa.

    O middleware ja aceitava so `Bearer ` exato, enquanto a ingestao (que usa
    `_chave_do_cabecalho`) normalizava -- cliente HTTP que escreve `bearer`
    passava numa rota e levava 401 na outra.
    """
    cliente = _cliente(tmp_path, chave_mestra=MESTRA)
    for esquema in ("Bearer", "bearer", "BEARER", "BeArEr"):
        resposta = cliente.get(
            "/conversas", headers={"Authorization": f"{esquema} {MESTRA}"}
        )
        assert resposta.status_code == 200, esquema


def test_ingestao_com_barra_final_segue_isenta_do_middleware(tmp_path):
    """`/ingestao/` e a mesma rota: a isencao compara o path sem a barra.

    Integrador que configurou a URL com barra final caia no 401 do middleware
    (que compara path exato) em vez de ser regido pela chave de FONTE.
    """
    cliente = _cliente(tmp_path, chave_mestra=MESTRA)
    mestra = {"Authorization": f"Bearer {MESTRA}"}
    fonte = _criar_fonte(cliente, mestra)
    chave_da_fonte = cliente.post(
        f"/integracoes/fontes/{fonte['id']}/chave", headers=mestra
    ).json()["chave"]

    pedido = {
        "id": "abc-barra",
        "mensagens": [
            {
                "autor": "cliente",
                "texto": "obrigado",
                "enviada_em": "2026-08-14T12:00:00+00:00",
            }
        ],
    }
    resposta = cliente.post(
        "/ingestao/", json=pedido,
        headers={"Authorization": f"Bearer {chave_da_fonte}"},
        follow_redirects=False,
    )
    # 307 e o redirect do proprio Starlette para /ingestao -- o que importa e
    # nao ter sido barrado pelo middleware com 401.
    assert resposta.status_code in (201, 307)


def test_ingestao_usa_o_canal_da_fonte_e_ignora_o_corpo(tmp_path):
    """Quem manda o dado nao escolhe em que canal ele e contabilizado."""
    cliente = _cliente(tmp_path, chave_mestra=MESTRA)
    mestra = {"Authorization": f"Bearer {MESTRA}"}
    fonte = _criar_fonte(cliente, mestra)
    chave = cliente.post(
        f"/integracoes/fontes/{fonte['id']}/chave", headers=mestra
    ).json()["chave"]

    resposta = cliente.post(
        "/ingestao",
        json={
            "id": "canal-1",
            "canal": "canal-inventado-pelo-cliente",
            "mensagens": [
                {
                    "autor": "cliente",
                    "texto": "obrigado",
                    "enviada_em": "2026-08-14T12:00:00+00:00",
                }
            ],
        },
        headers={"Authorization": f"Bearer {chave}"},
    )
    assert resposta.status_code == 201
    assert resposta.json()["canal"] == fonte["canal"]
    assert resposta.json()["fonte"] == fonte["nome"]


def test_ingestao_de_fonte_desativada_e_403(tmp_path):
    """O interruptor da tela de Integracoes precisa desligar de fato."""
    cliente = _cliente(tmp_path, chave_mestra=MESTRA)
    mestra = {"Authorization": f"Bearer {MESTRA}"}
    fonte = _criar_fonte(cliente, mestra)
    chave = cliente.post(
        f"/integracoes/fontes/{fonte['id']}/chave", headers=mestra
    ).json()["chave"]
    cliente.patch(
        f"/integracoes/fontes/{fonte['id']}", json={"ativa": False}, headers=mestra
    )

    resposta = cliente.post(
        "/ingestao",
        json={
            "id": "desligada-1",
            "mensagens": [
                {
                    "autor": "cliente",
                    "texto": "oi",
                    "enviada_em": "2026-08-14T12:00:00+00:00",
                }
            ],
        },
        headers={"Authorization": f"Bearer {chave}"},
    )
    # 403, nao 401: a chave esta certa, o que esta desligado e a fonte.
    assert resposta.status_code == 403
