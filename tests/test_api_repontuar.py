"""A regua misturada deixa de ser silenciosa."""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco
from fraus.modelos import Conversa, Mensagem


class MotorFalso:
    def pontuar_conversa(self, conversa, curadoria=None):
        return 50.0


def _cliente(tmp_path):
    banco = Banco(tmp_path / "t.db")
    banco.migrar()
    app = criar_app(banco=banco, motor=MotorFalso(), raiz_importacao=tmp_path)
    return TestClient(app), banco


def _conversa(id_):
    quando = datetime(2026, 8, 25, 10, 0, tzinfo=timezone.utc)
    return Conversa(
        id=id_, canal="csv", iniciada_em=quando,
        mensagens=[Mensagem(autor="cliente", texto="oi", enviada_em=quando)],
    )


def test_banco_sem_curadoria_nao_tem_nada_defasado(tmp_path):
    cliente, banco = _cliente(tmp_path)
    banco.salvar(_conversa("c1"), 50.0, "neutro", lexico_versao=0)
    corpo = cliente.get("/indicadores").json()
    assert corpo["pontuadas_com_lexico_antigo"] == 0
    assert corpo["total_no_banco"] == 1


def test_curar_deixa_o_que_ja_existia_defasado(tmp_path):
    cliente, banco = _cliente(tmp_path)
    banco.salvar(_conversa("c1"), 50.0, "neutro", lexico_versao=0)
    cliente.post("/lexico/curado", json={"tipo": "palavra", "termo": "x", "peso": -1})
    assert cliente.get("/indicadores").json()["pontuadas_com_lexico_antigo"] == 1


def test_a_contagem_ignora_o_recorte_de_periodo(tmp_path):
    """A regua misturada e propriedade do BANCO, nao da semana que se olha. Um
    aviso que sumisse ao filtrar esconderia o problema de quem estivesse
    justamente investigando um numero estranho."""
    cliente, banco = _cliente(tmp_path)
    banco.salvar(_conversa("c1"), 50.0, "neutro", lexico_versao=0)
    cliente.post("/lexico/curado", json={"tipo": "palavra", "termo": "x", "peso": -1})
    corpo = cliente.get("/indicadores?de=2020-01-01&ate=2020-12-31").json()
    assert corpo["pontuadas_com_lexico_antigo"] == 1
    assert corpo["total_no_banco"] == 1


def test_repontuar_poe_tudo_na_versao_vigente(tmp_path):
    cliente, banco = _cliente(tmp_path)
    banco.salvar(_conversa("c1"), 50.0, "neutro", lexico_versao=0)
    banco.salvar(_conversa("c2"), 50.0, "neutro", lexico_versao=0)
    cliente.post("/lexico/curado", json={"tipo": "palavra", "termo": "x", "peso": -1})

    resposta = cliente.post("/conversas/repontuar")
    assert resposta.status_code == 200
    assert resposta.json()["repontuadas"] == 2
    assert cliente.get("/indicadores").json()["pontuadas_com_lexico_antigo"] == 0


def test_repontuar_com_banco_vazio_nao_quebra(tmp_path):
    cliente, _ = _cliente(tmp_path)
    assert cliente.post("/conversas/repontuar").json()["repontuadas"] == 0
