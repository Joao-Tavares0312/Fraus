"""A terceira forma: tem dado, e nao ha evidencia suficiente para afirmar.

A interface tinha duas formas -- cabeca cheia (tem sinal) e cabeca vazada (sem
sinal). Faltava o caso do meio: uma conversa de uma unica mensagem "ok" saia
CHEIA, com a mesma confianca visual de uma conversa de 40 turnos.
(Desde 15/09/2026 "ok" sozinho e formula de cortesia e sai SEM sinal --
`fraus/cortesia.py` --, entao os exemplos daqui usam fala curta com conteudo.)

O QUE NAO PODE SER USADO AQUI: a probabilidade do modelo. Probabilidade nao
calibrada nao e confianca, e afirmar que e seria exatamente o tipo de
desonestidade que este projeto recusa em todo lugar. Calibrar exigiria
retreino. Entao a medida e EVIDENCIA OBSERVAVEL -- auditavel, defensavel, e
verificavel por quem ler o transcript.

Pelo mesmo motivo o campo NAO se chama `confianca`: o nome prometeria
calibracao que nao existe.
"""

from datetime import datetime, timezone

import pytest

from fraus.evidencia import (PALAVRAS_MINIMAS, evidencia_fraca,
                             motivos_de_evidencia_fraca)
from fraus.modelos import Conversa, Mensagem

BASE = datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc)


def _conversa(*falas_do_cliente: str) -> Conversa:
    mensagens = [Mensagem(autor="bot", texto="ola, posso ajudar?", enviada_em=BASE)]
    for fala in falas_do_cliente:
        mensagens.append(Mensagem(autor="cliente", texto=fala, enviada_em=BASE))
    return Conversa(id="c", canal="csv", iniciada_em=BASE, mensagens=mensagens)


def test_uma_unica_mensagem_do_cliente_e_evidencia_fraca():
    assert evidencia_fraca(_conversa("demorou")) is True


def test_poucas_palavras_espalhadas_em_varias_mensagens_ainda_e_fraca():
    """Tres mensagens de uma palavra nao sao mais evidencia que uma de tres.

    Contar so MENSAGENS deixaria passar a conversa de "ok" / "sim" / "tá",
    que e o mesmo vazio dividido em tres.
    """
    assert evidencia_fraca(_conversa("ok", "sim", "ta")) is True


def test_conversa_com_fala_substancial_nao_e_fraca():
    conversa = _conversa(
        "meu boleto venceu ontem e o sistema nao deixa emitir a segunda via",
        "ja tentei pelo aplicativo e pelo site, os dois dao o mesmo erro",
    )
    assert evidencia_fraca(conversa) is False


def test_conversa_sem_fala_do_cliente_nao_e_evidencia_fraca_e_sim_ausencia():
    """"Sem sinal" e "sinal fraco" sao estados DIFERENTES, e a forma tambem.

    Marcar a conversa muda como evidencia fraca faria a cabeca tracejada
    competir com a vazada pela mesma posicao, e a distincao que o produto
    inteiro defende -- ausencia nao e um valor baixo -- se perderia na
    interface exatamente onde ela e mais visivel.
    """
    muda = Conversa(
        id="mudo", canal="csv", iniciada_em=BASE,
        mensagens=[Mensagem(autor="bot", texto="ola", enviada_em=BASE)],
    )
    assert evidencia_fraca(muda) is None


def test_o_limiar_de_palavras_e_parametro_e_o_default_esta_declarado():
    # Duas mensagens, para isolar o criterio de PALAVRAS do de mensagens.
    conversa = _conversa("o pedido chegou", "quebrado hoje")  # 5 palavras
    assert evidencia_fraca(conversa) is False
    assert evidencia_fraca(conversa, palavras_minimas=20) is True
    assert PALAVRAS_MINIMAS == 5


def test_uma_mensagem_SO_e_fraca_mesmo_sendo_substancial():
    """Sem segunda fala nao ha evolucao de humor: a nota inteira pende de uma frase.

    Este e o criterio mais discutivel dos dois, e por isso tem teste proprio
    em vez de sair de carona no outro: quem quiser afrouxa-lo vai ter que
    apagar um teste que diz o que ele defende.
    """
    uma_so = _conversa("o boleto venceu ontem e o sistema nao emite segunda via")
    assert evidencia_fraca(uma_so) is True
    assert motivos_de_evidencia_fraca(uma_so) == ["uma unica mensagem do cliente"]


def test_os_motivos_sao_nomeados_nao_so_o_booleano():
    """A tela precisa dizer POR QUE a evidencia e fraca -- "fraca" nao aciona ninguem."""
    assert motivos_de_evidencia_fraca(_conversa("demorou")) == [
        "uma unica mensagem do cliente",
        "menos de 5 palavras do cliente",
    ]
    assert motivos_de_evidencia_fraca(_conversa("ok", "sim", "ta")) == [
        "menos de 5 palavras do cliente"
    ]
    assert motivos_de_evidencia_fraca(
        _conversa("o pedido chegou quebrado", "hoje de manha")
    ) == []
