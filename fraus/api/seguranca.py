"""As credenciais da API, num lugar so.

Sao DUAS, e elas nao se substituem:

- **chave de acesso** (`fra_...`) ou a **mestra**: exigidas em toda rota
  quando ha mestra definida. Sem mestra, a API e aberta -- o modo local
  documentado no README.
- **chave de fonte** (`frs_...`): a unica credencial aceita em `POST
  /ingestao`, que so escreve. Uma credencial por rota.

Gerenciar chave (criar, listar, revogar) e privilegio exclusivo da mestra:
uma chave que pode emitir outra chave nao seria um posto menor.
"""

import hmac

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from fraus import acesso, credencial
from fraus.api.contexto import Contexto
from fraus.db import Banco


# Rotas que o middleware de chave de acesso NAO cobre, cada uma por um motivo
# proprio: /ingestao tem credencial de FONTE (uma credencial por rota), e
# /acesso/estado precisa responder a quem ainda nao tem credencial nenhuma --
# e a resposta que diz a tela se ha o que apresentar.
ISENTAS = ("/ingestao", "/acesso/estado")


def chave_bearer(authorization: str | None) -> str | None:
    """A chave de um `Authorization: Bearer ...`, ou None se nao for um.

    O esquema e comparado SEM caixa porque a RFC 7235 o define assim -- cliente
    que manda `bearer` esta correto. Esta e a UNICA normalizacao do cabecalho
    no modulo: o middleware de chave de acesso e as rotas de fonte chamam daqui
    para nao divergirem (ja divergiram: um exigia `Bearer ` exato).
    """
    if not authorization:
        return None
    esquema, _, resto = authorization.partition(" ")
    if esquema.lower() != "bearer":
        return None
    return resto.strip()


def chave_do_cabecalho(authorization: str | None) -> str:
    """Extrai a chave do `Authorization: Bearer ...`, recusando o resto.

    401 sem `WWW-Authenticate` seria resposta incompleta: o cabecalho e o que
    diz ao cliente COMO se autenticar, e sem ele o integrador so sabe que
    falhou.
    """
    chave = chave_bearer(authorization)
    if chave is None:
        raise HTTPException(
            status_code=401,
            detail="informe a chave da fonte em Authorization: Bearer <chave>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return chave


def fonte_autorizada(banco: Banco, chave: str) -> dict:
    """Fonte a que a chave pertence, ou 401/403.

    A MENSAGEM E A MESMA para chave malformada, fonte inexistente e hash que
    nao bate. Distinguir os tres contaria a quem tenta se aquele id de fonte
    existe -- e a conferencia do hash roda mesmo quando a fonte nao foi achada,
    para o tempo de resposta tambem nao contar.

    Fonte desativada e caso separado (403, nao 401): a chave esta certa, o que
    esta desligado e a fonte. Recusar como "chave invalida" mandaria o
    integrador procurar problema onde nao ha.
    """
    negada = HTTPException(
        status_code=401,
        detail="chave invalida",
        headers={"WWW-Authenticate": "Bearer"},
    )

    fonte_id = credencial.fonte_da_chave(chave)
    fonte = banco.buscar_fonte(fonte_id) if fonte_id is not None else None
    guardado = banco.hash_da_chave_da_fonte(fonte_id) if fonte_id is not None else None

    if not credencial.confere(chave, guardado) or fonte is None:
        raise negada
    if not fonte["ativa"]:
        raise HTTPException(
            status_code=403,
            detail=f"a fonte '{fonte['nome']}' esta desativada",
        )
    return fonte


def e_mestra(ctx: Contexto, chave: str) -> bool:
    """Confere a chave contra as DUAS procedencias da mestra.

    A do ambiente e comparada em tempo constante contra o valor cru; a do
    banco, contra o hash (`credencial.confere` tambem nao vaza pelo tempo).
    As duas conferencias rodam SEMPRE, mesmo quando a primeira ja decidiu:
    curto-circuitar faria o tempo de resposta contar qual das duas existe.
    """
    do_ambiente = False
    if ctx.chave_mestra is not None:
        do_ambiente = hmac.compare_digest(
            chave.encode("utf-8"), ctx.chave_mestra.encode("utf-8")
        )
    do_banco = credencial.confere(chave, ctx.banco.hash_da_chave_mestra())
    return do_ambiente or do_banco


def acesso_autorizado(ctx: Contexto, chave: str) -> bool:
    """Mestra ou chave de acesso valida. Mensagem de recusa e uniforme
    la fora: daqui so sai sim ou nao."""
    if e_mestra(ctx, chave):
        return True
    chave_id = acesso.id_da_chave(chave)
    guardado = ctx.banco.hash_da_chave_acesso(chave_id) if chave_id is not None else None
    return credencial.confere(chave, guardado)


def exigir_mestra(ctx: Contexto, authorization: str | None) -> None:
    """Gerenciar chaves e privilegio da mestra, nunca de chave de acesso.

    No modo aberto (sem mestra) nao ha o que exigir -- as rotas de
    gerenciamento seguem abertas como o resto, coerente com a decisao de
    ativacao condicionada.

    403, nao 401: quem chega aqui com chave de acesso valida ja passou pelo
    middleware -- a credencial esta certa, o privilegio e que falta.
    """
    if not ctx.autenticacao_ligada():
        return
    chave = chave_do_cabecalho(authorization)
    if not e_mestra(ctx, chave):
        raise HTTPException(
            status_code=403, detail="esta rota exige a chave mestra"
        )


def registrar_middleware_de_acesso(app: FastAPI, ctx: Contexto) -> None:
    """Exige chave em toda rota QUANDO ha mestra -- decidido por REQUISICAO.

    O middleware e registrado sempre, e pergunta o estado a cada requisicao.
    Antes ele so era registrado se houvesse mestra no boot, e isso tornava
    impossivel ligar a autenticacao sem reiniciar: o app que subiu aberto nao
    tinha onde exigir a chave, e a rota que grava a mestra apenas PARECERIA
    ligar a defesa. Sem mestra ele libera, exatamente como antes.

    O custo e uma leitura de estado por requisicao -- uma consulta a uma tabela
    de uma linha, no mesmo SQLite que a rota ja vai abrir.
    """

    @app.middleware("http")
    async def exigir_chave_de_acesso(request, call_next):
        if not ctx.autenticacao_ligada():
            return await call_next(request)
        # /ingestao tem credencial propria (chave de FONTE): uma credencial
        # por rota. /acesso/estado e publica por necessidade -- a tela precisa
        # dela justamente quando ainda nao ha credencial nenhuma. OPTIONS e o
        # preflight do navegador -- nao carrega header de autorizacao por
        # definicao.
        # `rstrip("/")`: `/ingestao/` e a MESMA rota (o Starlette redireciona
        # para ela), e comparar o path exato mandava o integrador que
        # configurou a URL com barra final para o 401 daqui em vez da
        # credencial de fonte.
        if request.url.path.rstrip("/") in ISENTAS or request.method == "OPTIONS":
            return await call_next(request)
        cabecalho = request.headers.get("authorization")
        chave_recebida = chave_bearer(cabecalho)
        if chave_recebida is None:
            return JSONResponse(
                status_code=401,
                content={"detail": (
                    "informe a chave de acesso em Authorization: Bearer <chave>"
                )},
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not acesso_autorizado(ctx, chave_recebida):
            return JSONResponse(
                status_code=401,
                content={"detail": "chave invalida"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        return await call_next(request)
