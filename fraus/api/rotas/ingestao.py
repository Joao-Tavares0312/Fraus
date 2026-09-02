"""POST /ingestao -- atendimento vindo de um sistema EXTERNO, pela rede.

E um dos dois caminhos de escrita que nao exigem acesso ao disco da maquina --
o outro e `POST /integracoes/webhook/{fonte_id}`, que autentica por ASSINATURA
em vez de chave. A importacao le arquivo de uma pasta local; estes dois aceitam
a conversa pela rede.

O que os dois fazem com a conversa depois de autenticada e o MESMO codigo
(`fraus/api/registro.py`), de proposito: o canal vem da fonte cadastrada e o
score e derivado no servidor, e duas copias dessa regra divergiriam.
"""

from fastapi import APIRouter, Depends, Header

from fraus.api.contexto import Contexto, obter_contexto
from fraus.api.esquemas import PedidoIngestao
from fraus.api.registro import registrar_conversa
from fraus.api.seguranca import chave_do_cabecalho, fonte_autorizada

router = APIRouter()


@router.post("/ingestao", status_code=201)
def ingerir(
    pedido: PedidoIngestao,
    authorization: str | None = Header(default=None),
    ctx: Contexto = Depends(obter_contexto),
) -> dict:
    """Recebe atendimento de um sistema EXTERNO, autenticado por chave de fonte.

    Fonte desativada recusa com 403 (dentro de `fonte_autorizada`) -- o
    interruptor da tela de Integracoes precisa de fato desligar alguma coisa.

    Score, nota e categoria sao derivados em `registrar_conversa`, como em toda
    entrada, e ignorados se vierem no corpo.
    """
    chave = chave_do_cabecalho(authorization)
    fonte = fonte_autorizada(ctx.banco, chave)
    return registrar_conversa(ctx, pedido, fonte)
