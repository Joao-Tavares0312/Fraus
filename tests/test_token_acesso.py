"""O token de sessao: JWT HS256, e nada alem de HS256.

O papel viaja DENTRO do token assinado: a interface o le para esconder telas,
mas quem decide e o servidor, que confere a assinatura a cada requisicao --
ninguem promove a si mesmo editando o localStorage.

O relogio chega por parametro (`agora`), como na assinatura de webhook: teste
que depende do relogio da maquina passa hoje e falha na sexta.
"""

from datetime import datetime, timedelta, timezone

import jwt as pyjwt

from fraus import token_acesso

SEGREDO = "segredo-de-teste"
AGORA = datetime(2026, 8, 31, 12, 0, 0, tzinfo=timezone.utc)


def _emitir(**mudancas) -> str:
    parametros = dict(usuario_id=7, papel="usuario", segredo=SEGREDO, agora=AGORA)
    parametros.update(mudancas)
    return token_acesso.emitir(**parametros)


def test_ida_e_volta_carrega_usuario_e_papel():
    token = _emitir(usuario_id=7, papel="dev")
    sessao = token_acesso.conferir(token, SEGREDO, agora=AGORA)
    assert sessao == {"usuario_id": 7, "papel": "dev"}


def test_dentro_da_validade_aceita_e_depois_dela_recusa():
    token = _emitir()
    quase = AGORA + token_acesso.VALIDADE - timedelta(minutes=1)
    depois = AGORA + token_acesso.VALIDADE + timedelta(minutes=1)
    assert token_acesso.conferir(token, SEGREDO, agora=quase) is not None
    assert token_acesso.conferir(token, SEGREDO, agora=depois) is None


def test_assinatura_de_outro_segredo_recusa():
    token = _emitir()
    assert token_acesso.conferir(token, "outro-segredo", agora=AGORA) is None


def test_token_adulterado_recusa():
    token = _emitir(papel="usuario")
    cabecalho, corpo, assinatura = token.split(".")
    corpo_dev = pyjwt.encode(
        pyjwt.decode(token, SEGREDO, algorithms=["HS256"]) | {"papel": "dev"},
        "segredo-do-atacante",
        algorithm="HS256",
    ).split(".")[1]
    assert token_acesso.conferir(
        ".".join((cabecalho, corpo_dev, assinatura)), SEGREDO, agora=AGORA
    ) is None


def test_alg_none_recusa():
    # O ataque classico de JWT: cabecalho declarando "sem assinatura" e o
    # verificador obediente aceitando. HS256 e fixo por construcao.
    sem_assinatura = pyjwt.encode(
        {"sub": "7", "papel": "dev"}, key=None, algorithm="none"
    )
    assert token_acesso.conferir(sem_assinatura, SEGREDO, agora=AGORA) is None


def test_lixo_recusa_sem_levantar():
    assert token_acesso.conferir("nao-e-um-jwt", SEGREDO, agora=AGORA) is None
    assert token_acesso.conferir("", SEGREDO, agora=AGORA) is None


def test_payload_sem_campo_obrigatorio_recusa():
    incompleto = pyjwt.encode({"sub": "7"}, SEGREDO, algorithm="HS256")
    assert token_acesso.conferir(incompleto, SEGREDO, agora=AGORA) is None
