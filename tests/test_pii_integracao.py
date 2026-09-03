"""PII nao pode sobreviver a entrada da API -- ver `fraus/seguranca/pii.py`.

Nao ha `conftest.py` no projeto nem fixture `ctx_de_teste` reaproveitavel:
`tests/test_api.py` monta banco temporario + motor duble e sobe a app inteira
via `TestClient(criar_app(...))`, mas este teste chama `registrar_conversa`
direto -- sem HTTP -- entao precisa de um `Contexto` de verdade, nao de um
cliente HTTP. A fixture abaixo segue o mesmo padrao de montagem de
`tests/test_api.py` (banco `Banco(tmp_path / "fraus.db")` migrado + motor
duble), so que devolve o `Contexto` em vez do `TestClient`.
"""

from datetime import datetime, timezone

import pytest

from fraus.api.contexto import Contexto
from fraus.api.esquemas import PedidoIngestao
from fraus.db import Banco


class MotorFalso:
    """Motor duble minimo: so o que `registrar_conversa` chama."""

    def pontuar_conversa(self, conversa, curadoria=None):
        return 90.0


@pytest.fixture
def ctx_de_teste(tmp_path):
    banco = Banco(tmp_path / "fraus.db")
    banco.migrar()
    return Contexto(banco=banco, motor=MotorFalso(), raiz=tmp_path, chave_mestra=None)


def test_registrar_conversa_grava_texto_mascarado(ctx_de_teste):
    """PII nao pode chegar ao banco. O texto gravado ja vem mascarado."""
    from fraus.api.registro import registrar_conversa

    base = datetime(2026, 9, 3, 10, 0, 0, tzinfo=timezone.utc)
    pedido = PedidoIngestao(
        id="c-pii",
        encerrada_em=base,
        escalou_para_humano=False,
        mensagens=[
            {
                "autor": "cliente",
                "texto": "meu cpf e 529.982.247-25 e o email joao@exemplo.com",
                "enviada_em": base,
            }
        ],
    )
    registrar_conversa(ctx_de_teste, pedido, {"canal": "csv", "nome": "teste"})

    conversa, _score = ctx_de_teste.banco.todas()[0]
    texto = conversa.mensagens[0].texto
    assert "529.982.247-25" not in texto
    assert "joao@exemplo.com" not in texto
    assert "[CPF]" in texto
    assert "[EMAIL]" in texto
