"""Autenticacao de USUARIO: registrar, entrar e quem sou.

Usuario e identidade da dashboard -- quem esta olhando a tela e com qual
papel. Nao substitui as credenciais tecnicas: a mestra e as chaves `fra_`
autenticam processos, as `frs_` autenticam fontes, e todas continuam.

O cadastro nasce `usuario`. Nascer `dev` exige o codigo de convite
(FRAUS_CODIGO_DEV, ambiente): privilegio se liga por decisao explicita do
operador, nunca por padrao. Ver a spec de 31/08/2026, §2.3.
"""

import hmac
import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException

from fraus import token_acesso, usuarios
from fraus.api.contexto import Contexto, obter_contexto
from fraus.api.esquemas import PedidoCadastro, PedidoEntrada
from fraus.api.seguranca import chave_do_cabecalho

router = APIRouter()

# A recusa de login e UNICA para e-mail inexistente e senha errada: qualquer
# diferenca -- de status, de texto ou de tempo (ver usuarios.confere) --
# contaria a quem tenta quais e-mails tem conta.
_RECUSA_UNIFORME = "e-mail ou senha invalidos"


@router.get("/auth/estado")
def estado(ctx: Contexto = Depends(obter_contexto)) -> dict:
    """Se o login de usuario EXISTE nesta instalacao -- nao quem esta logado.

    A dashboard so exige login quando ha como logar: sem FRAUS_JWT_SEGREDO nao
    existe token possivel, e mandar o modo aberto para uma tela de entrar que
    responde 503 trancaria a instalacao local para fora. Publica pelo mesmo
    argumento de /acesso/estado: e a resposta que diz a tela se ha o que
    apresentar, e nao devolve segredo nenhum -- so o fato de existir.
    """
    return {"disponivel": ctx.jwt_segredo is not None}


@router.post("/auth/registrar", status_code=201)
def registrar(pedido: PedidoCadastro, ctx: Contexto = Depends(obter_contexto)) -> dict:
    papel = "usuario"
    if pedido.codigo_dev:
        # Codigo errado e 403 explicito, nao rebaixamento silencioso: quem
        # digitou o codigo queria ser dev, e nascer usuario sem aviso e a
        # falha silenciosa da casa. Sem FRAUS_CODIGO_DEV definida a recusa e a
        # MESMA -- dizer "a variavel nao esta definida" a um anonimo
        # descreveria a configuracao do servidor para quem esta de fora.
        confere = ctx.codigo_dev is not None and hmac.compare_digest(
            pedido.codigo_dev.encode("utf-8"), ctx.codigo_dev.encode("utf-8")
        )
        if not confere:
            raise HTTPException(status_code=403, detail="codigo de convite invalido")
        papel = "dev"
    agora = datetime.now(timezone.utc).isoformat()
    try:
        return ctx.banco.criar_usuario(
            nome=pedido.nome,
            email=pedido.email,
            senha_hash=usuarios.gerar_hash(pedido.senha),
            papel=papel,
            criado_em=agora,
        )
    except sqlite3.IntegrityError:
        # A unicidade e garantia do banco; aqui ela vira 409. Dizer que o
        # e-mail ja tem conta e o que permite a pessoa ir ao login -- e o
        # cadastro ja confirma existencia por natureza.
        raise HTTPException(
            status_code=409, detail="ja existe uma conta com este e-mail"
        )


@router.post("/auth/entrar")
def entrar(pedido: PedidoEntrada, ctx: Contexto = Depends(obter_contexto)) -> dict:
    if ctx.jwt_segredo is None:
        # Culpa do AMBIENTE, nao de quem chamou -- o mesmo contrato do webhook
        # sem variavel de segredo: 503, nunca 401.
        raise HTTPException(
            status_code=503,
            detail="autenticacao indisponivel: FRAUS_JWT_SEGREDO nao definida",
        )
    usuario = ctx.banco.buscar_usuario_por_email(pedido.email)
    guardado = ctx.banco.hash_da_senha(usuario["id"]) if usuario is not None else None
    # `confere` deriva o scrypt MESMO sem registro guardado -- o tempo de
    # resposta nao conta se o e-mail existe.
    if not usuarios.confere(pedido.senha, guardado) or usuario is None:
        raise HTTPException(status_code=401, detail=_RECUSA_UNIFORME)
    if not usuario["ativo"]:
        # 403, nao 401: a credencial esta certa, o que esta desligada e a
        # conta -- o mesmo contrato da fonte desativada.
        raise HTTPException(status_code=403, detail="esta conta esta desativada")
    token = token_acesso.emitir(
        usuario_id=usuario["id"],
        papel=usuario["papel"],
        segredo=ctx.jwt_segredo,
        agora=datetime.now(timezone.utc),
    )
    return {"token": token, "usuario": usuario}


@router.get("/auth/eu")
def eu(
    ctx: Contexto = Depends(obter_contexto),
    authorization: str | None = Header(default=None),
) -> dict:
    """A ficha de quem esta no token -- lida do BANCO, nao do payload.

    O token e a sessao; o banco e o estado atual. Ler daqui e o que faz a
    conta desativada (ou apagada) parar de responder na hora, sem esperar o
    token expirar.
    """
    if ctx.jwt_segredo is None:
        raise HTTPException(
            status_code=503,
            detail="autenticacao indisponivel: FRAUS_JWT_SEGREDO nao definida",
        )
    token = chave_do_cabecalho(authorization)
    sessao = token_acesso.conferir(
        token, ctx.jwt_segredo, agora=datetime.now(timezone.utc)
    )
    usuario = (
        ctx.banco.buscar_usuario(sessao["usuario_id"]) if sessao is not None else None
    )
    if usuario is None or not usuario["ativo"]:
        raise HTTPException(
            status_code=401,
            detail="sessao invalida ou expirada",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return usuario
