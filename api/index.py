"""Entrada ASGI da Vercel com carga do motor dentro da primeira chamada.

A Vercel tem um teto curto para IMPORTAR a aplicacao, separado dos 300 s da
invocacao. Construir os tres grafos ONNX no import ultrapassa esse teto. Esta
casca nasce imediatamente e monta a API real na primeira requisicao; erro de
modelo continua propagando alto, sem duble e sem resposta parcial.
"""

import threading

from fraus.api.main import criar_app_padrao


class AplicacaoPreguicosa:
    def __init__(self) -> None:
        self._app = None
        self._trava = threading.Lock()

    def _carregar(self):
        if self._app is None:
            with self._trava:
                if self._app is None:
                    self._app = criar_app_padrao()
        return self._app

    async def __call__(self, scope, receive, send):
        await self._carregar()(scope, receive, send)


app = AplicacaoPreguicosa()

__all__ = ["app"]
