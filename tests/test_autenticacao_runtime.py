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
    def pontuar_conversa(self, conversa, curadoria=None):
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


def test_ambiente_EXCLUI_a_gravada(tmp_path):
    """Com a variavel definida, ela e a UNICA mestra. A gravada nao vale mais.

    ESTE TESTE INVERTEU EM 25/08/2026, e a reversao e deliberada. Ele afirmava o
    contrario -- que as duas autorizavam juntas --, com esta justificativa:

        "O ambiente vence como ORIGEM declarada, nao invalida a gravada.
         Recusar a do banco quando ha variavel deixaria quem gravou pela tela
         sem entrar depois de alguem definir a variavel no ambiente."

    O medo e legitimo e a saida dele e trivial: apagar a variavel devolve o
    posto a mestra do banco (fixado no teste seguinte). O que a uniao criava,
    esse sim, nao tinha saida: o README apresenta `FRAUS_CHAVE_MESTRA` como o
    caminho de quem PERDEU ou VAZOU a mestra da tela, e com a uniao a vazada
    continuava abrindo tudo. Pior, a variavel definida faz `/acesso/mestra`
    recusar a rotacao com 409 -- entao nao sobrava caminho nenhum pela API para
    matar a chave vazada.

    A assimetria e o argumento: ser trancado fora e REVERSIVEL, credencial
    vazada que sobrevive ao procedimento de revogacao documentado nao e.
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
    ).status_code == 401


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


def test_sem_ambiente_a_gravada_continua_valendo(tmp_path):
    """O par do teste acima: tirar a variavel devolve o posto a mestra do banco.

    Sem isto, o conserto de precedencia poderia ter matado a mestra gravada em
    TODA situacao -- e ela e o que faz a autenticacao ligada por botao
    sobreviver a reiniciar o processo.
    """
    gravada = "frm_" + "c" * 64
    cliente, banco = _cliente(tmp_path, chave_mestra=None)
    _grava(banco, gravada)

    assert cliente.get(
        "/conversas", headers={"Authorization": f"Bearer {gravada}"}
    ).status_code == 200
