"""POST /ingestao -- atendimento vindo de um sistema EXTERNO, pela rede.

E um dos dois caminhos de escrita que nao exigem acesso ao disco da maquina --
o outro e `POST /integracoes/webhook/{fonte_id}`, que autentica por ASSINATURA
em vez de chave. A importacao le arquivo de uma pasta local; estes dois aceitam
a conversa pela rede.

O que os dois fazem com a conversa depois de autenticada e o MESMO codigo
(`fraus/api/registro.py`), de proposito: o canal vem da fonte cadastrada e o
score e derivado no servidor, e duas copias dessa regra divergiriam.
"""

from fastapi import APIRouter, Depends, Header, Request

from fraus.api.contexto import Contexto, obter_contexto
from fraus.api.esquemas import PedidoIngestao
from fraus.api.registro import registrar_conversa
from fraus.api.seguranca import chave_do_cabecalho, fonte_autorizada
from fraus.api.vazao import barrar_se_exceder

router = APIRouter()


@router.post("/ingestao", status_code=201)
def ingerir(
    request: Request,
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
    # DEPOIS de autenticar e ANTES de pontuar, e as duas coisas importam: so
    # aqui existe uma identidade que o lado de fora nao forja (a fonte, nao a
    # chave crua), e o que o teto protege e a inferencia que vem em seguida --
    # o Motor inteiro em CPU por conversa. Ver `fraus/api/vazao.py`.
    barrar_se_exceder(request.app.state.limitador_de_ingestao, str(fonte["id"]))
    return registrar_conversa(ctx, pedido, fonte)
