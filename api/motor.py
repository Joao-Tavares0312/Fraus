"""Funcao do MOTOR da Vercel: as rotas que leem texto com os tres BERTimbau.

Recebe so o que `vercel.json` encaminha para `/api/motor` (analise, ingestao,
webhook, repontuacao, simulador, drivers, grafo e `/saude`). Carrega os grafos
ONNX no aquecimento do boot; falha de modelo propaga alto, sem duble.
"""

from fraus.api.main import criar_app_padrao
from fraus.api.preguicosa import AplicacaoPreguicosa

app = AplicacaoPreguicosa(criar_app_padrao)

__all__ = ["app"]
