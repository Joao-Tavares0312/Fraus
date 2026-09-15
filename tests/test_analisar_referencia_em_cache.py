"""`/analisar` nao desserializa o banco inteiro a cada chamada.

No Supabase, `banco.todas()` atravessa a rede e custa proporcional ao banco.
A referencia de vocabulario so muda quando as conversas mudam -- entao ela e
reaproveitada enquanto a assinatura do banco for a mesma, e refeita quando
nao for. Nunca copia envelhecida: a assinatura e conferida A CADA analise.
"""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco
from fraus.modelos import Conversa, Mensagem
from tests.test_api import CSV, MotorRespeitandoSinal


def _montar(tmp_path):
    banco = Banco(tmp_path / "t.db")
    banco.migrar()
    chamadas = []
    original = banco.todas
    banco.todas = lambda: (chamadas.append(1), original())[1]
    cliente = TestClient(criar_app(banco=banco, motor=MotorRespeitandoSinal(), raiz_importacao=tmp_path))
    return cliente, banco, chamadas


def test_segunda_analise_com_banco_igual_nao_rele_o_banco(tmp_path):
    cliente, _, chamadas = _montar(tmp_path)
    cliente.post("/analisar", json={"csv": CSV})
    cliente.post("/analisar", json={"csv": CSV})
    assert len(chamadas) == 1


def test_banco_mudou_a_referencia_e_refeita(tmp_path):
    cliente, banco, chamadas = _montar(tmp_path)
    antes = cliente.post("/analisar", json={"csv": CSV}).json()
    agora = datetime(2026, 8, 13, 10, tzinfo=timezone.utc)
    banco.salvar(Conversa(id="x", canal="csv", iniciada_em=agora, mensagens=[
        Mensagem(autor="cliente", texto="otimo otimo", enviada_em=agora)]), 50.0, "neutro")
    depois = cliente.post("/analisar", json={"csv": CSV}).json()
    assert len(chamadas) == 2
    assert depois["referencia_conversas"] == antes["referencia_conversas"] + 1
