"""Casca ASGI que adia a montagem da API para a primeira requisicao.

A Vercel tem um teto curto para IMPORTAR a aplicacao, separado dos segundos da
invocacao. Montar a API real no import (banco, migracao e, na funcao do motor,
o aquecimento dos grafos ONNX) ultrapassa esse teto. Esta casca nasce
imediatamente e chama a fabrica na primeira requisicao; erro de modelo continua
propagando alto, sem duble e sem resposta parcial.

Mora no pacote, e nao em `api/`, porque cada `.py` dentro de `api/` vira uma
funcao da Vercel.
"""

import threading
from collections.abc import Callable

from fastapi import FastAPI


class AplicacaoPreguicosa:
    def __init__(self, fabrica: Callable[[], FastAPI]) -> None:
        self._fabrica = fabrica
        self._app = None
        self._trava = threading.Lock()

    def _carregar(self):
        if self._app is None:
            with self._trava:
                if self._app is None:
                    self._app = self._fabrica()
        return self._app

    async def __call__(self, scope, receive, send):
        await self._carregar()(scope, receive, send)
