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
from fraus.api.registro import registrar_conversa, resumo_validacao
from fraus.api.vazao import ENTREGAS_POR_JANELA, LimitadorDeVazao, segundos_ate_a_vaga

router = APIRouter()

# Exportado para `fraus/api/seguranca.py` montar a lista ISENTAS a partir daqui.
# Uma segunda copia da string la so ficaria errada no dia em que esta mudasse --
# e o efeito seria 401 em toda chamada de webhook, com o log de entregas vazio
# dizendo "nao chegou nada".
PREFIXO_WEBHOOK = "/integracoes/webhook"


class Recusa(Exception):
    """Recusa do porteiro: o status HTTP, o veredito e DUAS mensagens.

    Excecao propria em vez de HTTPException direta porque TODA recusa precisa
    virar linha em `entregas_webhook` antes de virar resposta. Levantar
    HTTPException de dentro dos passos deixaria o registro na mao de quem
    lembrasse -- e a recusa que ninguem registra e exatamente a que o operador
    precisava ver.

    SAO DUAS MENSAGENS porque os dois destinos tem plateias diferentes:

    - `motivo` vai para `entregas_webhook`, que so se le com credencial. E ali
      que quem OPERA precisa do detalhe -- qual variavel de ambiente falta, que
      fonte e essa. Sem o detalhe, a tabela existe e nao ajuda.
    - `publico` e o `detail` do HTTP, e chega a um ANONIMO: a rota do webhook
      nao pede Authorization, a credencial dela e a assinatura. Nome de fonte,
      nome de variavel de ambiente da maquina que hospeda e o texto de um
      `ValueError` sobre o formato do segredo sao estado interno, e contar
      estado interno a quem ainda nao provou identidade e o mesmo defeito que o
      passo 6 recusa cometer.

    Quem nao passa `publico` esta dizendo que o motivo ja e generico -- o caso
    dos passos 3 a 8, que falam so do que veio na propria requisicao.
    """

    def __init__(
        self, status: int, veredito: str, motivo: str, publico: str | None = None,
        cabecalhos: dict[str, str] | None = None,
    ) -> None:
        super().__init__(motivo)
        self.status = status
        self.veredito = veredito
        self.motivo = motivo
        self.publico = publico if publico is not None else motivo
        # So o 429 usa, para o `Retry-After`. Existe aqui, e nao no ponto de
        # levantamento, porque quem transforma `Recusa` em resposta e o
        # `except` la de cima -- sem isto o cabecalho teria de ser reconstruido
        # la, longe de quem sabe por que ele existe.
        self.cabecalhos = cabecalhos


# `status_code=201` no DECORADOR, e nao so no JSONResponse do fim: o schema
# OpenAPI publicado sai do decorador, e sem ele o `/docs` anunciava 200 para o
# caminho feliz enquanto a rota devolvia 201 -- a tabela do README promete 201, e
# quem integra le o schema.
@router.post(
    PREFIXO_WEBHOOK + "/{fonte_id}",
    status_code=201,
    responses={
        200: {
            "description": (
                "Reentrega ja processada (mesmo webhook-id da fonte). Nao e "
                "erro -- o corpo confirma a duplicidade sem gravar de novo."
            )
        }
    },
)
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
        # Passo 1. Sem fonte nao ha de quem registrar a entrega -- e uma linha
        # com fonte_id invalido nao teria onde ser lida.
        #
        # O texto ja e generico: nome nenhum, nada do cadastro. O que sobra e o
        # 404 em si, que diz a um anonimo se aquele id existe. Fechar isso
        # exigiria responder o mesmo para id valido e invalido, e ai a entrega
        # de uma fonte que existe seria indistinguivel de um erro de digitacao
        # na URL -- justamente o diagnostico que quem integra precisa. Como o
        # id e um inteiro pequeno e sequencial, o cadastro e enumeravel por
        # desenho; e limitacao declarada, nao descuido.
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
            request.app.state.limitador_de_webhook,
        )
    except Recusa as recusa:
        # O DETALHE vai para a tabela; a REDE recebe a versao publica. Ver a
        # docstring de `Recusa`.
        registrar(recusa.veredito, recusa.motivo)
        raise HTTPException(
            status_code=recusa.status,
            detail=recusa.publico,
            headers=recusa.cabecalhos,
        ) from recusa

    if resultado is None:
        # Passo 7: reentrega. 200, NAO erro -- o Standard Webhooks manda a
        # plataforma retentar diante de qualquer resposta fora de 2xx, e
        # responder erro a uma reentrega legitima poria a integracao em laco
        # infinito por conta propria.
        #
        # O 200 e EXPLICITO no JSONResponse porque o decorador declara 201: sem
        # o status aqui, a reentrega herdaria o 201 e diria que gravou uma
        # conversa que ja existia.
        registrar("duplicada", "webhook-id ja processado")
        return JSONResponse(
            status_code=200, content={"duplicada": True, "webhook_id": webhook_id}
        )

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
    limitador: LimitadorDeVazao,
) -> dict | None:
    """Os passos 2 a 9. Devolve o veredito, ou None se for reentrega.

    Levanta `Recusa` -- nunca HTTPException -- para que quem chamou registre a
    entrega antes de responder.
    """
    # Passo 2: o segredo. 503, nao 401: variavel ausente e defeito da MAQUINA
    # que hospeda. Responder 401 mandaria quem integra depurar a propria
    # requisicao por um problema que nao e dele.
    #
    # O NOME DA VARIAVEL NAO SAI PELA REDE. Quem chama aqui e anonimo, e o
    # nome da variavel de ambiente da maquina que hospeda -- assim como o nome
    # da fonte e o texto do ValueError sobre o formato do segredo -- e estado
    # interno. Ele continua inteiro no `motivo`, que so se le em
    # `GET /integracoes/fontes/{id}/entregas`, atras de credencial: e ali que
    # quem opera precisa descobrir qual variavel falta, e e ali que ele esta.
    publico_sem_segredo = (
        "esta fonte nao esta com o segredo de webhook configurado na API -- "
        "e defeito da instalacao que hospeda, nao da sua requisicao; o motivo "
        "detalhado esta no historico de entregas da fonte"
    )
    nome_da_variavel = fonte["variavel_segredo"]
    if not nome_da_variavel:
        # Quando a fonte nem e do tipo 'webhook', a causa raiz nao e a
        # variavel ausente -- e o tipo. Uma fonte 'csv' ou 'discord' nunca vai
        # nomear variavel de segredo, e dizer so "nao nomeia variavel" faria
        # quem opera procurar um cadastro incompleto onde o que ha e uma
        # fonte do tipo errado. O passo 6 e que recusaria por tipo, mas uma
        # fonte sem segredo nunca chega la -- para aqui, no passo 2.
        motivo = (
            f"a fonte '{fonte['nome']}' nao nomeia variavel de ambiente para o "
            "segredo do webhook -- cadastre o nome dela na tela de Integracoes"
        )
        if fonte["tipo"] != "webhook":
            motivo += (
                f" (a fonte e do tipo '{fonte['tipo']}', nao 'webhook' -- "
                "essa e a causa raiz)"
            )
        raise Recusa(503, "sem_segredo", motivo, publico_sem_segredo)
    segredo = os.environ.get(nome_da_variavel)
    if not segredo:
        raise Recusa(503, "sem_segredo", (
            f"a variavel {nome_da_variavel} nao esta definida no ambiente da API"
        ), publico_sem_segredo)
    try:
        assinatura.chave_do_segredo(segredo)
    except ValueError as erro:
        raise Recusa(503, "sem_segredo", (
            f"a variavel {nome_da_variavel} nao carrega um segredo valido: {erro}"
        ), publico_sem_segredo) from erro

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

    # Passo 5b: o TETO DE VAZAO -- OWASP API4:2023. Cada entrega aceita roda o
    # Motor inteiro em CPU, e esta rota e ANONIMA por desenho: sem teto, um
    # laco de shell com o segredo de uma fonte enche o banco e ocupa o
    # processo.
    #
    # A POSICAO E LOGO DEPOIS DA ASSINATURA, e aqui isso pesa mais que em
    # `/ingestao`: o `fonte_id` vem na URL, entao qualquer anonimo escolhe
    # contra qual fonte bater. Contar a tentativa RECUSADA transformaria o teto
    # no caminho mais curto para derrubar a integracao de outra pessoa --
    # defesa que o atacante usa como arma. Depois do HMAC, quem chega aqui
    # provou ter o segredo da fonte, e a fonte e uma identidade que o lado de
    # fora nao forja.
    #
    # E `Recusa`, e nao `HTTPException` direta, porque toda recusa desta rota
    # vira linha em `entregas_webhook`: um 429 invisivel ali seria justamente a
    # recusa que o operador precisava ver, a que explica por que a plataforma
    # comecou a retentar. Isso e seguro para o dedupe SO PORQUE
    # `entrega_ja_vista` conta apenas veredito "aceita" -- ver o comentario
    # dela em `fraus/db.py`.
    espera = segundos_ate_a_vaga(limitador, str(fonte_id))
    if espera is not None:
        raise Recusa(
            429, "vazao",
            f"teto de {ENTREGAS_POR_JANELA} entregas por minuto atingido",
            "muitas entregas desta fonte -- aguarde antes de mandar de novo",
            {"Retry-After": str(espera)},
        )

    # Passo 6: o TIPO da fonte. So fonte cadastrada como `webhook` recebe
    # entrega por esta rota -- uma fonte `csv` que por acidente nomeie uma
    # variavel de segredo nao vira porta de escrita pela rede.
    #
    # A POSICAO E DEPOIS DA ASSINATURA, de proposito, junto do passo 7 e pelo
    # mesmo motivo dele: responder 403 antes do HMAC contaria a um anonimo o
    # tipo de cada fonte do cadastro, que e o estado interno que o passo 7 se
    # recusa a contar. Colocar este passo la em cima, logo apos buscar a fonte,
    # seria barato e coerente com "recusar cedo", mas trocaria o vazamento que
    # o item de revisao pediu para fechar por um vazamento novo. Quem chega
    # aqui ja provou que tem o segredo desta fonte; para essa pessoa, saber que
    # a fonte nao e de webhook e diagnostico, nao informacao privilegiada.
    #
    # O efeito colateral aceito: uma fonte nao-webhook SEM variavel de segredo
    # para no passo 2 com 503, e nao com este 403. As duas mensagens publicas
    # sao diferentes -- a do passo 2 fala em segredo nao configurado, a deste
    # passo em entrega por webhook nao aceita -- mas nenhuma delas conta o
    # tipo real da fonte a quem ainda nao provou identidade, que e a mesma
    # discricao que o passo 2 tem.
    if fonte["tipo"] != "webhook":
        raise Recusa(403, "tipo_incompativel", (
            f"a fonte '{fonte['nome']}' e do tipo '{fonte['tipo']}' e nao recebe "
            "entrega por webhook"
        ), "esta fonte nao recebe entrega por webhook")

    # Passo 7: a fonte ativa. DEPOIS da assinatura: informar que a fonte esta
    # desativada a quem nao provou identidade conta a um desconhecido o estado
    # interno do sistema.
    if not fonte["ativa"]:
        raise Recusa(403, "fonte_inativa", f"a fonte '{fonte['nome']}' esta desativada")

    # Passo 8: reentrega. Nao e recusa -- ver o comentario em `receber`.
    if ctx.banco.entrega_ja_vista(fonte_id, webhook_id):
        return None

    # Passo 9: so agora o corpo vira objeto.
    #
    # O motivo da Recusa NUNCA e `str(erro)`: `ValidationError.__str__` embute
    # o `input_value` recebido -- para JSON malformado, o corpo cru inteiro; e
    # para campo de tipo errado, o valor daquele campo (que pode ser fala real
    # de cliente). Esse motivo vai direto para `registrar_entrega` e fica na
    # coluna `motivo`, alem de sair no `detail` da resposta -- as duas rotas
    # persistiriam ou vazariam PII. `resumo_validacao` usa so o CAMINHO e o
    # TIPO do erro, nunca o valor.
    try:
        pedido = PedidoIngestao.model_validate_json(corpo)
    except ValidationError as erro:
        raise Recusa(400, "corpo_invalido", resumo_validacao(erro)) from erro

    try:
        return registrar_conversa(ctx, pedido, fonte)
    except HTTPException as erro:
        # `registrar_conversa` levanta 400 quando os campos nao montam uma
        # Conversa valida (timestamp naive, por exemplo). Vira Recusa para que
        # a entrega seja registrada como as outras.
        raise Recusa(erro.status_code, "corpo_invalido", str(erro.detail)) from erro
