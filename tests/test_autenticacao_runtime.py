"""A autenticacao decide por REQUISICAO, nao por boot.

Sem isto, ligar a mestra em runtime nao protegeria nada: o middleware nem
existiria no app que subiu aberto, e o botao da tela apenas PARECERIA
funcionar -- que e a pior falha possivel neste caminho.
"""

from fastapi.testclient import TestClient

from fraus import credencial
from fraus.api.main import criar_app
from fraus.db import Banco


class MotorFalso:
    def pontuar_conversa(self, conversa):
        return 50.0


def _cliente(tmp_path, chave_mestra=None):
    banco = Banco(tmp_path / "t.db")
    banco.migrar()
    app = criar_app(
        banco=banco, motor=MotorFalso(), raiz_importacao=tmp_path,
        chave_mestra=chave_mestra,
    )
    return TestClient(app), banco


def _grava(banco, chave):
    banco.gravar_chave_mestra(
        credencial.hash_da_chave(chave),
        credencial.dica(chave),
        "2026-08-17T10:00:00+00:00",
    )


def test_mestra_gravada_no_banco_passa_a_valer_no_mesmo_processo(tmp_path):
    cliente, banco = _cliente(tmp_path)
    assert cliente.get("/conversas").status_code == 200  # aberta

    chave = "frm_" + "a" * 64
    _grava(banco, chave)

    # MESMO cliente, MESMO app: sem reiniciar nada.
    assert cliente.get("/conversas").status_code == 401
    autorizada = cliente.get("/conversas", headers={"Authorization": f"Bearer {chave}"})
    assert autorizada.status_code == 200


def test_ambiente_e_banco_autorizam_os_dois(tmp_path):
    """O ambiente vence como ORIGEM declarada, nao invalida a gravada.

    Precedencia existe para responder "de onde vem a mestra vigente"; recusar a
    do banco quando ha variavel deixaria quem gravou pela tela sem entrar depois
    de alguem definir a variavel no ambiente.
    """
    do_ambiente = "segredo-do-ambiente"
    cliente, banco = _cliente(tmp_path, chave_mestra=do_ambiente)
    do_banco = "frm_" + "b" * 64
    _grava(banco, do_banco)

    assert cliente.get(
        "/conversas", headers={"Authorization": f"Bearer {do_ambiente}"}
    ).status_code == 200
    assert cliente.get(
        "/conversas", headers={"Authorization": f"Bearer {do_banco}"}
    ).status_code == 200


def test_chave_errada_continua_401_com_as_duas_procedencias(tmp_path):
    cliente, banco = _cliente(tmp_path, chave_mestra="segredo-do-ambiente")
    _grava(banco, "frm_" + "c" * 64)
    recusada = cliente.get("/conversas", headers={"Authorization": "Bearer nao-e"})
    assert recusada.status_code == 401
    assert recusada.json()["detail"] == "chave invalida"


def test_estado_sem_mestra_nenhuma(tmp_path):
    cliente, _ = _cliente(tmp_path)
    assert cliente.get("/acesso/estado").json() == {"ligada": False, "origem": None}


def test_estado_com_ambiente(tmp_path):
    cliente, _ = _cliente(tmp_path, chave_mestra="segredo")
    corpo = cliente.get(
        "/acesso/estado", headers={"Authorization": "Bearer segredo"}
    ).json()
    assert corpo == {"ligada": True, "origem": "ambiente"}


def test_estado_com_banco(tmp_path):
    cliente, banco = _cliente(tmp_path)
    _grava(banco, "frm_" + "d" * 64)
    assert cliente.get("/acesso/estado").json() == {"ligada": True, "origem": "banco"}


def test_estado_e_publico_mesmo_com_autenticacao_ligada(tmp_path):
    """A tela precisa desta resposta justamente quando nao tem credencial."""
    cliente, banco = _cliente(tmp_path)
    _grava(banco, "frm_" + "e" * 64)
    sem_header = cliente.get("/acesso/estado")
    assert sem_header.status_code == 200
    assert sem_header.json()["ligada"] is True
    # E nao vaza mais do que o necessario para desenhar a tela.
    assert set(sem_header.json()) == {"ligada", "origem"}


def test_saude_responde_sem_chave_com_autenticacao_ligada(tmp_path):
    """Diagnostico atras de credencial MENTE.

    Com /saude fechada, a dashboard sem chave recebia 401 no health check e
    anunciava "API fora do ar" com a API no ar -- mandando quem opera procurar
    servidor derrubado quando o que faltava era uma chave.
    """
    cliente, banco = _cliente(tmp_path)
    _grava(banco, "frm_" + "f" * 64)

    # A rota de dados fecha...
    assert cliente.get("/conversas").status_code == 401
    # ...e o diagnostico continua respondendo.
    resposta = cliente.get("/saude")
    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}
