"""Teto de escrita em `/ingestao`, POR FONTE AUTENTICADA.

O QUE ISTO FECHA: OWASP API4:2023 (Unrestricted Resource Consumption). Uma
chave `frs_` vazada nao dava acesso de leitura -- so de escrita -- mas dava
escrita SEM TETO: cada `POST /ingestao` roda o Motor inteiro (BERTimbau,
emocao, ironia, fusor) em CPU. Um laco de shell com uma chave valida enchia o
banco e ocupava o processo, e o unico limite era a paciencia de quem atacava.

POR QUE NAO NO MIDDLEWARE, ONDE MORA O TETO DE `/auth/*`. O middleware roda
antes da autenticacao, entao so poderia contar por IP ou pela chave CRUA. As
duas escolhas sao piores:

  - por IP: uma plataforma de verdade (Discord, WhatsApp) chama de um punhado
    de IPs de saida compartilhados; o teto viraria obstaculo de uso normal;
  - pela chave crua: `fonte_da_chave` le o id SEM conferir o hash, entao
    qualquer anonimo forjando `frs_3_lixo` gastaria a janela da fonte 3 e
    derrubaria a integracao legitima. Defesa que o atacante usa como arma.

Contar DEPOIS de `fonte_autorizada` custa um sha256 e uma consulta -- barato
perto da inferencia que vem em seguida, e e a unica identidade que o lado de
fora nao consegue forjar.

O TETO E POR PROCESSO, como o de `/auth/*`. Nao e defesa contra botnet: e
defesa contra o laco de uma sessao, que e o caso real.
"""

import pytest
from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.api.vazao import INGESTOES_POR_JANELA
from fraus.db import Banco
from tests.test_api import MotorFalso

MENSAGENS = [
    {"autor": "cliente", "texto": "oi", "enviada_em": "2026-01-01T10:00:00+00:00"},
    {"autor": "bot", "texto": "ola", "enviada_em": "2026-01-01T10:00:05+00:00"},
]


@pytest.fixture
def cliente(tmp_path):
    banco = Banco(tmp_path / "fraus.db")
    banco.migrar()
    return TestClient(
        criar_app(banco=banco, motor=MotorFalso(), raiz_importacao=tmp_path)
    )


def _fonte_com_chave(cliente, nome="Suporte") -> str:
    fonte_id = cliente.post(
        "/integracoes/fontes",
        json={"nome": nome, "canal": "whatsapp", "tipo": "webhook"},
    ).json()["id"]
    return cliente.post(f"/integracoes/fontes/{fonte_id}/chave").json()["chave"]


def _ingerir(cliente, chave, n):
    return cliente.post(
        "/ingestao",
        json={"id": f"conversa-{n}", "mensagens": MENSAGENS},
        headers={"Authorization": f"Bearer {chave}"},
    )


# ---- o teto -------------------------------------------------------------


def test_a_enxurrada_de_escrita_e_cortada(cliente):
    """O buraco em si. Este e o teste que impede a regressao."""
    chave = _fonte_com_chave(cliente)
    for n in range(INGESTOES_POR_JANELA):
        assert _ingerir(cliente, chave, n).status_code == 201

    assert _ingerir(cliente, chave, "excedente").status_code == 429


def test_a_recusa_diz_quando_tentar_de_novo(cliente):
    """Integrador sem `Retry-After` so tem uma pista: continuar batendo."""
    chave = _fonte_com_chave(cliente)
    for n in range(INGESTOES_POR_JANELA + 1):
        resposta = _ingerir(cliente, chave, n)

    assert resposta.status_code == 429
    assert int(resposta.headers["Retry-After"]) > 0


# ---- o que NAO pode mudar -----------------------------------------------


def test_uma_fonte_no_teto_nao_derruba_a_outra(cliente):
    """A janela e POR FONTE. Compartilhar o teto faria uma integracao
    barulhenta calar a outra -- e daria a quem tem uma chave qualquer o poder
    de bloquear todas as demais."""
    barulhenta = _fonte_com_chave(cliente, "Barulhenta")
    quieta = _fonte_com_chave(cliente, "Quieta")

    for n in range(INGESTOES_POR_JANELA + 1):
        _ingerir(cliente, barulhenta, n)

    assert _ingerir(cliente, quieta, "primeira").status_code == 201


def test_chave_forjada_nao_gasta_a_janela_da_fonte_legitima(cliente):
    """A razao de o teto viver DEPOIS da autenticacao. `frs_<id>_lixo` carrega
    um id de fonte que ninguem conferiu; se ele contasse, o teto viraria a arma
    do atacante contra a integracao de verdade."""
    chave = _fonte_com_chave(cliente)
    fonte_id = chave.split("_")[1]

    for n in range(INGESTOES_POR_JANELA + 5):
        forjada = _ingerir(cliente, f"frs_{fonte_id}_lixo", n)
        assert forjada.status_code == 401

    assert _ingerir(cliente, chave, "legitima").status_code == 201


def test_o_teto_de_ingestao_nao_alcanca_a_leitura(cliente):
    """A dashboard dispara varias chamadas por render. O teto de escrita nao
    pode virar teto de tela."""
    chave = _fonte_com_chave(cliente)
    for n in range(INGESTOES_POR_JANELA + 1):
        _ingerir(cliente, chave, n)

    assert cliente.get("/conversas").status_code == 200
    assert cliente.get("/indicadores").status_code == 200
