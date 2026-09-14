"""/perfis-mapeamento -- o mapeamento de colunas que o analista confirmou.

Um export que o Fraus nao conhece por nome passa pelo mapeador, que infere qual
coluna e texto, autor, data e conversa. O analista confere na previa e, se
quiser, salva: o proximo arquivo com as MESMAS colunas (mesma assinatura) e
lido com esse mapa sem perguntar de novo.

A validacao aqui e a mesma que a leitura faria, adiantada: perfil que nao
serve para ler o arquivo de onde veio nao entra no banco -- descobrir isso so
no proximo upload seria a falha silenciosa adiada.
"""

from fastapi import APIRouter, Depends, HTTPException

from fraus.api.contexto import Contexto, obter_contexto
from fraus.api.esquemas import PedidoPerfilMapeamento
from fraus.ingest.mapeador import OBRIGATORIOS, ORDENS_DE_DATA, SINONIMOS, assinatura

router = APIRouter()


@router.get("/perfis-mapeamento")
def listar(ctx: Contexto = Depends(obter_contexto)) -> list[dict]:
    return ctx.banco.listar_perfis_mapeamento()


@router.post("/perfis-mapeamento", status_code=201)
def salvar(pedido: PedidoPerfilMapeamento, ctx: Contexto = Depends(obter_contexto)) -> dict:
    """Cria, ou edita o perfil que ja existe para estas colunas."""
    colunas = [c.strip() for c in pedido.colunas]
    desconhecidos = sorted(set(pedido.papeis) - set(SINONIMOS))
    if desconhecidos:
        raise HTTPException(
            status_code=400,
            detail=f"papel desconhecido: {', '.join(desconhecidos)}. Papéis: {', '.join(SINONIMOS)}.",
        )
    faltando = [p for p in OBRIGATORIOS if not pedido.papeis.get(p)]
    if faltando:
        raise HTTPException(
            status_code=400,
            detail=f"o perfil precisa dizer a coluna de {', '.join(faltando)}.",
        )
    fora = sorted({c for c in pedido.papeis.values() if c is not None and c not in colunas})
    if fora:
        raise HTTPException(
            status_code=400,
            detail=f"coluna(s) fora do arquivo: {', '.join(fora)}. Colunas: {', '.join(colunas[:12])}.",
        )
    escolhidas = [c for c in pedido.papeis.values() if c is not None]
    if len(escolhidas) != len(set(escolhidas)):
        raise HTTPException(status_code=400, detail="uma coluna não pode fazer dois papéis.")
    if pedido.ordem_data is not None and pedido.ordem_data not in ORDENS_DE_DATA:
        raise HTTPException(
            status_code=400, detail=f"ordem_data precisa ser {' ou '.join(ORDENS_DE_DATA)}"
        )
    return ctx.banco.salvar_perfil_mapeamento(
        pedido.nome.strip(), assinatura(colunas), colunas, pedido.papeis, pedido.ordem_data
    )


@router.delete("/perfis-mapeamento/{perfil_id}", status_code=204)
def apagar(perfil_id: int, ctx: Contexto = Depends(obter_contexto)) -> None:
    if not ctx.banco.apagar_perfil_mapeamento(perfil_id):
        raise HTTPException(status_code=404, detail="perfil de mapeamento nao encontrado")
