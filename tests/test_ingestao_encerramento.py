"""`encerrada_em` na borda da ingestao (auditoria de 13/10/2026).

`/ingestao` e o webhook validam pelo mesmo `PedidoIngestao`. Encerramento
antes da ultima fala entrava (`duracao_s: -3600` na lista) e virava duracao
zero no vetor, em silencio; naive nem chegava a ser recusado.
"""

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from fraus.api.esquemas import PedidoIngestao

T = datetime(2026, 9, 15, 10, tzinfo=timezone(timedelta(hours=-3)))
MENSAGENS = [
    {"autor": "cliente", "texto": "oi", "enviada_em": T},
    {"autor": "bot", "texto": "ola", "enviada_em": T + timedelta(minutes=5)},
]


def test_encerramento_antes_da_ultima_fala_e_recusado():
    with pytest.raises(ValidationError, match="encerrada_em"):
        PedidoIngestao(id="x", mensagens=MENSAGENS, encerrada_em=T + timedelta(minutes=1))


def test_encerramento_sem_fuso_e_recusado():
    with pytest.raises(ValidationError, match="encerrada_em"):
        PedidoIngestao(id="x", mensagens=MENSAGENS, encerrada_em=datetime(2026, 9, 15, 11))


def test_encerramento_na_ultima_fala_ou_depois_vale():
    PedidoIngestao(id="x", mensagens=MENSAGENS, encerrada_em=T + timedelta(minutes=5))
    PedidoIngestao(id="x", mensagens=MENSAGENS, encerrada_em=None)
