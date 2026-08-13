from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from dolos.modelos import Conversa, Mensagem


def _ts(segundo: int) -> datetime:
    return datetime(2026, 8, 13, 10, 0, segundo, tzinfo=timezone.utc)


def _conversa(mensagens: list[Mensagem]) -> Conversa:
    return Conversa(
        id="c1",
        canal="csv",
        iniciada_em=_ts(0),
        encerrada_em=None,
        escalou_para_humano=False,
        mensagens=mensagens,
    )


def test_mensagens_cliente_filtra_somente_o_cliente():
    conversa = _conversa([
        Mensagem(autor="cliente", texto="oi", enviada_em=_ts(0)),
        Mensagem(autor="bot", texto="ola", enviada_em=_ts(5)),
        Mensagem(autor="cliente", texto="valeu", enviada_em=_ts(9)),
    ])
    assert [m.texto for m in conversa.mensagens_cliente] == ["oi", "valeu"]


def test_conversa_sem_mensagem_do_cliente_nao_tem_sinal():
    conversa = _conversa([Mensagem(autor="bot", texto="ola", enviada_em=_ts(0))])
    assert conversa.tem_sinal_cliente is False


def test_autor_invalido_e_rejeitado():
    with pytest.raises(ValidationError):
        Mensagem(autor="gerente", texto="oi", enviada_em=_ts(0))


def test_timestamp_naive_e_rejeitado():
    with pytest.raises(ValidationError):
        Mensagem(autor="cliente", texto="oi", enviada_em=datetime(2026, 8, 13, 10, 0, 0))


def test_conversa_iniciada_em_naive_e_rejeitado():
    with pytest.raises(ValidationError):
        Conversa(
            id="c1",
            canal="csv",
            iniciada_em=datetime(2026, 8, 13, 10, 0, 0),
            encerrada_em=None,
            escalou_para_humano=False,
            mensagens=[],
        )


def test_conversa_encerrada_em_naive_e_rejeitado():
    with pytest.raises(ValidationError):
        Conversa(
            id="c1",
            canal="csv",
            iniciada_em=_ts(0),
            encerrada_em=datetime(2026, 8, 13, 10, 0, 0),
            escalou_para_humano=False,
            mensagens=[],
        )
