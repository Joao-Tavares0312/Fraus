"""Assinatura de webhook de ENTRADA, no padrao Standard Webhooks.

Irmao do `credencial.py`, e a diferenca entre os dois e a razao de este modulo
existir separado:

- a chave `frs_` so precisa ser CONFERIDA, entao o banco guarda o hash dela e o
  segredo em claro pode morrer no instante em que e mostrado;
- a assinatura de webhook precisa ser RECOMPUTADA, e para isso o servidor
  precisa do segredo em claro toda vez.

Por isso o segredo daqui nunca entra no banco: a fonte guarda o NOME de uma
variavel de ambiente, e o valor mora no ambiente da maquina onde a API roda.
O `fraus.db` continua sem levar credencial junto num backup vazado.

TRES DECISOES, e o motivo de cada uma:

1. **O padrao e o Standard Webhooks, nao um formato nosso.** Os cabecalhos sao
   `webhook-id`, `webhook-timestamp` e `webhook-signature`, e o que se assina e
   `{id}.{timestamp}.{corpo}`. Inventar um formato proprio custaria o mesmo
   trabalho e entregaria menos: com o padrao, quem integra usa biblioteca de
   prateleira em vez de ler a nossa documentacao.

2. **O segredo e `whsec_<base64>` e a chave HMAC e o base64 DECODIFICADO.**
   Usar a string inteira seria mais simples e mataria o unico motivo de adotar
   o padrao -- a biblioteca do outro lado faz o decode, geraria outra
   assinatura, e nada bateria.

3. **O corpo entra aqui como BYTES, nunca como str ou dict.** HMAC e
   byte-exato: desserializar e re-serializar para conferir muda a assinatura
   por reordenacao de chave ou por um espaco de diferenca. A assinatura do tipo
   e o que impede alguem de passar um dict sem perceber.
"""

import base64
import binascii
import hashlib
import hmac
import secrets

PREFIXO = "whsec"

# 32 bytes = 256 bits, o mesmo piso do `credencial.py`. Nao ha dicionario que
# chegue perto de um segredo sorteado desse tamanho.
BYTES_DO_SEGREDO = 32

# Cinco minutos, o valor que a especificacao sugere e que os provedores usam.
# Apertar mais transformaria relogio levemente dessincronizado em recusa; afrouxar
# alarga a janela em que uma captura da rede continua valendo.
JANELA_SEGUNDOS = 300

VERSAO = "v1"


def gerar_segredo() -> str:
    """Segredo novo, no formato que a especificacao define.

    NUNCA e persistido pelo Fraus: sai uma vez na resposta da rota, o operador
    poe na variavel de ambiente e a plataforma recebe a copia.
    """
    return f"{PREFIXO}_{base64.b64encode(secrets.token_bytes(BYTES_DO_SEGREDO)).decode()}"


def chave_do_segredo(segredo: str) -> bytes:
    """Os bytes da chave HMAC, decodificados do segredo.

    LEVANTA `ValueError` em vez de devolver `None`, e a diferenca importa:
    segredo malformado e defeito da maquina que hospeda -- alguem preencheu a
    variavel de ambiente errado. A rota traduz isso em 503 nomeando a variavel,
    nunca em 401: mandar quem integra depurar a propria requisicao por um
    problema que nao e dele custa horas de quem nao pode conserta-lo.
    """
    if not segredo or not segredo.startswith(f"{PREFIXO}_"):
        raise ValueError(f"segredo de webhook deve comecar com '{PREFIXO}_'")
    corpo = segredo[len(PREFIXO) + 1:]
    if not corpo:
        raise ValueError("segredo de webhook sem a parte codificada")
    try:
        # `validate=True` para que caractere fora do alfabeto base64 seja erro,
        # e nao um descarte silencioso que produziria uma chave curta e uma
        # recusa de assinatura sem explicacao.
        return base64.b64decode(corpo, validate=True)
    except (binascii.Error, ValueError) as erro:
        raise ValueError("segredo de webhook nao e base64 valido") from erro


def _conteudo_assinado(webhook_id: str, timestamp: str, corpo: bytes) -> bytes:
    """`{id}.{timestamp}.{corpo}` -- os tres, sempre, e nessa ordem.

    O id entra para que a assinatura pertenca AQUELE evento, e o timestamp para
    que ela expire. Assinar so o corpo deixaria uma captura da rede valida para
    sempre e reaproveitavel em qualquer evento.
    """
    return f"{webhook_id}.{timestamp}.".encode("utf-8") + corpo


def assinar(webhook_id: str, timestamp: str, corpo: bytes, segredo: str) -> str:
    """A assinatura no formato do cabecalho: `v1,<base64>`."""
    digesto = hmac.new(
        chave_do_segredo(segredo),
        _conteudo_assinado(webhook_id, timestamp, corpo),
        hashlib.sha256,
    ).digest()
    return f"{VERSAO},{base64.b64encode(digesto).decode()}"


def confere(
    webhook_id: str, timestamp: str, corpo: bytes, segredo: str, recebida: str
) -> bool:
    """Confere em TEMPO CONSTANTE, e aceita mais de uma assinatura no cabecalho.

    `==` vaza, pelo tempo, quantos bytes bateram -- suficiente para descobrir a
    assinatura byte a byte. `hmac.compare_digest` nao vaza.

    O cabecalho pode trazer VARIAS assinaturas separadas por espaco, e recusar
    isso quebraria justamente a rotacao de segredo sem janela de
    indisponibilidade, que e o motivo de a especificacao permitir. Basta uma
    bater. Todas sao comparadas mesmo depois de uma bater, para que o tempo de
    resposta nao conte QUAL delas era a boa.
    """
    if not recebida:
        return False
    esperada = assinar(webhook_id, timestamp, corpo, segredo)
    achou = False
    for candidata in recebida.split(" "):
        if hmac.compare_digest(candidata.strip(), esperada):
            achou = True
    return achou


def dentro_da_janela(timestamp: str, agora: int) -> bool:
    """Janela de +/- 5 min. Vale para os DOIS lados.

    Relogio adiantado no remetente e caso real, e aceitar timestamp futuro sem
    limite deixaria uma captura da rede valida para sempre -- que e exatamente
    o ataque que o timestamp existe para fechar.

    Timestamp nao numerico e recusa, nao excecao: ele vem da rede.
    """
    try:
        enviado = int(timestamp)
    except (TypeError, ValueError):
        return False
    return abs(agora - enviado) <= JANELA_SEGUNDOS
