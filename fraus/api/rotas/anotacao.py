"""/anotacao -- a regua de ironia anotada as cegas, por link, sem conta.

Quem anota recebe um link com token opaco, no molde do convite de equipe
(`/operacao/convites/<token>`). O banco guarda so `sha256(token)`; o token
sai UMA vez, na criacao. Nenhum nome de pessoa e guardado: o anotador e um id
curto aleatorio (`a_` + 8 hex).

Duas rotas sao PUBLICAS -- ler a propria fila e gravar resposta -- e o
middleware as isenta pelo formato exato do caminho (`seguranca.py`). As duas
de dev (`POST /anotacao/anotadores`, `GET /anotacao/respostas`) tem caminho
FIXO que casaria com `/anotacao/{token}`; por isso a rota fixa e declarada
antes da parametrica aqui, e o middleware exclui esses nomes da isencao.

A fila nunca leva par, estrato, rotulo, dominio nem `g`: so `id` e `texto`.
O instante da resposta e do SERVIDOR; o corpo nao escolhe quando respondeu.

LINK DE GRUPO. Um link so, postado num grupo de mensagens, que da a cada
pessoa o SEU anotador: `POST /anotacao/grupos/<token>/entrar` (publica) ocupa
uma vaga e devolve um token pessoal novo. A vaga e ocupada antes de o
anotador nascer, numa leitura-e-escrita serializada (`alterar_documento`):
cinco vagas nao viram seis com cliques simultaneos. Quem repassa o link
gasta vaga -- o link nao sabe quem e quem.
"""

import hashlib
import json
import secrets
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, Field, StrictInt, ValidationError, field_validator

from fraus.anotacao_regua import ordem_do_anotador, respostas_do_anotador
from fraus.api.contexto import Contexto, obter_contexto
from fraus.api.vazao import segundos_ate_a_vaga
from fraus.avaliacao_ironia import carregar_rascunho
from fraus.consolidacao_regua import RESPOSTAS

router = APIRouter(prefix="/anotacao")

TIPO_ANOTADOR = "anotador_regua"
TIPO_RESPOSTA = "resposta_regua"
TIPO_GRUPO = "grupo_regua"
# Caminhos fixos sob /anotacao que NAO sao token. O middleware importa daqui:
# uma rota fixa nova que esquecesse de entrar nesta lista seria isentada de
# credencial como se fosse link de anotador.
CAMINHOS_FIXOS = ("anotadores", "respostas", "grupos")
CAMPOS_DO_REGISTRO = ("anotador", "frase_id", "resposta", "instante")
_NAO_ENCONTRADO = "link de anotacao invalido ou revogado"
_GRUPO_NAO_ENCONTRADO = "link de grupo invalido ou revogado"
_GRUPO_CHEIO = "este link de grupo ja esta cheio"
VAGAS_MAXIMAS_POR_GRUPO = 20
# Teto de VOLUME por link, ao lado do teto de ritmo (`vazao.py`): cinco
# respostas por frase da regua (300 x 5 = 1500). Trocar de ideia algumas vezes
# cabe; um link vazado nao enche o banco -- so com o ritmo, seriam 86 mil
# registros por dia.
MAXIMO_RESPOSTAS_POR_ANOTADOR = 5 * 300


class PedidoResposta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    frase_id: str
    resposta: str

    @field_validator("resposta")
    @classmethod
    def _resposta_conhecida(cls, valor: str) -> str:
        # A lista e a da consolidacao: uma resposta que ela recusaria nao
        # pode entrar pelo caminho de gravacao.
        if valor not in RESPOSTAS:
            raise ValueError("resposta desconhecida")
        return valor


class PedidoGrupo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Estrito: "5" e `true` nao viram vaga por coercao.
    vagas: StrictInt = Field(ge=1, le=VAGAS_MAXIMAS_POR_GRUPO)


@lru_cache(maxsize=1)
def _rascunho():
    return tuple(carregar_rascunho())


@lru_cache(maxsize=1)
def _ids_do_rascunho() -> frozenset[str]:
    return frozenset(f.frase_id for f in _rascunho())


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _anotador_valido(ctx: Contexto, token: str) -> str:
    """Id do anotador, ou 404 -- o MESMO para inexistente e revogado."""
    registro = ctx.banco.documento(TIPO_ANOTADOR, _hash(token))
    if registro is None or registro.get("revogado"):
        raise HTTPException(404, _NAO_ENCONTRADO)
    return registro["anotador"]


def _espera_ou_429(limitador, identidade: str) -> None:
    espera = segundos_ate_a_vaga(limitador, identidade)
    if espera is not None:
        raise HTTPException(
            429, "muitas requisicoes seguidas -- aguarde antes de tentar de novo",
            headers={"Retry-After": str(espera)},
        )


def _registros(ctx: Contexto) -> list[dict]:
    """TODAS as respostas -- so para o export de dev, nunca em rota publica."""
    return [{k: r[k] for k in CAMPOS_DO_REGISTRO} for r in ctx.banco.documentos(TIPO_RESPOSTA)]


def _prefixo(anotador: str) -> str:
    # O id do registro comeca com `<anotador>:` (ver `gravar_resposta`); o
    # banco filtra por esse prefixo e a rota publica nunca le a tabela inteira.
    return f"{anotador}:"


def _registros_do_anotador(ctx: Contexto, anotador: str) -> list[dict]:
    return [{k: r[k] for k in CAMPOS_DO_REGISTRO}
            for r in ctx.banco.documentos_com_prefixo(TIPO_RESPOSTA, _prefixo(anotador))]


def _resumo_sem_eco(erro: ValidationError, modelo: type[BaseModel] = PedidoResposta) -> str:
    """Onde e o que falhou, sem NADA do que veio (armadilha 10 do handoff).

    Diferente de `registro.resumo_validacao`, aqui o modelo e `extra="forbid"`
    -- e o erro `extra_forbidden` traz no `loc` o nome do campo que o cliente
    inventou. So nome de campo DECLARADO sai; o resto vira marcador fixo.
    """
    partes = []
    for item in erro.errors():
        loc = item["loc"]
        if item["type"] == "extra_forbidden":
            partes.append("(campo_nao_previsto)")
        elif loc and loc[0] in modelo.model_fields:
            partes.append(f"{loc[0]} ({item['type']})")
        else:
            partes.append(f"({item['type']})")
    return "corpo nao bate o contrato: " + ", ".join(partes)


async def _corpo_validado(request: Request, modelo: type[BaseModel]):
    """Corpo lido a mao, nao por parametro tipado: o 422 padrao do FastAPI
    devolve o `input` recebido (armadilha 10 do handoff)."""
    try:
        bruto = json.loads(await request.body())
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(422, "corpo nao e JSON valido") from None
    try:
        return modelo.model_validate(bruto)
    except ValidationError as erro:
        raise HTTPException(422, _resumo_sem_eco(erro, modelo)) from None


def _guardar_anotador(banco, anotador: str, **extra) -> str:
    """Grava o anotador e devolve o token -- que so existe nesta resposta."""
    token = secrets.token_urlsafe(32)
    banco.guardar_documento(TIPO_ANOTADOR, _hash(token), {
        "anotador": anotador,
        "criado_em": datetime.now(timezone.utc).isoformat(),
        "revogado": False,
        **extra,
    })
    return token


def _novo_id_de_anotador() -> str:
    return "a_" + secrets.token_hex(4)


@router.post("/anotadores", status_code=201)
def criar_anotador(ctx: Contexto = Depends(obter_contexto)):
    """So dev (`rota_administrativa`). O token sai aqui e nunca mais."""
    anotador = _novo_id_de_anotador()
    return {"anotador": anotador, "token": _guardar_anotador(ctx.banco, anotador)}


def ocupar_vaga(banco, chave_do_grupo: str, anotador: str) -> dict:
    """Poe `anotador` numa vaga do grupo, ou 404/409 -- tudo dentro da trava
    de `alterar_documento`, que serializa a leitura e a escrita (BEGIN
    IMMEDIATE no SQLite, advisory lock no Postgres). Contar vaga fora dela
    deixaria dois cliques simultaneos lerem "4 de 5" e gravarem 6."""
    def transformar(grupo):
        if grupo.get("revogado"):
            raise HTTPException(404, _GRUPO_NAO_ENCONTRADO)
        if len(grupo["anotadores"]) >= grupo["vagas"]:
            raise HTTPException(409, _GRUPO_CHEIO)
        return {**grupo, "anotadores": [*grupo["anotadores"], anotador]}

    grupo = banco.alterar_documento(TIPO_GRUPO, chave_do_grupo, transformar)
    if grupo is None:
        raise HTTPException(404, _GRUPO_NAO_ENCONTRADO)
    return grupo


@router.post("/grupos", status_code=201)
async def criar_grupo(request: Request, ctx: Contexto = Depends(obter_contexto)):
    """So dev. Um link para N pessoas; o token sai aqui e nunca mais."""
    pedido = await _corpo_validado(request, PedidoGrupo)
    token = secrets.token_urlsafe(32)
    grupo = "g_" + secrets.token_hex(4)
    await run_in_threadpool(ctx.banco.guardar_documento, TIPO_GRUPO, _hash(token), {
        "grupo": grupo,
        "vagas": pedido.vagas,
        "anotadores": [],
        "revogado": False,
        "criado_em": datetime.now(timezone.utc).isoformat(),
    })
    return {"grupo": grupo, "token": token}


@router.post("/grupos/{token}/entrar", status_code=201)
def entrar_no_grupo(token: str, request: Request, ctx: Contexto = Depends(obter_contexto)):
    """Publica. Ocupa uma vaga e devolve o token PESSOAL de um anotador novo.

    A vaga e ocupada ANTES de o anotador ser gravado: se o processo cair entre
    os dois passos perde-se uma vaga, nunca se ganha uma a mais. Teto pelo
    hash do token do grupo, pelo mesmo motivo das outras rotas publicas.
    """
    _espera_ou_429(request.app.state.limitador_de_grupo, _hash(token))
    anotador = _novo_id_de_anotador()
    grupo = ocupar_vaga(ctx.banco, _hash(token), anotador)
    return {"token": _guardar_anotador(ctx.banco, anotador, grupo=grupo["grupo"])}


@router.post("/grupos/{grupo}/revogar")
def revogar_grupo(grupo: str, anotadores: bool = False, ctx: Contexto = Depends(obter_contexto)):
    """So dev. Fecha a ENTRADA pelo link do grupo; quem ja entrou segue
    anotando. Com `?anotadores=1` revoga tambem os anotadores do grupo -- e as
    respostas deles saem do export."""
    alvo = next((g for g in ctx.banco.documentos(TIPO_GRUPO) if g["grupo"] == grupo), None)
    if alvo is None:
        raise HTTPException(404, "grupo inexistente")
    ctx.banco.alterar_documento(TIPO_GRUPO, alvo["id"], lambda d: {**d, "revogado": True})
    revogados = 0
    if anotadores:
        for registro in ctx.banco.documentos(TIPO_ANOTADOR):
            if registro.get("grupo") == grupo and not registro.get("revogado"):
                ctx.banco.alterar_documento(TIPO_ANOTADOR, registro["id"], lambda d: {**d, "revogado": True})
                revogados += 1
    return {"grupo": grupo, "revogado": True, "anotadores_revogados": revogados}


@router.post("/anotadores/{anotador}/revogar")
def revogar_anotador(anotador: str, ctx: Contexto = Depends(obter_contexto)):
    """So dev. O registro e achado pelo id opaco DENTRO do payload: o id da
    linha e o hash do token, que ninguem mais tem."""
    alvo = next((r for r in ctx.banco.documentos(TIPO_ANOTADOR) if r["anotador"] == anotador), None)
    if alvo is None:
        raise HTTPException(404, "anotador inexistente")
    ctx.banco.alterar_documento(TIPO_ANOTADOR, alvo["id"], lambda d: {**d, "revogado": True})
    return {"anotador": anotador, "revogado": True}


# DECLARADA ANTES de `/{token}`: o Starlette casa na ordem de registro, e
# "respostas" e um token sintaticamente valido.
@router.get("/respostas")
def exportar_respostas(ctx: Contexto = Depends(obter_contexto)):
    """So dev. Lista no formato que `scripts/consolidar_regua_ironia.py` le.

    Anotador REVOGADO fica de fora: revogar um link e dizer que aquelas
    respostas nao valem (link vazado, anotador que nao seguiu o protocolo), e
    elas nao podem entrar na regua pela porta do export.
    """
    revogados = {a["anotador"] for a in ctx.banco.documentos(TIPO_ANOTADOR) if a.get("revogado")}
    validos = [r for r in _registros(ctx) if r["anotador"] not in revogados]
    return sorted(validos, key=lambda r: (r["instante"], r["anotador"], r["frase_id"]))


@router.get("/{token}")
def fila_do_anotador(token: str, request: Request, ctx: Contexto = Depends(obter_contexto)):
    # Contado pelo HASH DO TOKEN, antes de olhar o banco: token inventado
    # tambem gasta janela (a dele). NAO por IP: a dashboard chama pelo proxy
    # do Next, entao todo anotador chega com o IP do proxy e uma janela por IP
    # seria UMA janela para todos -- 30 leituras por minuto para a turma
    # inteira. Enumerar token e inviavel pela entropia (256 bits), nao pelo
    # teto; o teto protege o banco de um laco sobre o mesmo link.
    _espera_ou_429(request.app.state.limitador_de_leitura_de_anotacao, _hash(token))
    anotador = _anotador_valido(ctx, token)
    return {
        "frases": ordem_do_anotador(_rascunho(), anotador),
        "respostas": respostas_do_anotador(_registros_do_anotador(ctx, anotador), anotador),
    }


@router.post("/{token}/respostas", status_code=201)
async def gravar_resposta(token: str, request: Request, ctx: Contexto = Depends(obter_contexto)):
    # Corpo lido a mao, nao por parametro tipado: o 422 padrao do FastAPI
    # devolve o `input` recebido, e esta rota e anonima.
    # Teto ANTES do banco e pelo hash do token, pelo mesmo motivo da leitura:
    # POST com token inventado tambem e contado, e o IP do proxy nao separa
    # anotadores. Um token por anotador, entao e o mesmo que contar por ele.
    _espera_ou_429(request.app.state.limitador_de_anotacao, _hash(token))
    anotador = await run_in_threadpool(_anotador_valido, ctx, token)
    ja_mandadas = await run_in_threadpool(
        ctx.banco.contar_documentos_com_prefixo, TIPO_RESPOSTA, _prefixo(anotador))
    if ja_mandadas >= MAXIMO_RESPOSTAS_POR_ANOTADOR:
        raise HTTPException(409, "este link ja mandou o maximo de respostas")
    pedido = await _corpo_validado(request, PedidoResposta)
    if pedido.frase_id not in _ids_do_rascunho():
        raise HTTPException(422, "frase_id fora da regua")
    instante = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    registro = {"anotador": anotador, "frase_id": pedido.frase_id,
                "resposta": pedido.resposta, "instante": instante}
    identificador = f"{_prefixo(anotador)}{pedido.frase_id}:{instante}:{uuid.uuid4().hex[:6]}"
    await run_in_threadpool(ctx.banco.guardar_documento, TIPO_RESPOSTA, identificador, registro)
    return registro
