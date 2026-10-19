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
