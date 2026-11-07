"""Funcao LEVE da Vercel: auth, CRUD, leituras e a regua, sem carregar pesos.

`vercel.json` encaminha para `api/motor.py` as rotas que exigem o `Motor`; o
resto cai aqui. Esta funcao nao inclui `modelos-onnx/` e nunca abre uma sessao
ONNX, entao a instancia fria custa so o import e a migracao do banco. Uma rota
de modelo que chegue aqui por erro de rewrite falha alto, com
`MotorForaDaFuncao`.
"""

from functools import partial

from fraus.api.main import criar_app_padrao
from fraus.api.preguicosa import AplicacaoPreguicosa

app = AplicacaoPreguicosa(partial(criar_app_padrao, com_motor=False))

__all__ = ["app"]
