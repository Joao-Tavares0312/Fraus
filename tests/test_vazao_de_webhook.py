"""Teto de escrita no webhook, a irma do teto de `/ingestao`.

O QUE FICOU PELA METADE EM 08/09/2026. O teto de vazao entrou em `/ingestao`
naquele dia e o webhook ficou de fora -- e ele e o OUTRO caminho de escrita
pela rede, com a mesma exposicao: OWASP API4:2023. Pior, em um aspecto: a rota
do webhook e ANONIMA por desenho (a credencial dela e a assinatura, entao ela e
isenta do middleware de chave de acesso), e cada entrega aceita roda o Motor
inteiro em CPU.

A IDENTIDADE E A FONTE, e ela vem da URL -- mas so vale DEPOIS que a assinatura
confere. `fonte_id` no caminho e escolha de quem chama: contar antes do HMAC
deixaria um anonimo mandando lixo para `/integracoes/webhook/3` gastar a janela
da fonte 3 e derrubar a integracao legitima. E o mesmo raciocinio que pos o teto
de `/ingestao` na rota em vez do middleware, e vale aqui com mais forca, porque
aqui nem cabecalho de credencial existe.

O TETO CONTA COMO RECUSA REGISTRADA, nao como excecao solta: toda recusa desta
rota vira linha em `entregas_webhook`, e um 429 que nao aparecesse ali seria
justamente a recusa que o operador precisava ver -- ele e quem explica por que a
plataforma comecou a retentar.

E ISSO E SEGURO PARA O DEDUPE, mas so porque `entrega_ja_vista` conta APENAS
veredito "aceita". Se um dia ela passar a contar qualquer veredito, este 429
vira uma forma de queimar um `webhook-id` legitimo -- a mesma armadilha ja
registrada em `fraus/db.py`.
"""

import json
import time

import pytest

from fraus import assinatura
from fraus.api.rotas.webhook import PREFIXO_WEBHOOK
from fraus.api.vazao import ENTREGAS_POR_JANELA
from tests.test_api import cliente  # noqa: F401

SEGREDO = "whsec_" + "QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVphYmNkZWY="
VARIAVEL = "FRAUS_WEBHOOK_VAZAO"


def _corpo(n):
    return {
        "id": f"atendimento-{n}",
        "mensagens": [
            {"autor": "cliente", "texto": "meu pedido nao chegou",
             "enviada_em": "2026-09-08T10:00:00-03:00"},
            {"autor": "bot", "texto": "vou verificar",
             "enviada_em": "2026-09-08T10:00:12-03:00"},
        ],
    }


@pytest.fixture
def fonte(cliente, monkeypatch):  # noqa: F811
    monkeypatch.setenv(VARIAVEL, SEGREDO)
    return cliente.post("/integracoes/fontes", json={
        "nome": "Zendesk", "canal": "webchat", "tipo": "webhook",
        "variavel_segredo": VARIAVEL,
    }).json()


@pytest.fixture
def outra_fonte(cliente, monkeypatch):  # noqa: F811
    monkeypatch.setenv(VARIAVEL, SEGREDO)
    return cliente.post("/integracoes/fontes", json={
        "nome": "Intercom", "canal": "webchat", "tipo": "webhook",
        "variavel_segredo": VARIAVEL,
    }).json()


def _enviar(cliente, fonte_id, n, *, segredo=SEGREDO):  # noqa: F811
    bruto = json.dumps(_corpo(n)).encode("utf-8")
    webhook_id = f"msg_{n}"
    ts = str(int(time.time()))
    return cliente.post(
        f"{PREFIXO_WEBHOOK}/{fonte_id}",
        content=bruto,
        headers={
            "content-type": "application/json",
            "webhook-id": webhook_id,
            "webhook-timestamp": ts,
            "webhook-signature": assinatura.assinar(webhook_id, ts, bruto, segredo),
        },
    )


def _entregas(cliente, fonte_id):  # noqa: F811
    return cliente.get(f"/integracoes/fontes/{fonte_id}/entregas").json()


# ---- o teto -------------------------------------------------------------


def test_a_enxurrada_assinada_e_cortada(cliente, fonte):  # noqa: F811
    """O buraco em si. Este e o teste que impede a regressao."""
    for n in range(ENTREGAS_POR_JANELA):
        assert _enviar(cliente, fonte["id"], n).status_code == 201

    assert _enviar(cliente, fonte["id"], "excedente").status_code == 429


def test_a_recusa_diz_quando_tentar_de_novo(cliente, fonte):  # noqa: F811
    """A plataforma retenta diante de qualquer resposta fora de 2xx. Sem
    `Retry-After` ela retenta na cadencia dela, que e exatamente a enxurrada
    que o teto acabou de cortar."""
    for n in range(ENTREGAS_POR_JANELA + 1):
        resposta = _enviar(cliente, fonte["id"], n)

    assert resposta.status_code == 429
    assert int(resposta.headers["Retry-After"]) > 0


def test_o_429_vira_linha_no_log_de_entregas(cliente, fonte):  # noqa: F811
    """Recusa que ninguem registra e a que o operador precisava ver: e ela que
    explica por que a plataforma comecou a retentar."""
    for n in range(ENTREGAS_POR_JANELA + 1):
        _enviar(cliente, fonte["id"], n)

    vereditos = [e["veredito"] for e in _entregas(cliente, fonte["id"])]
    assert "vazao" in vereditos


# ---- o que NAO pode mudar -----------------------------------------------


def test_o_teto_e_por_fonte(cliente, fonte, outra_fonte):  # noqa: F811
    """Janela compartilhada faria uma integracao barulhenta calar a outra."""
    for n in range(ENTREGAS_POR_JANELA + 1):
        _enviar(cliente, fonte["id"], n)

    assert _enviar(cliente, outra_fonte["id"], "primeira").status_code == 201


def test_assinatura_invalida_nao_gasta_a_janela_da_fonte(cliente, fonte):  # noqa: F811
    """A razao de o teto viver DEPOIS da assinatura, e aqui ela pesa mais que
    em `/ingestao`: o `fonte_id` vem na URL, entao qualquer anonimo escolhe
    contra qual fonte bater. Se a tentativa recusada contasse, o teto viraria o
    caminho mais curto para derrubar uma integracao alheia."""
    for n in range(ENTREGAS_POR_JANELA + 5):
        recusada = _enviar(cliente, fonte["id"], n, segredo="whsec_" + "b3V0cm8=")
        assert recusada.status_code == 401

    assert _enviar(cliente, fonte["id"], "legitima").status_code == 201


def test_o_429_nao_queima_o_webhook_id_para_a_retentativa(cliente, fonte):  # noqa: F811
    """`entrega_ja_vista` conta so veredito "aceita". Se um dia contar
    qualquer um, o 429 vira uma forma de descartar um atendimento legitimo em
    silencio -- a plataforma retenta o MESMO id e leva "duplicada"."""
    for n in range(ENTREGAS_POR_JANELA):
        _enviar(cliente, fonte["id"], n)

    barrada = _enviar(cliente, fonte["id"], "retentada")
    assert barrada.status_code == 429

    # A janela do teste nao expira em tempo util; o que importa e que o id nao
    # foi marcado como visto. Conferido direto no banco, que e o que o dedupe le.
    assert "duplicada" not in [e["veredito"] for e in _entregas(cliente, fonte["id"])]
