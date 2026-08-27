"""O miolo das duas rotas de ENTRADA: montar, pontuar, derivar e gravar.

Existe para que `POST /ingestao` (chave de fonte) e
`POST /integracoes/webhook/{fonte_id}` (assinatura) nao mantenham duas copias
da mesma regra. Duas copias divergem, e a invariante 3 do projeto -- veredito
derivado no servidor, nunca aceito do cliente -- nasceu exatamente de uma
divergencia dessas. A que envelhece e sempre a que ninguem olha.
"""

from fastapi import HTTPException
from pydantic import ValidationError

from fraus.api.contexto import Contexto
from fraus.api.esquemas import PedidoIngestao
from fraus.indicadores import nota_0_10
from fraus.modelos import Conversa


def registrar_conversa(ctx: Contexto, pedido: PedidoIngestao, fonte: dict) -> dict:
    """Grava o atendimento e devolve o veredito DERIVADO.

    O CANAL e o da fonte cadastrada, nao o que veio no corpo: quem manda o dado
    nao escolhe em que canal ele e contabilizado, do mesmo jeito que nao escolhe
    a propria nota.
    """
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

    # UMA leitura de curadoria, e e a MESMA que grava a versao: reler abriria
    # janela para pontuar com um lexico e marcar com a versao de outro.
    curadoria = ctx.curadoria_vigente()
    score = ctx.motor.pontuar_conversa(conversa, curadoria)
    # UMA leitura de faixa por requisicao: derivar a categoria duas vezes abria
    # janela para a gravacao e a resposta lerem configuracoes diferentes, e as
    # duas precisam contar a mesma historia.
    categoria = ctx.categoria_de(score, ctx.faixas_vigentes())
    ctx.banco.salvar(conversa, score, categoria, lexico_versao=curadoria.versao)
    return {
        "id": conversa.id,
        "canal": conversa.canal,
        "score": score,
        "nota": nota_0_10(score) if score is not None else None,
        "categoria": categoria,
        "fonte": fonte["nome"],
    }
