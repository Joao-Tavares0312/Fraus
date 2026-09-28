"""A explicacao da nota usa o MESMO lexico que produziu a nota.

O score gravado sai pontuado com a curadoria vigente. Se `/atribuicao` e
`/analisar` explicassem com o lexico de fabrica, a tela mostraria evidencia
que nao produziu o numero -- pior que nao explicar.
"""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco
from fraus.modelos import Conversa, Mensagem

CSV = (
    "conversa_id,canal,autor,texto,enviada_em,escalou_para_humano\n"
    "c1,csv,cliente,lentissimo,2026-08-13T10:00:00+00:00,false\n"
    "c1,csv,bot,de nada,2026-08-13T10:00:08+00:00,false\n"
)


class MotorEspiao:
    def __init__(self):
        self.curadorias = []

    def pontuar_conversa(self, conversa, curadoria=None):
        return 50.0

    def atribuir_conversa(self, conversa, curadoria=None):
        self.curadorias.append(curadoria)
        return {"mensagens": [], "importancias": {}, "contribuicoes": None}

    def analisar_conversa(self, conversa, referencia=None, curadoria=None):
        self.curadorias.append(curadoria)
        return {"mensagens": [], "importancias": {}, "contribuicoes": None,
                "score": 50.0, "vocabulario": []}


def _montar(tmp_path):
    banco = Banco(tmp_path / "t.db")
    banco.migrar()
    motor = MotorEspiao()
    cliente = TestClient(criar_app(banco=banco, motor=motor, raiz_importacao=tmp_path))
    cliente.post("/lexico/curado",
                 json={"tipo": "palavra", "termo": "lentissimo", "peso": -1})
    return cliente, banco, motor


def test_atribuicao_recusa_explicar_score_de_regua_antiga(tmp_path):
    cliente, banco, motor = _montar(tmp_path)
    agora = datetime(2026, 8, 13, 10, tzinfo=timezone.utc)
    conversa = Conversa(id="c1", canal="csv", iniciada_em=agora, mensagens=[
        Mensagem(autor="cliente", texto="lentissimo", enviada_em=agora)])
    banco.salvar(conversa, 50.0, "detrator")

    resposta = cliente.get("/conversas/c1/atribuicao")
    assert resposta.status_code == 409
    assert "repontue" in resposta.json()["detail"]


def test_atribuicao_explica_com_a_mesma_curadoria_que_pontuou(tmp_path):
    cliente, banco, motor = _montar(tmp_path)
    agora = datetime(2026, 8, 13, 10, tzinfo=timezone.utc)
    conversa = Conversa(id="c1", canal="csv", iniciada_em=agora, mensagens=[
        Mensagem(autor="cliente", texto="lentissimo", enviada_em=agora)])
    banco.salvar(conversa, 50.0, "detrator", lexico_versao=banco.lexico_versao())

    assert cliente.get("/conversas/c1/atribuicao").status_code == 200
    assert motor.curadorias[-1].polaridade_de("lentissimo") == -1


def test_analisar_explica_com_a_curadoria_vigente(tmp_path):
    cliente, _, motor = _montar(tmp_path)
    assert cliente.post("/analisar", json={"csv": CSV}).status_code == 200
    assert motor.curadorias[-1].polaridade_de("lentissimo") == -1
