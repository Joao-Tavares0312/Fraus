"""/lexico/curado -- o que o analista ensinou ao lexico.

A FRONTEIRA QUE ESTE MODULO SUSTENTA: o analista edita o DICIONARIO, nunca a
nota. O peso curado alimenta o sinal lexico e o fusor treinado decide quanto
isso vale no score -- exatamente como ja faz com as 79.189 formas do SentiLex.

A validacao de escala nao e burocracia. Palavra e -1/0/+1 porque e essa a escala
em que `lexico_polaridade_media` foi treinada; um -0,7 ali injetaria na feature
um valor que o fusor nunca viu, e o efeito no score deixaria de ser previsivel.
Emoji e continuo em [-1, 1] porque e a escala do Emoji Sentiment Ranking.

Nao e privilegio de mestra: curar lexico e trabalho do analista, nao
administracao de credencial. Vale a chave de acesso como o resto da API.
"""

import emoji as lib_emoji
from fastapi import APIRouter, Depends, HTTPException

from fraus.api.contexto import Contexto, obter_contexto
from fraus.api.esquemas import PedidoCurado

router = APIRouter()

PESOS_DE_PALAVRA = (-1, 0, 1)


def _validar(pedido: PedidoCurado) -> tuple[str, float]:
    """Normaliza o termo e impoe a escala do tipo. Devolve (termo, peso)."""
    if pedido.tipo == "palavra":
        if pedido.peso not in PESOS_DE_PALAVRA:
            raise HTTPException(
                status_code=400,
                detail=(
                    "peso de palavra e -1 (negativa), 0 (neutra) ou 1 (positiva)"
                    " -- a mesma escala do SentiLex-PT02"
                ),
            )
        # Minusculas, como o lexicon indexa. Sem isto "Lentissimo" e
        # "lentissimo" virariam duas linhas, e o indice unico nao pegaria.
        return pedido.termo.strip().lower(), float(pedido.peso)

    if not -1 <= pedido.peso <= 1:
        raise HTTPException(
            status_code=400,
            detail="peso de emoji fica entre -1 e 1 -- a escala do Emoji Sentiment Ranking",
        )
    termo = pedido.termo.strip()
    achados = lib_emoji.emoji_list(termo)
    # A mesma biblioteca que o sinal de emoji ja usa, e nunca regex propria:
    # duas nocoes de "o que e um emoji" divergem na primeira sequencia com
    # modificador de tom de pele.
    if len(achados) != 1 or achados[0]["emoji"] != termo:
        raise HTTPException(status_code=400, detail="informe exatamente um emoji")
    return termo, float(pedido.peso)


@router.get("/lexico/curado")
def listar(ctx: Contexto = Depends(obter_contexto)) -> list[dict]:
    return ctx.banco.listar_curados()


@router.post("/lexico/curado", status_code=201)
def curar(pedido: PedidoCurado, ctx: Contexto = Depends(obter_contexto)) -> dict:
    """Cadastra ou EDITA um termo. Vale da proxima pontuacao em diante."""
    termo, peso = _validar(pedido)
    return ctx.banco.curar(pedido.tipo, termo, peso, pedido.motivo)


@router.delete("/lexico/curado/{curado_id}", status_code=204)
def revogar(curado_id: int, ctx: Contexto = Depends(obter_contexto)) -> None:
    if not ctx.banco.revogar_curado(curado_id):
        raise HTTPException(status_code=404, detail="termo curado nao encontrado")
