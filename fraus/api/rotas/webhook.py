"""POST /integracoes/webhook/{fonte_id} -- atendimento por webhook assinado.

O SEGUNDO caminho de escrita pela rede, ao lado de `POST /ingestao`. A
diferenca e a credencial: `/ingestao` pede uma chave `frs_` no cabecalho
Authorization, e isto aqui confere uma ASSINATURA sobre o corpo. As duas
existem porque plataforma nenhuma dispensa a segunda forma -- o padrao de
mercado e URL unica por endpoint com assinatura, nao header customizado.

O que as duas fazem depois de autenticar e o MESMO codigo
(`fraus/api/registro.py`): o canal vem da fonte e o veredito e derivado no
servidor.

A ORDEM DO PORTEIRO E IDENTIDADE, DEPOIS AUTORIDADE, DEPOIS PARSE. Nada de
desserializar JSON, tocar no banco ou pontuar antes de a assinatura passar --
e a regra que separa um receptor de webhook de uma porta aberta.
"""

import os
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from fraus import assinatura
from fraus.api.contexto import Contexto, obter_contexto
from fraus.api.esquemas import PedidoIngestao
from fraus.api.registro import registrar_conversa

router = APIRouter()

# Exportado para `fraus/api/seguranca.py` montar a lista ISENTAS a partir daqui.
# Uma segunda copia da string la so ficaria errada no dia em que esta mudasse --
# e o efeito seria 401 em toda chamada de webhook, com o log de entregas vazio
# dizendo "nao chegou nada".
PREFIXO_WEBHOOK = "/integracoes/webhook"


class Recusa(Exception):
    """Recusa do porteiro: o status HTTP, o veredito registrado e o motivo.

    Excecao propria em vez de HTTPException direta porque TODA recusa precisa
    virar linha em `entregas_webhook` antes de virar resposta. Levantar
    HTTPException de dentro dos passos deixaria o registro na mao de quem
    lembrasse -- e a recusa que ninguem registra e exatamente a que o operador
    precisava ver.
    """

    def __init__(self, status: int, veredito: str, motivo: str) -> None:
        super().__init__(motivo)
        self.status = status
        self.veredito = veredito
        self.motivo = motivo


@router.post(PREFIXO_WEBHOOK + "/{fonte_id}")
async def receber(
    fonte_id: int,
    request: Request,
    webhook_id: str | None = Header(default=None, alias="webhook-id"),
    webhook_timestamp: str | None = Header(default=None, alias="webhook-timestamp"),
    webhook_signature: str | None = Header(default=None, alias="webhook-signature"),
    ctx: Contexto = Depends(obter_contexto),
):
    """Recebe atendimento assinado no padrao Standard Webhooks.

    O corpo e lido CRU, em bytes, e nao por um modelo Pydantic no parametro:
    HMAC e byte-exato, e deixar o FastAPI desserializar e a gente re-serializar
    para conferir muda a assinatura por reordenacao de chave ou por um espaco
    de diferenca. A validacao Pydantic acontece depois, sobre os MESMOS bytes,
    e so depois de a assinatura passar.
    """
    fonte = ctx.banco.buscar_fonte(fonte_id)
    if fonte is None:
        # Sem fonte nao ha de quem registrar a entrega -- e uma linha com
        # fonte_id invalido nao teria onde ser lida.
        raise HTTPException(status_code=404, detail="fonte nao encontrada")

    corpo = await request.body()
    recebida_em = datetime.now(timezone.utc).isoformat()

    def registrar(veredito: str, motivo: str | None = None,
                  conversa_id: str | None = None) -> None:
        ctx.banco.registrar_entrega(
            fonte_id=fonte_id, webhook_id=webhook_id, veredito=veredito,
            recebida_em=recebida_em, motivo=motivo, conversa_id=conversa_id,
        )

    try:
        resultado = _passar_pelo_porteiro(
            ctx, fonte, fonte_id, corpo,
            webhook_id, webhook_timestamp, webhook_signature,
        )
    except Recusa as recusa:
        registrar(recusa.veredito, recusa.motivo)
        raise HTTPException(status_code=recusa.status, detail=recusa.motivo) from recusa

    if resultado is None:
        # Passo 7: reentrega. 200, NAO erro -- o Standard Webhooks manda a
        # plataforma retentar diante de qualquer resposta fora de 2xx, e
        # responder erro a uma reentrega legitima poria a integracao em laco
        # infinito por conta propria.
        registrar("duplicada", "webhook-id ja processado")
        return {"duplicada": True, "webhook_id": webhook_id}

    registrar("aceita", conversa_id=resultado["id"])
    return JSONResponse(status_code=201, content=jsonable_encoder(resultado))


def _passar_pelo_porteiro(
    ctx: Contexto,
    fonte: dict,
    fonte_id: int,
    corpo: bytes,
    webhook_id: str | None,
    webhook_timestamp: str | None,
    webhook_signature: str | None,
) -> dict | None:
    """Os passos 2 a 8. Devolve o veredito, ou None se for reentrega.

    Levanta `Recusa` -- nunca HTTPException -- para que quem chamou registre a
    entrega antes de responder.
    """
    # Passo 2: o segredo. 503, nao 401: variavel ausente e defeito da MAQUINA
    # que hospeda, e o corpo nomeia a variavel porque quem opera precisa saber
    # qual. Responder 401 mandaria quem integra depurar a propria requisicao
    # por um problema que nao e dele.
    nome_da_variavel = fonte["variavel_segredo"]
    if not nome_da_variavel:
        raise Recusa(503, "sem_segredo", (
            f"a fonte '{fonte['nome']}' nao nomeia variavel de ambiente para o "
            "segredo do webhook -- cadastre o nome dela na tela de Integracoes"
        ))
    segredo = os.environ.get(nome_da_variavel)
    if not segredo:
        raise Recusa(503, "sem_segredo", (
            f"a variavel {nome_da_variavel} nao esta definida no ambiente da API"
        ))
    try:
        assinatura.chave_do_segredo(segredo)
    except ValueError as erro:
        raise Recusa(503, "sem_segredo", (
            f"a variavel {nome_da_variavel} nao carrega um segredo valido: {erro}"
        )) from erro

    # Passo 3: os tres cabecalhos. Nomeia QUAL falta -- "cabecalho ausente" sem
    # o nome manda o integrador conferir os tres.
    for nome, valor in (
        ("webhook-id", webhook_id),
        ("webhook-timestamp", webhook_timestamp),
        ("webhook-signature", webhook_signature),
    ):
        if not valor:
            raise Recusa(400, "corpo_invalido", f"cabecalho {nome} ausente")

    # Passo 4: a janela. Antes do HMAC de proposito -- e a checagem barata, e
    # rejeitar cedo e o que impede um corpo grande de custar computo.
    if not assinatura.dentro_da_janela(webhook_timestamp, agora=int(time.time())):
        raise Recusa(400, "fora_da_janela", (
            f"webhook-timestamp fora da janela de "
            f"{assinatura.JANELA_SEGUNDOS}s do relogio do servidor"
        ))

    # Passo 5: a assinatura.
    if not assinatura.confere(
        webhook_id, webhook_timestamp, corpo, segredo, webhook_signature
    ):
        raise Recusa(401, "assinatura", "assinatura nao confere")

    # Passo 6: a fonte ativa. DEPOIS da assinatura: informar que a fonte esta
    # desativada a quem nao provou identidade conta a um desconhecido o estado
    # interno do sistema.
    if not fonte["ativa"]:
        raise Recusa(403, "fonte_inativa", f"a fonte '{fonte['nome']}' esta desativada")

    # Passo 7: reentrega. Nao e recusa -- ver o comentario em `receber`.
    if ctx.banco.entrega_ja_vista(fonte_id, webhook_id):
        return None

    # Passo 8: so agora o corpo vira objeto.
    try:
        pedido = PedidoIngestao.model_validate_json(corpo)
    except ValidationError as erro:
        raise Recusa(400, "corpo_invalido", str(erro)) from erro

    try:
        return registrar_conversa(ctx, pedido, fonte)
    except HTTPException as erro:
        # `registrar_conversa` levanta 400 quando os campos nao montam uma
        # Conversa valida (timestamp naive, por exemplo). Vira Recusa para que
        # a entrega seja registrada como as outras.
        raise Recusa(erro.status_code, "corpo_invalido", str(erro.detail)) from erro
