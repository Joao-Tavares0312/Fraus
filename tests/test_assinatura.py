"""Assinatura de webhook no padrao Standard Webhooks.

Testes do modulo PURO: sem HTTP e sem banco. O porteiro da rota que usa isto
esta em tests/test_webhook.py.
"""

import base64

import pytest

from fraus import assinatura

CORPO = b'{"id":"atendimento-1","mensagens":[]}'


def test_segredo_gerado_tem_o_prefixo_e_e_base64_valido():
    segredo = assinatura.gerar_segredo()
    assert segredo.startswith("whsec_")
    # A chave HMAC e o base64 DECODIFICADO -- e o que a especificacao define,
    # e o que faz uma biblioteca de prateleira do outro lado bater com a gente.
    assert len(assinatura.chave_do_segredo(segredo)) == 32


def test_dois_segredos_nunca_sao_iguais():
    assert assinatura.gerar_segredo() != assinatura.gerar_segredo()


def test_assinatura_confere_contra_ela_mesma():
    segredo = assinatura.gerar_segredo()
    assinada = assinatura.assinar("msg_1", "1756300000", CORPO, segredo)
    assert assinada.startswith("v1,")
    assert assinatura.confere("msg_1", "1756300000", CORPO, segredo, assinada)


def test_corpo_alterado_em_um_byte_nao_confere():
    """O teste que prova que a conferencia e sobre os BYTES CRUS.

    E o unico que pega a regressao de deixar o FastAPI desserializar e a gente
    re-serializar para conferir: reordenar uma chave ou mudar um espaco muda a
    assinatura, e o defeito passaria despercebido em todo teste de corpo igual.
    """
    segredo = assinatura.gerar_segredo()
    assinada = assinatura.assinar("msg_1", "1756300000", CORPO, segredo)
    assert not assinatura.confere(
        "msg_1", "1756300000", CORPO + b" ", segredo, assinada
    )


@pytest.mark.parametrize("campo", ["id", "timestamp"])
def test_id_ou_timestamp_trocado_nao_confere(campo):
    """Os tres entram no payload assinado -- trocar qualquer um invalida."""
    segredo = assinatura.gerar_segredo()
    assinada = assinatura.assinar("msg_1", "1756300000", CORPO, segredo)
    outro_id = "msg_2" if campo == "id" else "msg_1"
    outro_ts = "1756399999" if campo == "timestamp" else "1756300000"
    assert not assinatura.confere(outro_id, outro_ts, CORPO, segredo, assinada)


def test_segredo_diferente_nao_confere():
    assinada = assinatura.assinar("msg_1", "1756300000", CORPO, assinatura.gerar_segredo())
    assert not assinatura.confere(
        "msg_1", "1756300000", CORPO, assinatura.gerar_segredo(), assinada
    )


@pytest.mark.parametrize("recebida", ["", "v1,", "lixo", "v2,QUJD", "QUJD"])
def test_assinatura_malformada_e_recusada_sem_levantar(recebida):
    """Recusa, nao excecao: entrada malformada vem da rede o tempo todo."""
    segredo = assinatura.gerar_segredo()
    assert not assinatura.confere("msg_1", "1756300000", CORPO, segredo, recebida)


def test_confere_aceita_uma_entre_varias_assinaturas_no_cabecalho():
    """Rotacao de segredo manda as duas assinaturas separadas por espaco.

    Recusar o cabecalho com mais de uma quebraria justamente a rotacao sem
    janela de indisponibilidade, que e o motivo de a especificacao permitir.
    """
    segredo = assinatura.gerar_segredo()
    valida = assinatura.assinar("msg_1", "1756300000", CORPO, segredo)
    assert assinatura.confere(
        "msg_1", "1756300000", CORPO, segredo, f"v1,QUJD {valida}"
    )


@pytest.mark.parametrize("segredo", ["", "whsec_", "sem-prefixo", "whsec_!!!nao-base64"])
def test_segredo_malformado_levanta_value_error(segredo):
    """Aqui LEVANTA, e a diferenca importa: segredo malformado e defeito da
    MAQUINA que hospeda (variavel mal preenchida), nao da requisicao. A rota
    traduz isso em 503, nunca em 401."""
    with pytest.raises(ValueError):
        assinatura.chave_do_segredo(segredo)


@pytest.mark.parametrize("timestamp,esperado", [
    ("1756300000", True),      # exatamente agora
    ("1756299800", True),      # 200s atras, dentro dos 300
    ("1756299699", False),     # 301s atras, fora
    ("1756300301", False),     # 301s no FUTURO, fora
    ("ontem", False),          # nao numerico
    ("", False),
])
def test_janela_de_replay_de_cinco_minutos(timestamp, esperado):
    """A janela vale para os DOIS lados. Relogio adiantado no remetente e um
    caso real; assinatura com timestamp futuro sem limite deixaria uma captura
    valida para sempre."""
    assert assinatura.dentro_da_janela(timestamp, agora=1756300000) is esperado
