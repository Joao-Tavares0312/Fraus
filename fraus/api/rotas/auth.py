"""Autenticacao de USUARIO: registrar, entrar e quem sou.

Usuario e identidade da dashboard -- quem esta olhando a tela e com qual
papel. Nao substitui as credenciais tecnicas: a mestra e as chaves `fra_`
autenticam processos, as `frs_` autenticam fontes, e todas continuam.

O cadastro nasce `usuario`. Nascer `dev` exige o codigo de convite
(FRAUS_CODIGO_DEV, ambiente): privilegio se liga por decisao explicita do
operador, nunca por padrao. Ver a spec de 31/08/2026, §2.3.
"""

import hmac
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException

from fraus import token_acesso, usuarios
from fraus.api.contexto import Contexto, obter_contexto
from fraus.api.esquemas import PedidoCadastro, PedidoEntrada
from fraus.db import ErroDeIntegridade
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
    return {
        "disponivel": ctx.jwt_segredo is not None,
        # Se o cadastro exige codigo. A tela precisa saber para nao rotular o
        # campo como "(opcional)" numa instalacao onde ele e obrigatorio --
        # formulario que mente sobre o que exige produz um 403 que parece
        # defeito. Nao vaza segredo: diz que EXISTE exigencia, nunca qual.
        "cadastro_exige_codigo": ctx.codigo_convite is not None,
    }


def _confere_codigo(oferecido: str | None, esperado: str | None) -> bool:
    """Comparacao em tempo constante que trata ausencia como recusa."""
    if not oferecido or not esperado:
        return False
    return hmac.compare_digest(
        oferecido.encode("utf-8"), esperado.encode("utf-8")
    )


def papel_do_cadastro(ctx: Contexto, codigo: str | None) -> str:
    """Com qual papel esta conta nasce -- ou 403 se ela nao pode nascer.

    DOIS CODIGOS, DOIS PRIVILEGIOS DIFERENTES:

    * `FRAUS_CODIGO_DEV` promove a `dev`, e sempre foi assim;
    * `FRAUS_CODIGO_CONVITE` decide se a pessoa PODE CRIAR CONTA. Ele nasceu
      em 02/09/2026, quando a API saiu do `localhost` para um tunel publico.

    POR QUE O SEGUNDO PRECISOU EXISTIR. `POST /auth/registrar` e isento de
    credencial por desenho -- tem de ser, porque quem se cadastra ainda nao tem
    nenhuma. Isso era inofensivo enquanto a API so existia na maquina de quem a
    roda. Publicada, virava isto: qualquer pessoa que descobrisse o endereco
    fazia um POST, recebia um JWT e passava a LER todos os atendimentos --
    porque `acesso_autorizado` aceita qualquer sessao valida do mesmo jeito que
    aceita a mestra. A mestra protegia a leitura contra o anonimo, e deixar de
    ser anonimo era de graca. Reproduzido contra a instalacao publicada antes
    deste conserto.

    SEM `FRAUS_CODIGO_CONVITE` NADA MUDA: a instalacao segue aberta, que e o
    comportamento certo para quem roda em casa e nao quer digitar codigo para
    entrar na propria ferramenta. A exigencia e uma decisao de quem publica.

    A recusa e SEMPRE a mesma mensagem, para codigo errado, codigo ausente e
    variavel nao definida. Diferenciar contaria a configuracao do servidor a
    quem esta do lado de fora.
    """
    if _confere_codigo(codigo, ctx.codigo_dev):
        return "dev"
    # Codigo oferecido que nao e o de dev so pode ser o de convite. Oferecer um
    # codigo errado NUNCA rebaixa em silencio: quem digitou queria algo.
    if codigo and not _confere_codigo(codigo, ctx.codigo_convite):
        raise HTTPException(status_code=403, detail="codigo de convite invalido")
    if ctx.codigo_convite is not None and not codigo:
        raise HTTPException(
            status_code=403,
            detail="esta instalacao exige um codigo de convite para criar conta",
        )
    return "usuario"


@router.post("/auth/registrar", status_code=201)
def registrar(pedido: PedidoCadastro, ctx: Contexto = Depends(obter_contexto)) -> dict:
    papel = papel_do_cadastro(ctx, pedido.codigo_dev)
    agora = datetime.now(timezone.utc).isoformat()
    try:
        return ctx.banco.criar_usuario(
            nome=pedido.nome,
            email=pedido.email,
            senha_hash=usuarios.gerar_hash(pedido.senha),
            papel=papel,
            criado_em=agora,
        )
    except ErroDeIntegridade:
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
