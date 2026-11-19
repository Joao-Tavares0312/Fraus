"""O contrato que o TARS usa: a conversa inteira, reenviada a cada turno.

O TARS manda o retrato do chat depois de cada resposta do bot (19/10/2026).
O mesmo `id` com mais mensagens SUBSTITUI a conversa -- senao cada turno
viraria um atendimento novo e o NPS contaria o mesmo cliente varias vezes.
"""

from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco
from tests.test_api import MotorFalso
from tests.test_vazao_de_ingestao import _fonte_com_chave


def _turnos(n):
    falas = []
    for i in range(n):
        falas.append({"autor": "cliente", "texto": f"pergunta {i}",
                      "enviada_em": f"2026-09-23T12:{i:02d}:00-03:00"})
        falas.append({"autor": "bot", "texto": f"resposta {i}",
                      "enviada_em": f"2026-09-23T12:{i:02d}:05-03:00"})
    return falas


def test_reenvio_do_mesmo_chat_atualiza_sem_duplicar(tmp_path):
    banco = Banco(tmp_path / "fraus.db")
    banco.migrar()
    cliente = TestClient(criar_app(banco=banco, motor=MotorFalso(), raiz_importacao=tmp_path))
    chave = _fonte_com_chave(cliente, nome="TARS")
    cabecalho = {"Authorization": f"Bearer {chave}"}

    primeiro = cliente.post("/ingestao", headers=cabecalho,
                            json={"id": "inst_x:telegram:8624457065", "mensagens": _turnos(1)})
    assert primeiro.status_code == 201, primeiro.text
    segundo = cliente.post("/ingestao", headers=cabecalho,
                           json={"id": "inst_x:telegram:8624457065", "mensagens": _turnos(3)})
    assert segundo.status_code == 201, segundo.text

    assert primeiro.json()["id"] == segundo.json()["id"]
    todas = banco.todas()
    assert len(todas) == 1
    assert len(todas[0][0].mensagens) == 6


def test_reenvio_substitui_o_voto_junto_com_a_conversa(tmp_path):
    """O voto mora no payload, e o payload e substituido inteiro.

    Por isso o TARS relê o voto do banco e o manda em TODO envio (19/11/2026):
    reenviar sem `feedback_declarado` apaga o voto aqui. Este teste fixa o
    contrato de substituicao, nao uma regra nova.
    """
    banco = Banco(tmp_path / "fraus.db")
    banco.migrar()
    cliente = TestClient(criar_app(banco=banco, motor=MotorFalso(), raiz_importacao=tmp_path))
    chave = _fonte_com_chave(cliente, nome="TARS")
    cabecalho = {"Authorization": f"Bearer {chave}"}
    ident = "tars:v2:inst_x:telegram:0123456789abcdef0123456789abcdef:1763550000"

    for turnos in (1, 2):
        resposta = cliente.post("/ingestao", headers=cabecalho, json={
            "id": ident, "mensagens": _turnos(turnos),
            "feedback_declarado": 1, "comentario_feedback": "resolveu rapido",
        })
        assert resposta.status_code == 201, resposta.text
    todas = banco.todas()
    assert len(todas) == 1
    assert todas[0][0].feedback_declarado == 1
    assert todas[0][0].comentario_feedback == "resolveu rapido"

    sem_voto = cliente.post("/ingestao", headers=cabecalho,
                            json={"id": ident, "mensagens": _turnos(3)})
    assert sem_voto.status_code == 201, sem_voto.text
    todas = banco.todas()
    assert len(todas) == 1
    assert todas[0][0].feedback_declarado is None
    assert todas[0][0].comentario_feedback is None
