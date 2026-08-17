"""/acesso/chaves -- as chaves que a dashboard usa para LER a API.

Gerenciar chave e privilegio da MESTRA, nunca de chave de acesso: uma chave
que pode emitir outra chave nao e um posto menor, e o 403 de `exigir_mestra`
e o que separa os dois niveis.

A chave sai EM CLARO uma unica vez, na criacao. O banco guarda so o hash --
um `fraus.db` vazado num backup nao leva credencial junto.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException

from fraus import acesso as acesso_dominio
from fraus import credencial
from fraus.api.contexto import Contexto, obter_contexto
from fraus.api.esquemas import PedidoChaveAcesso
from fraus.api.seguranca import exigir_mestra

router = APIRouter()


@router.get("/acesso/estado")
def estado(ctx: Contexto = Depends(obter_contexto)) -> dict:
    """A autenticacao esta ligada, e de onde vem a mestra.

    PUBLICA por necessidade (ver `seguranca.ISENTAS`): a tela precisa desta
    resposta exatamente quando ainda nao existe credencial nenhuma para
    apresentar. Por isso ela nao carrega dica, hash nem data -- so o suficiente
    para a interface saber o que desenhar, e nada que ajude quem esta do lado
    de fora.
    """
    return {"ligada": ctx.autenticacao_ligada(), "origem": ctx.origem_da_mestra()}


@router.post("/acesso/chaves", status_code=201)
def criar_chave_acesso(
    pedido: PedidoChaveAcesso,
    authorization: str | None = Header(default=None),
    ctx: Contexto = Depends(obter_contexto),
) -> dict:
    """Gera uma chave de acesso e a devolve EM CLARO uma unica vez."""
    exigir_mestra(ctx, authorization)
    registro = ctx.banco.criar_chave_acesso(
        nome=pedido.nome,
        criada_em=datetime.now(timezone.utc).isoformat(),
    )
    chave, chave_hash = acesso_dominio.gerar(registro["id"])
    ctx.banco.gravar_chave_acesso(
        registro["id"], chave_hash=chave_hash, dica=credencial.dica(chave)
    )
    return {
        **registro,
        "dica": credencial.dica(chave),
        "chave": chave,
        "aviso": (
            "Guarde agora: esta chave não pode ser lida de novo. "
            "Revogue e gere outra se perdê-la."
        ),
    }


@router.get("/acesso/chaves")
def listar_chaves_acesso(
    authorization: str | None = Header(default=None),
    ctx: Contexto = Depends(obter_contexto),
) -> list[dict]:
    exigir_mestra(ctx, authorization)
    return ctx.banco.listar_chaves_acesso()


@router.delete("/acesso/chaves/{chave_id}", status_code=204)
def revogar_chave_acesso(
    chave_id: int,
    authorization: str | None = Header(default=None),
    ctx: Contexto = Depends(obter_contexto),
) -> None:
    exigir_mestra(ctx, authorization)
    if not ctx.banco.apagar_chave_acesso(chave_id):
        raise HTTPException(status_code=404, detail="chave nao encontrada")
