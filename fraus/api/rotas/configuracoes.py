"""GET e PUT /configuracoes -- as faixas de NPS e os cortes de latencia."""

from fastapi import APIRouter, Depends, HTTPException

from fraus.api.contexto import Contexto, obter_contexto
from fraus.configuracao import PADROES as CONFIGURACAO_DE_FABRICA
from fraus.configuracao import carregar as carregar_configuracao
from fraus.configuracao import salvar as salvar_configuracao

router = APIRouter()


@router.get("/configuracoes")
def configuracoes(ctx: Contexto = Depends(obter_contexto)) -> dict:
    """Configuracao vigente E a de fabrica -- a tela precisa das duas.

    Sem a de fabrica, "voltar ao padrao" seria um botao que a interface
    teria que preencher com numeros digitados de novo, e digitar de novo e
    exatamente como faixa duplicada nasce.
    """
    return {
        "vigente": carregar_configuracao(ctx.banco),
        "fabrica": CONFIGURACAO_DE_FABRICA,
    }

@router.put("/configuracoes")
def configurar(pedido: dict, ctx: Contexto = Depends(obter_contexto)) -> dict:
    """Grava as chaves enviadas. Chave desconhecida ou valor invalido e 400.

    O corpo e um dicionario cru de proposito: chave desconhecida precisa
    chegar a validacao para ser NOMEADA no erro, e nao ser descartada em
    silencio por um modelo de entrada tolerante.
    """
    try:
        vigente = salvar_configuracao(ctx.banco, pedido)
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro
    return {"vigente": vigente, "fabrica": CONFIGURACAO_DE_FABRICA}
