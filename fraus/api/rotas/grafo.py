"""GET /grafo -- a memoria do sistema como grafo.

Rota FINA: toda a montagem mora em `fraus/grafo.py`, que e modulo puro. Aqui
so acontecem a validacao dos parametros e a leitura do banco.

Ela NAO carrega modelo e NAO chama o `Motor` para pontuar nada: le o que ja
esta gravado e conta. O unico dado que vem do modelo e o eixo global do fusor
-- coeficiente ja treinado, em disco, sem inferencia.
"""

from fastapi import APIRouter, Depends, HTTPException

from fraus.api.contexto import Contexto, obter_contexto
from fraus.grafo import CAMADAS, TETO_TERMOS_PADRAO, TODAS_AS_CAMADAS, montar_grafo

# Teto de termos que o cliente PODE pedir. Sem ele, `?teto_termos=79190`
# devolveria o SentiLex inteiro numa resposta so.
TETO_TERMOS_GRAFO = 500

router = APIRouter()


def _camadas_ou_400(bruto: str | None) -> frozenset[str]:
    """Camadas pedidas, ou 400 nomeando a desconhecida.

    Ignorar o valor invalido devolveria um grafo DIFERENTE do pedido sem
    avisar ninguem -- e o tipo de silencio que faz alguem concluir que a
    camada esta vazia quando na verdade ela nunca foi consultada.
    """
    if not bruto:
        return TODAS_AS_CAMADAS
    pedidas = [parte.strip() for parte in bruto.split(",") if parte.strip()]
    desconhecidas = [parte for parte in pedidas if parte not in CAMADAS]
    if desconhecidas:
        raise HTTPException(
            status_code=400,
            detail=f"camada desconhecida: {', '.join(desconhecidas)}. Conhecidas: {', '.join(CAMADAS)}",
        )
    return frozenset(pedidas)


@router.get("/grafo")
def grafo(
    de: str | None = None,
    ate: str | None = None,
    camadas: str | None = None,
    teto_termos: int = TETO_TERMOS_PADRAO,
    ctx: Contexto = Depends(obter_contexto),
) -> dict:
    """Nos e arestas da memoria do sistema, no recorte pedido."""
    if teto_termos < 1 or teto_termos > TETO_TERMOS_GRAFO:
        raise HTTPException(
            status_code=400,
            detail=f"teto_termos precisa estar entre 1 e {TETO_TERMOS_GRAFO}",
        )

    pedidas = _camadas_ou_400(camadas)
    registros = ctx.registros_do_recorte(de, ate)

    # Fusor sem treino devolve `{}`, e o grafo omite as arestas de feature.
    # Nao ha try/except aqui de proposito: se o `Motor` quebrar ao ler um
    # coeficiente ja carregado, isso e defeito real e deve aparecer.
    eixo = ctx.motor.eixo_global()

    return montar_grafo(
        registros,
        ctx.faixas_vigentes(),
        camadas=pedidas,
        teto_termos=teto_termos,
        eixo=eixo,
        fontes=ctx.banco.listar_fontes() if "proveniencia" in pedidas else (),
        importacoes=ctx.banco.listar_importacoes() if "proveniencia" in pedidas else (),
    )
