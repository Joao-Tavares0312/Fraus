"""POST /integracoes/webhook/{fonte_id} -- o porteiro de oito passos.

A ordem e identidade, depois autoridade, depois parse: nada de desserializar
JSON, tocar no banco ou pontuar antes de a assinatura passar.
"""

import json

import pytest

from fraus import assinatura
from fraus.api.rotas.webhook import PREFIXO_WEBHOOK

# Reusa as fixtures de tests/test_api.py -- `cliente` monta o app com o motor
# duble. Um conftest proprio criaria um segundo app para manter em dia.
from tests.test_api import cliente  # noqa: F401

SEGREDO = "whsec_" + "QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVphYmNkZWY="
VARIAVEL = "FRAUS_WEBHOOK_TESTE"

CORPO = {
    "id": "atendimento-1",
    "mensagens": [
        {"autor": "cliente", "texto": "meu pedido nao chegou",
         "enviada_em": "2026-08-27T10:00:00-03:00"},
        {"autor": "bot", "texto": "vou verificar",
         "enviada_em": "2026-08-27T10:00:12-03:00"},
    ],
}


@pytest.fixture
def fonte(cliente, monkeypatch):  # noqa: F811
    """Fonte de webhook com o segredo presente no ambiente da API."""
    monkeypatch.setenv(VARIAVEL, SEGREDO)
    return cliente.post("/integracoes/fontes", json={
        "nome": "Zendesk", "canal": "webchat", "tipo": "webhook",
        "variavel_segredo": VARIAVEL,
    }).json()


def _enviar(cliente, fonte_id, corpo=None, *, segredo=SEGREDO, webhook_id="msg_1",
            timestamp=None, agora=None, assinada=None):
    """Monta e envia uma chamada assinada. Serializa UMA vez e assina esses
    bytes exatos -- reserializar para assinar e o defeito que os testes caçam."""
    import time
    bruto = json.dumps(CORPO if corpo is None else corpo).encode("utf-8")
    ts = timestamp if timestamp is not None else str(int(agora or time.time()))
    return cliente.post(
        f"{PREFIXO_WEBHOOK}/{fonte_id}",
        content=bruto,
        headers={
            "content-type": "application/json",
            "webhook-id": webhook_id,
            "webhook-timestamp": ts,
            "webhook-signature": assinada if assinada is not None
                                 else assinatura.assinar(webhook_id, ts, bruto, segredo),
        },
    )


def _entregas(cliente, fonte_id):
    return cliente.get(f"/integracoes/fontes/{fonte_id}/entregas").json()


# --- o caminho feliz --------------------------------------------------------

def test_assinatura_valida_e_aceita_e_grava_a_conversa(cliente, fonte):  # noqa: F811
    resposta = _enviar(cliente, fonte["id"])
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["id"] == "atendimento-1"
    assert corpo["fonte"] == "Zendesk"
    assert [c["id"] for c in cliente.get("/conversas").json()] == ["atendimento-1"]


def test_o_canal_e_o_da_fonte_nunca_o_do_corpo(cliente, fonte):  # noqa: F811
    """Quem manda o dado nao escolhe em que canal ele e contabilizado."""
    _enviar(cliente, fonte["id"], corpo={**CORPO, "canal": "inventado"})
    assert cliente.get("/conversas").json()[0]["canal"] == "webchat"


@pytest.mark.parametrize("campo,valor", [
    # MotorFalso sempre devolve score 90.0 -- nota 9, categoria "promotor".
    # Os valores injetados aqui sao os que NAO batem com o que o motor duble
    # de fato produz, para que a asserçao prove que o corpo foi ignorado e
    # nao acerte por coincidencia com o resultado real.
    ("score", 1.0), ("nota", 2), ("categoria", "detrator"),
])
def test_veredito_no_corpo_e_ignorado(cliente, fonte, campo, valor):  # noqa: F811
    """Invariante 3: score, nota e categoria sao derivados no SERVIDOR."""
    resposta = _enviar(cliente, fonte["id"], corpo={**CORPO, campo: valor})
    assert resposta.status_code == 201
    assert resposta.json()[campo] != valor


# --- o porteiro, um teste por passo -----------------------------------------

def test_fonte_inexistente_e_404(cliente, fonte):  # noqa: F811
    assert _enviar(cliente, 99999).status_code == 404


def test_variavel_ausente_no_ambiente_e_503_nomeando_a_variavel(
    cliente, fonte, monkeypatch,  # noqa: F811
):
    """503, nao 401: variavel ausente e defeito da MAQUINA que hospeda.

    Responder 401 mandaria quem integra caçar um problema que nao e dele --
    horas gastas por quem nem consegue conserta-lo."""
    monkeypatch.delenv(VARIAVEL, raising=False)
    resposta = _enviar(cliente, fonte["id"])
    assert resposta.status_code == 503
    assert VARIAVEL in resposta.json()["detail"]
    assert _entregas(cliente, fonte["id"])[0]["veredito"] == "sem_segredo"


def test_fonte_sem_variavel_nomeada_e_503(cliente):  # noqa: F811
    """Fonte de webhook sem variavel nomeada nao tem como conferir nada."""
    sem = cliente.post("/integracoes/fontes", json={
        "nome": "Solta", "canal": "webchat", "tipo": "webhook",
    }).json()
    assert _enviar(cliente, sem["id"]).status_code == 503


@pytest.mark.parametrize("faltando", ["webhook-id", "webhook-timestamp", "webhook-signature"])
def test_cabecalho_ausente_e_400(cliente, fonte, faltando):  # noqa: F811
    import time
    bruto = json.dumps(CORPO).encode("utf-8")
    ts = str(int(time.time()))
    cabecalhos = {
        "content-type": "application/json",
        "webhook-id": "msg_1",
        "webhook-timestamp": ts,
        "webhook-signature": assinatura.assinar("msg_1", ts, bruto, SEGREDO),
    }
    del cabecalhos[faltando]
    resposta = cliente.post(
        f"{PREFIXO_WEBHOOK}/{fonte['id']}", content=bruto, headers=cabecalhos
    )
    assert resposta.status_code == 400
    assert faltando in resposta.json()["detail"]


def test_timestamp_velho_e_400_e_nao_grava_conversa(cliente, fonte):  # noqa: F811
    import time
    resposta = _enviar(cliente, fonte["id"], agora=time.time() - 3600)
    assert resposta.status_code == 400
    assert cliente.get("/conversas").json() == []
    assert _entregas(cliente, fonte["id"])[0]["veredito"] == "fora_da_janela"


def test_timestamp_muito_no_futuro_e_400(cliente, fonte):  # noqa: F811
    """A janela vale para os dois lados: aceitar futuro sem limite deixaria
    uma captura da rede valida para sempre."""
    import time
    assert _enviar(cliente, fonte["id"], agora=time.time() + 3600).status_code == 400


def test_assinatura_errada_e_401_e_nao_grava_conversa(cliente, fonte):  # noqa: F811
    resposta = _enviar(cliente, fonte["id"], assinada="v1,QUJDREVG")
    assert resposta.status_code == 401
    assert cliente.get("/conversas").json() == []
    assert _entregas(cliente, fonte["id"])[0]["veredito"] == "assinatura"


def test_corpo_alterado_depois_de_assinado_e_401(cliente, fonte):  # noqa: F811
    """O teste central do modulo: prova que a conferencia e sobre os BYTES
    CRUS que chegaram, nao sobre o dict reserializado."""
    import time
    bruto = json.dumps(CORPO).encode("utf-8")
    ts = str(int(time.time()))
    assinada = assinatura.assinar("msg_1", ts, bruto, SEGREDO)
    resposta = cliente.post(
        f"{PREFIXO_WEBHOOK}/{fonte['id']}",
        content=bruto + b" ",  # um unico byte a mais
        headers={
            "content-type": "application/json", "webhook-id": "msg_1",
            "webhook-timestamp": ts, "webhook-signature": assinada,
        },
    )
    assert resposta.status_code == 401


def test_fonte_desativada_e_403_e_so_DEPOIS_da_assinatura(cliente, fonte):  # noqa: F811
    """403 depois da assinatura de proposito: informar que a fonte esta
    desativada a quem nao provou identidade conta a um desconhecido o estado
    interno do sistema."""
    cliente.patch(f"/integracoes/fontes/{fonte['id']}", json={"ativa": False})
    assert _enviar(cliente, fonte["id"]).status_code == 403
    # assinatura errada em fonte desativada responde 401, nao 403 -- a ordem
    # do porteiro e observavel daqui.
    assert _enviar(cliente, fonte["id"], assinada="v1,QUJD").status_code == 401


def test_reentrega_do_mesmo_webhook_id_e_200_e_nao_duplica(cliente, fonte):  # noqa: F811
    """200, NAO erro. O Standard Webhooks manda a plataforma retentar diante de
    qualquer resposta fora de 2xx -- responder erro a uma reentrega legitima
    poria a integracao em laco infinito por conta propria."""
    assert _enviar(cliente, fonte["id"], webhook_id="msg_1").status_code == 201
    repetida = _enviar(cliente, fonte["id"], webhook_id="msg_1")
    assert repetida.status_code == 200
    assert repetida.json()["duplicada"] is True
    assert len(cliente.get("/conversas").json()) == 1
    assert _entregas(cliente, fonte["id"])[0]["veredito"] == "duplicada"


def test_corpo_que_nao_bate_o_contrato_e_400(cliente, fonte):  # noqa: F811
    resposta = _enviar(cliente, fonte["id"], corpo={"id": "x", "mensagens": []})
    assert resposta.status_code == 400
    assert _entregas(cliente, fonte["id"])[0]["veredito"] == "corpo_invalido"


def test_corpo_que_nao_e_json_e_400_sem_explodir(cliente, fonte):  # noqa: F811
    import time
    ts = str(int(time.time()))
    bruto = b"isto nao e json"
    resposta = cliente.post(
        f"{PREFIXO_WEBHOOK}/{fonte['id']}", content=bruto,
        headers={
            "content-type": "application/json", "webhook-id": "msg_1",
            "webhook-timestamp": ts,
            "webhook-signature": assinatura.assinar("msg_1", ts, bruto, SEGREDO),
        },
    )
    assert resposta.status_code == 400


# --- o registro -------------------------------------------------------------

def test_entrega_aceita_aponta_a_conversa_que_gerou(cliente, fonte):  # noqa: F811
    _enviar(cliente, fonte["id"])
    (entrega,) = _entregas(cliente, fonte["id"])
    assert entrega["veredito"] == "aceita"
    assert entrega["conversa_id"] == "atendimento-1"


def test_o_corpo_da_requisicao_nao_aparece_em_entrega_nenhuma(cliente, fonte):  # noqa: F811
    """O corpo e PII de cliente real. Depurar se resolve com veredito e motivo."""
    _enviar(cliente, fonte["id"])
    assert "meu pedido nao chegou" not in cliente.get(
        f"/integracoes/fontes/{fonte['id']}/entregas"
    ).text


# --- a regressao que so apareceria em producao ------------------------------

def test_a_rota_responde_com_a_mestra_ligada_sem_exigir_chave_de_acesso(
    tmp_path, monkeypatch,
):
    """A regressao de ISENTAS, e ela e silenciosa.

    Com FRAUS_CHAVE_MESTRA definida, o middleware exige `Bearer fra_` em toda
    rota fora da lista. A plataforma externa nao tem -- nem pode ter -- uma
    chave de acesso: a credencial dela e a ASSINATURA. Sem a rota na lista,
    toda chamada levaria 401 antes de a assinatura ser olhada, e o log de
    entregas ficaria vazio dizendo "nao chegou nada" enquanto a plataforma
    recebe 401 em cada tentativa.
    """
    from fastapi.testclient import TestClient
    from tests.test_api import MotorFalso  # o duble ja usado pela suite
    from fraus.api.main import criar_app
    from fraus.db import Banco

    monkeypatch.setenv(VARIAVEL, SEGREDO)
    banco = Banco(tmp_path / "fraus.db")
    banco.migrar()
    app = criar_app(banco=banco, motor=MotorFalso(), raiz_importacao=tmp_path,
                    chave_mestra="mestra-secreta")
    protegido = TestClient(app)

    fonte_criada = protegido.post(
        "/integracoes/fontes",
        json={"nome": "Zendesk", "canal": "webchat", "tipo": "webhook",
              "variavel_segredo": VARIAVEL},
        headers={"Authorization": "Bearer mestra-secreta"},
    ).json()

    # Sem Authorization nenhum -- so a assinatura.
    assert _enviar(protegido, fonte_criada["id"]).status_code == 201


def test_a_url_com_barra_final_tambem_passa_pelo_middleware(cliente, fonte):  # noqa: F811
    """Quem cadastra a URL do outro lado poe barra final o tempo todo, e o
    Starlette redireciona -- mas a lista ISENTAS compara o path."""
    import time
    bruto = json.dumps(CORPO).encode("utf-8")
    ts = str(int(time.time()))
    resposta = cliente.post(
        f"{PREFIXO_WEBHOOK}/{fonte['id']}/", content=bruto,
        headers={
            "content-type": "application/json", "webhook-id": "msg_1",
            "webhook-timestamp": ts,
            "webhook-signature": assinatura.assinar("msg_1", ts, bruto, SEGREDO),
        },
        follow_redirects=True,
    )
    assert resposta.status_code == 201
