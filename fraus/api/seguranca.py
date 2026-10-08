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
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from fraus import acesso, credencial, token_acesso
from fraus.api.contexto import Contexto
from fraus.api.rotas.anotacao import CAMINHOS_FIXOS as CAMINHOS_FIXOS_DA_ANOTACAO
from fraus.api.rotas.webhook import PREFIXO_WEBHOOK
from fraus.db import Banco


# Rotas que o middleware de chave de acesso NAO cobre, cada uma por um motivo
# proprio:
#
# - `/ingestao` tem credencial de FONTE -- uma credencial por rota.
# - `/acesso/estado` precisa responder a quem ainda nao tem credencial nenhuma:
#   e a resposta que diz a tela se ha o que apresentar.
# - `/saude` e `/saude/prontidao` porque sao DIAGNOSTICO, e diagnostico atras de credencial
#   mente. Com ela fechada, a dashboard sem chave recebia 401 no health check e
#   anunciava "API fora do ar" com a API perfeitamente no ar -- mandando quem
#   opera procurar servidor derrubado quando o que faltava era uma chave. Ela
#   nao devolve dado nenhum: o corpo e `{"status": "ok"}`, o mesmo fato que
#   qualquer um confirma abrindo uma conexao TCP na porta.
# - `/auth/registrar` e `/auth/entrar` sao as rotas de quem ainda nao tem
#   credencial NENHUMA -- o mesmo argumento de `/acesso/estado`. Elas tem
#   defesa propria: o cadastro exige o codigo de convite para privilegio, e o
#   login so devolve token a quem prova a senha.
# - `/integracoes/webhook/{id}` tem credencial propria (a ASSINATURA do corpo),
#   e a plataforma externa nao tem -- nem pode ter -- uma chave de acesso
#   `fra_`. Sem esta linha o defeito e silencioso e so aparece em producao: com
#   a mestra definida, toda chamada de webhook levaria 401 aqui antes de a
#   assinatura ser olhada, e o log de entregas ficaria vazio dizendo "nao
#   chegou nada" enquanto a plataforma recebe 401 em cada tentativa.
ISENTAS = (
    "/ingestao",
    "/acesso/estado",
    "/saude",
    "/saude/prontidao",
    "/auth/estado",
    "/auth/registrar",
    "/auth/entrar",
)


def rota_publica_de_anotacao(metodo: str, caminho: str) -> bool:
    """O link do anotador: `GET /anotacao/<token>` e `POST /anotacao/<token>/respostas`.

    Isenta pelo FORMATO EXATO, no molde do convite, e nunca por prefixo:
    `/anotacao/respostas` (exportar) e `/anotacao/anotadores` (criar) tem o
    mesmo formato de um token e sao so de dev. Uma isencao por prefixo
    entregaria as respostas de todos os anotadores a qualquer anonimo.
    `caminho` ja chega sem barra final.
    """
    partes = caminho.split("/")
    if len(partes) < 3 or partes[0] != "" or partes[1] != "anotacao":
        return False
    token = partes[2]
    if not token or token in CAMINHOS_FIXOS_DA_ANOTACAO:
        return False
    if metodo == "GET":
        return len(partes) == 3
    if metodo == "POST":
        return len(partes) == 4 and partes[3] == "respostas"
    return False


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
    """Confere a chave contra a mestra VIGENTE -- uma so, nunca as duas.

    A do ambiente e comparada em tempo constante contra o valor cru; a do
    banco, contra o hash (`credencial.confere` tambem nao vaza pelo tempo).
    As duas conferencias rodam SEMPRE, mesmo quando a resposta ja esta
    decidida: curto-circuitar faria o tempo de resposta contar qual das duas
    existe.

    A PRECEDENCIA E EXCLUDENTE, e isto e conserto de 25/08/2026. Antes daqui
    saia `do_ambiente or do_banco`, e as duas mestras valiam ao mesmo tempo --
    uniao, nao precedencia. O README apresenta `FRAUS_CHAVE_MESTRA` como a
    saida de quem PERDEU ou VAZOU a mestra gerada pela tela, e `/acesso/mestra`
    afirma o mesmo ao recusar a rotacao com 409 ("tem precedencia sobre a
    gravada"). Com a uniao, quem seguia esse caminho achando ter revogado a
    chave vazada nao havia revogado nada -- e, como a variavel definida bloqueia
    a rotacao, nao sobrava nenhum caminho pela API para mata-la.

    Com a variavel definida ela e a UNICA mestra. Sem ela, a gravada volta a
    valer sozinha -- que e o que faz a autenticacao ligada por botao sobreviver
    a reiniciar o processo.
    """
    do_ambiente = False
    if ctx.chave_mestra is not None:
        do_ambiente = hmac.compare_digest(
            chave.encode("utf-8"), ctx.chave_mestra.encode("utf-8")
        )
    do_banco = credencial.confere(chave, ctx.banco.hash_da_chave_mestra())
    # A leitura do banco acontece de qualquer jeito (tempo constante); o que
    # muda e se ela CONTA. `origem_da_mestra` ja decide isso do mesmo jeito.
    return do_ambiente if ctx.chave_mestra is not None else do_banco


def acesso_autorizado(ctx: Contexto, chave: str) -> bool:
    """Mestra, chave de acesso ou JWT de usuario valido. Mensagem de recusa e
    uniforme la fora: daqui so sai sim ou nao."""
    if e_mestra(ctx, chave):
        return True
    if ctx.chave_acesso_ambiente is not None and hmac.compare_digest(
        chave.encode("utf-8"), ctx.chave_acesso_ambiente.encode("utf-8")
    ):
        return True
    chave_id = acesso.id_da_chave(chave)
    guardado = ctx.banco.hash_da_chave_acesso(chave_id) if chave_id is not None else None
    if credencial.confere(chave, guardado):
        return True
    return sessao_do_jwt(ctx, chave) is not None


def sessao_do_jwt(ctx: Contexto, chave: str | None) -> dict | None:
    """A sessao de usuario, quando o bearer e um JWT valido; None para o resto.

    Chave `fra_` e mestra nao parecem JWT e caem no None sem custo. Sem
    `jwt_segredo` configurado nao existe token valido possivel -- e a resposta
    e None, nunca excecao: quem chama esta no meio de decidir uma requisicao.

    O TOKEN NAO E A ULTIMA PALAVRA, e isto e conserto de 03/09/2026. Antes daqui
    saia a sessao assim que assinatura e `exp` batessem, sem olhar o banco. Duas
    consequencias, as duas reproduzidas:

    - Conta DESATIVADA seguia lendo tudo. So `/auth/eu` consultava `usuarios`,
      entao a tela dizia "sessao invalida" -- e quem opera acreditava ter
      cortado o acesso -- enquanto `/conversas` respondia 200 por ate 12 horas,
      a validade do token.
    - O `papel` viajava DENTRO do token. Rebaixar `dev` -> `usuario` no banco so
      surtia efeito na expiracao, e `rota_administrativa` continuava aberta.

    Agora a assinatura decide QUEM esta falando e o banco decide o que essa
    pessoa PODE -- que e a unica divisao em que revogar significa alguma coisa.
    A ordem importa: o usuario so e carregado DEPOIS de a assinatura conferir,
    senao qualquer token nomeando um id existente entraria.

    O custo e uma leitura por requisicao, a mesma que `faixas_vigentes()` ja
    paga. (O middleware e `acesso_autorizado` chamam esta funcao em sequencia,
    entao sao duas -- consulta por chave primaria, e o preco de nao mentir
    sobre quem tem acesso.)
    """
    if chave is None or ctx.jwt_segredo is None:
        return None
    sessao = token_acesso.conferir(
        chave, ctx.jwt_segredo, agora=datetime.now(timezone.utc)
    )
    if sessao is None:
        return None
    usuario = ctx.banco.buscar_usuario(sessao["usuario_id"])
    if usuario is None or not usuario["ativo"]:
        return None
    versao = ctx.banco.documento("sessao", str(usuario["id"])) or {"versao": 0}
    if sessao.get("versao", 0) != versao["versao"]:
        return None
    # O papel vem do BANCO, nao do payload: e o que faz promover e rebaixar
    # valerem na hora, nos dois sentidos.
    return {**sessao, "papel": usuario["papel"]}


def rota_administrativa(metodo: str, caminho: str) -> bool:
    """As rotas que so o papel `dev` alcanca (spec 2026-08-31, §2.2).

    O corte e o da decisao de produto: dev administra (integracoes, modelo,
    configuracoes, importacao, curadoria do lexico), usuario analisa. Leitura
    que a tela de analise usa -- conversas, indicadores, lexico curado LIDO --
    fica fora de proposito.

    `/integracoes/webhook/{id}` nunca chega aqui: o middleware isenta o
    prefixo do webhook ANTES deste teste, e a plataforma externa nao carrega
    JWT de qualquer jeito.
    """
    if caminho.startswith("/operacao/acesso") or (caminho == "/operacao/equipes" and metodo != "GET"):
        return True
    # Criar link de anotador e exportar as respostas da regua: dev. As rotas
    # publicas do anotador saem do middleware antes deste teste.
    if caminho in ("/anotacao/anotadores", "/anotacao/respostas"):
        return True
    if caminho.startswith("/integracoes") or caminho == "/modelo" or caminho.startswith("/modelo/"):
        return True
    if caminho in ("/conversas/importar", "/conversas/importar/previa", "/conversas/repontuar"):
        return True
    if caminho == "/configuracoes" and metodo != "GET":
        return True
    if caminho.startswith("/lexico") and metodo != "GET":
        return True
    # Perfil de mapeamento muda como TODO arquivo futuro daquela estrutura e
    # lido -- e configuracao da instalacao, como o lexico curado.
    if caminho.startswith("/perfis-mapeamento") and metodo != "GET":
        return True
    return False


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
        # /ingestao tem credencial propria (chave de FONTE): uma credencial
        # por rota. /acesso/estado e publica por necessidade -- a tela precisa
        # dela justamente quando ainda nao ha credencial nenhuma. OPTIONS e o
        # preflight do navegador -- nao carrega header de autorizacao por
        # definicao.
        # `rstrip("/")`: `/ingestao/` e a MESMA rota (o Starlette redireciona
        # para ela), e comparar o path exato mandava o integrador que
        # configurou a URL com barra final para o 401 daqui em vez da
        # credencial de fonte.
        caminho = request.url.path.rstrip("/")
        if request.method == "GET" and caminho.startswith("/operacao/convites/") and len(caminho.split("/")) == 4:
            # Publica: quem recebeu o link ainda nao tem conta. Mas a sessao, se
            # veio, e lida -- quem criou a conta por este link ocupa a vaga, e
            # so reconhecendo a pessoa a rota responde que o convite e dela.
            request.state.sessao = sessao_do_jwt(ctx, chave_bearer(request.headers.get("authorization")))
            return await call_next(request)
        if (
            caminho in ISENTAS
            or rota_publica_de_anotacao(request.method, caminho)
            or caminho.startswith(f"{PREFIXO_WEBHOOK}/")
            or request.method == "OPTIONS"
        ):
            return await call_next(request)
        cabecalho = request.headers.get("authorization")
        chave_recebida = chave_bearer(cabecalho)
        # O portao de PAPEL vem antes do interruptor da mestra, porque vale
        # nos dois modos: a API aberta continua aberta para quem nao se
        # identifica, mas um JWT de usuario apresentado E identidade valida --
        # e identidade de usuario nao administra em modo nenhum. 403, nao 401:
        # a credencial esta certa, o privilegio e que falta.
        sessao = sessao_do_jwt(ctx, chave_recebida)
        request.state.sessao = sessao
        if (
            sessao is not None
            and sessao["papel"] != "dev"
            and rota_administrativa(request.method, caminho)
        ):
            return JSONResponse(
                status_code=403,
                content={"detail": "esta rota exige o papel dev"},
            )
        if not ctx.autenticacao_ligada():
            return await call_next(request)
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
