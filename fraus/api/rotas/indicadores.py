"""Os agregados: /indicadores, /lexico e /serie-temporal.

Existem para tirar a agregacao do CLIENTE. Sem eles, montar o grafico ou os
cartoes exigia baixar a TRANSCRICAO de toda conversa do recorte -- o N+1 que
a dashboard fazia. O recorte de periodo acontece aqui, no servidor, com as
duas pontas INCLUSIVAS.
"""

from fastapi import APIRouter, Depends

from fraus.api.contexto import Contexto, obter_contexto
from fraus.api.periodo import no_recorte, recorte_ou_400
from fraus.indicadores import (calcular_csat, calcular_nps, containment_rate,
                               lexico_por_classe, serie_diaria,
                               tempo_mediano_resposta)

router = APIRouter()


@router.get("/indicadores")
def indicadores(
    de: str | None = None,
    ate: str | None = None,
    ctx: Contexto = Depends(obter_contexto),
) -> dict:
    """Indicadores agregados, com recorte opcional de periodo.

    Com `de`/`ate`, os numeros respondem SO pelo recorte -- e o que tira
    da dashboard a agregacao no cliente que ela fazia com filtro ativo.
    `tempo_mediano_resposta_s` e derivado dos timestamps na leitura
    (latencia nunca e persistida) e vem `null` sem nenhum par
    cliente -> resposta, nunca zero.
    """
    registros = ctx.registros_do_recorte(de, ate)
    conversas = [conversa for conversa, _ in registros]
    scores = [score for _, score in registros if score is not None]
    return {
        "nps": calcular_nps(scores, ctx.faixas_vigentes()),
        "csat": calcular_csat(scores),
        "containment_rate": containment_rate(conversas),
        "total_conversas": len(conversas),
        "sem_sinal": len(conversas) - len(scores),
        "tempo_mediano_resposta_s": tempo_mediano_resposta(registros),
    }


@router.get("/lexico")
def lexico(
    de: str | None = None,
    ate: str | None = None,
    ctx: Contexto = Depends(obter_contexto),
) -> dict:
    """Palavras e emojis caracteristicos por categoria, no recorte pedido.

    Existia so no cliente, que baixava toda transcricao para contar -- o
    ultimo N+1 da visao geral. A ordenacao e por DISTINCAO: o termo que
    aparece em toda parte nao explica classe nenhuma.
    """
    registros = ctx.registros_do_recorte(de, ate)
    return {"classes": lexico_por_classe(registros, ctx.faixas_vigentes())}


@router.get("/serie-temporal")
def serie_temporal(
    de: str | None = None,
    ate: str | None = None,
    ctx: Contexto = Depends(obter_contexto),
) -> dict:
    """NPS inferido x latencia mediana por dia, com recorte de periodo.

    Existe para tirar da dashboard o N+1 que ela fazia: sem este endpoint,
    montar o grafico exigia baixar a TRANSCRICAO de toda conversa do
    recorte so para ler timestamps. As duas pontas do recorte sao
    INCLUSIVAS, que e como quem opera le "de 01/03 ate 07/03".
    """
    inicio, fim = recorte_ou_400(de, ate)
    registros = [
        (conversa, score)
        for conversa, score in ctx.banco.todas()
        if no_recorte(conversa.iniciada_em, inicio, fim)
    ]
    return {
        "de": inicio.isoformat() if inicio else None,
        "ate": fim.isoformat() if fim else None,
        "pontos": serie_diaria(registros, ctx.faixas_vigentes()),
    }
