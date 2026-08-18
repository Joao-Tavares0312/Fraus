"""POST /ingestao -- atendimento vindo de um sistema EXTERNO, pela rede.

E o unico caminho de escrita que nao exige acesso ao disco da maquina: a
importacao le arquivo de uma pasta local, e isto aqui aceita a conversa pela
rede, autenticada por chave de FONTE (`frs_...`).

O CANAL e o da fonte cadastrada, nao o que veio no corpo, e o score e
derivado aqui: quem manda o dado nao escolhe em que canal ele e
contabilizado, do mesmo jeito que nao escolhe a propria nota.
"""

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import ValidationError

from fraus.api.contexto import Contexto, obter_contexto
from fraus.api.esquemas import PedidoIngestao
from fraus.api.seguranca import chave_do_cabecalho, fonte_autorizada
from fraus.indicadores import nota_0_10
from fraus.modelos import Conversa

router = APIRouter()


@router.post("/ingestao", status_code=201)
def ingerir(
    pedido: PedidoIngestao,
    authorization: str | None = Header(default=None),
    ctx: Contexto = Depends(obter_contexto),
) -> dict:
    """Recebe atendimento de um sistema EXTERNO, autenticado por chave.

    E o unico caminho de escrita que nao exige acesso ao disco da maquina:
    a importacao le arquivo de uma pasta local, e isto aqui aceita a
    conversa pela rede.

    O CANAL e o da FONTE cadastrada, nao o que veio no corpo: quem manda o
    dado nao escolhe em que canal ele e contabilizado, do mesmo jeito que
    nao escolhe o proprio score. Fonte desativada recusa -- o interruptor
    da tela de Integracoes precisa de fato desligar alguma coisa.

    Score e categoria sao derivados aqui, como em toda entrada.
    """
    chave = chave_do_cabecalho(authorization)
    fonte = fonte_autorizada(ctx.banco, chave)

    try:
        conversa = Conversa(
            id=pedido.id,
            canal=fonte["canal"],
            iniciada_em=pedido.mensagens[0].enviada_em,
            encerrada_em=pedido.encerrada_em,
            escalou_para_humano=pedido.escalou_para_humano,
            mensagens=sorted(pedido.mensagens, key=lambda m: m.enviada_em),
        )
    except ValidationError as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro

    score = ctx.motor.pontuar_conversa(conversa)
    # UMA leitura de faixa por requisicao: derivar a categoria duas vezes
    # abria janela para a gravacao e a resposta lerem configuracoes
    # diferentes, e as duas precisam contar a mesma historia.
    categoria = ctx.categoria_de(score, ctx.faixas_vigentes())
    ctx.banco.salvar(conversa, score, categoria)
    return {
        "id": conversa.id,
        "canal": conversa.canal,
        "score": score,
        "nota": nota_0_10(score) if score is not None else None,
        "categoria": categoria,
        "fonte": fonte["nome"],
    }
