"""/acesso -- quem liga a autenticacao, e quem pode ler a API depois.

Tres rotas, tres papeis:

- `GET /acesso/estado` diz se a autenticacao esta ligada e de onde vem a
  mestra. Publica, porque a tela precisa dela quando ainda nao ha credencial.
- `POST /acesso/mestra` LIGA a autenticacao (ou rotaciona a mestra). E o
  caminho que dispensa o terminal.
- `/acesso/chaves` emite e revoga as chaves de acesso da dashboard.

Gerenciar chave e privilegio da MESTRA, nunca de chave de acesso: uma chave
que pode emitir outra chave nao e um posto menor, e o 403 de `exigir_mestra`
e o que separa os dois niveis.

Toda chave sai EM CLARO uma unica vez, na criacao. O banco guarda so o hash --
um `fraus.db` vazado num backup nao leva credencial junto.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException

from fraus import acesso as acesso_dominio
from fraus import credencial
from fraus.api.contexto import Contexto, obter_contexto
from fraus.api.esquemas import PedidoChaveAcesso
from fraus.api.seguranca import chave_bearer, e_mestra, exigir_mestra

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


@router.post("/acesso/mestra", status_code=201)
def criar_ou_rotacionar_mestra(
    authorization: str | None = Header(default=None),
    ctx: Contexto = Depends(obter_contexto),
) -> dict:
    """Liga a autenticacao, ou troca a mestra de quem ja esta dentro.

    Dois caminhos, decididos pelo ESTADO -- nunca pelo que o cliente pede:

    1. **Sem mestra nenhuma.** Gera a mestra e emite JUNTO uma chave de acesso
       `dashboard`. As duas saem em claro, uma unica vez. A segunda nao e
       conveniencia: sem ela o clique deixaria a propria dashboard em 401, e o
       passo seguinte seria o terminal que este caminho veio eliminar.
    2. **Ja ligada pelo banco.** Exige a mestra ATUAL e rotaciona: a antiga
       deixa de valer no mesmo instante. Sem a mestra atual e 409, nunca um 201
       que sobrescreveria a credencial de quem esta dentro -- essa rota fica
       aberta enquanto a API esta aberta, e um 201 aqui seria a porta para
       alguem tomar a API antes do dono.

    Mestra vinda do AMBIENTE recusa as duas coisas: a variavel vence o banco,
    entao gravar por cima criaria duas verdades com a do ambiente ganhando --
    a rota responderia 201 sem mudar nada, que e pior do que recusar.

    Nao existe caminho para DESLIGAR. Um botao que baixa a defesa nao tem
    contrapartida de risco aceitavel; desligar continua sendo trabalho de
    ambiente (apagar a variavel e a linha do banco).
    """
    if ctx.chave_mestra is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                "a chave mestra vem do ambiente (FRAUS_CHAVE_MESTRA) e tem "
                "precedencia sobre a gravada. Troque a variavel e reinicie a API."
            ),
        )

    primeiro_uso = ctx.banco.hash_da_chave_mestra() is None
    if not primeiro_uso:
        chave_recebida = chave_bearer(authorization)
        if chave_recebida is None or not e_mestra(ctx, chave_recebida):
            raise HTTPException(
                status_code=409,
                detail=(
                    "a autenticacao ja esta ligada. Para trocar a chave mestra, "
                    "apresente a atual em Authorization: Bearer <chave>."
                ),
            )

    agora = datetime.now(timezone.utc).isoformat()
    mestra, mestra_hash = acesso_dominio.gerar_mestra()
    ctx.banco.gravar_chave_mestra(
        chave_hash=mestra_hash, dica=credencial.dica(mestra), criada_em=agora
    )

    chave_de_acesso = None
    if primeiro_uso:
        registro = ctx.banco.criar_chave_acesso(nome="dashboard", criada_em=agora)
        chave_de_acesso, hash_de_acesso = acesso_dominio.gerar(registro["id"])
        ctx.banco.gravar_chave_acesso(
            registro["id"],
            chave_hash=hash_de_acesso,
            dica=credencial.dica(chave_de_acesso),
        )

    return {
        "chave_mestra": mestra,
        # `null` na rotacao: a chave de acesso da dashboard continua valendo, e
        # emitir outra a cada rotacao encheria a tabela de credencial viva que
        # ninguem sabe quem usa.
        "chave_acesso": chave_de_acesso,
        "dica": credencial.dica(mestra),
        "aviso": (
            "Guarde agora: estas chaves não podem ser lidas de novo. "
            "O servidor guarda apenas o hash delas."
        ),
    }


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
