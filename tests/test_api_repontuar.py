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


def _aguardar(cliente, limite_s=10.0):
    """Consulta o progresso ate o trabalho sair de `rodando`."""
    import time

    fim = time.monotonic() + limite_s
    while time.monotonic() < fim:
        estado = cliente.get("/conversas/repontuar").json()
        if estado["estado"] != "rodando":
            return estado
        time.sleep(0.02)
    raise AssertionError("repontuacao nao terminou no prazo")


def test_repontuar_responde_ja_e_roda_em_segundo_plano(tmp_path):
    """202 com o total: a requisicao nao espera os tres BERTimbau por conversa.

    Sincrona, a rota prendia uma requisicao HTTP pelo banco inteiro, e um proxy
    que desistisse deixava o banco metade numa regua, metade noutra.
    """
    cliente, banco = _cliente(tmp_path)
    banco.salvar(_conversa("c1"), 50.0, "neutro", lexico_versao=0)
    banco.salvar(_conversa("c2"), 50.0, "neutro", lexico_versao=0)
    cliente.post("/lexico/curado", json={"tipo": "palavra", "termo": "x", "peso": -1})

    resposta = cliente.post("/conversas/repontuar")
    assert resposta.status_code == 202
    assert resposta.json()["total"] == 2

    final = _aguardar(cliente)
    assert final["estado"] == "concluido"
    assert final["feitas"] == 2
    assert cliente.get("/indicadores").json()["pontuadas_com_lexico_antigo"] == 0


def test_repontuar_com_banco_vazio_nao_quebra(tmp_path):
    cliente, _ = _cliente(tmp_path)
    assert cliente.post("/conversas/repontuar").status_code == 202
    assert _aguardar(cliente) | {"iniciado_em": None, "concluido_em": None} == {
        "estado": "concluido", "total": 0, "feitas": 0, "erro": None,
        "iniciado_em": None, "concluido_em": None,
    }


def test_sem_repontuacao_nenhuma_o_progresso_e_404(tmp_path):
    cliente, _ = _cliente(tmp_path)
    assert cliente.get("/conversas/repontuar").status_code == 404


def test_segunda_repontuacao_com_a_primeira_rodando_e_409(tmp_path):
    """Duas ao mesmo tempo gravariam o mesmo banco com duas curadorias."""
    import threading

    liberar = threading.Event()

    class MotorLento:
        def pontuar_conversa(self, conversa, curadoria=None):
            liberar.wait(5)
            return 50.0

    banco = Banco(tmp_path / "t.db")
    banco.migrar()
    banco.salvar(_conversa("c1"), 50.0, "neutro", lexico_versao=0)
    cliente = TestClient(criar_app(banco=banco, motor=MotorLento(), raiz_importacao=tmp_path))

    assert cliente.post("/conversas/repontuar").status_code == 202
    segunda = cliente.post("/conversas/repontuar")
    assert segunda.status_code == 409
    assert cliente.get("/conversas/repontuar").json()["estado"] == "rodando"
    liberar.set()
    assert _aguardar(cliente)["estado"] == "concluido"


def test_falha_no_meio_fica_registrada_e_nao_some(tmp_path):
    """O que ja foi gravado fica; o estado diz onde parou e por que."""

    class MotorQuebra:
        def pontuar_conversa(self, conversa, curadoria=None):
            if conversa.id == "c2":
                raise RuntimeError("modelo caiu")
            return 50.0

    banco = Banco(tmp_path / "t.db")
    banco.migrar()
    banco.salvar(_conversa("c1"), 50.0, "neutro", lexico_versao=0)
    banco.salvar(_conversa("c2"), 50.0, "neutro", lexico_versao=0)
    cliente = TestClient(criar_app(banco=banco, motor=MotorQuebra(), raiz_importacao=tmp_path))
    cliente.post("/conversas/repontuar")
    final = _aguardar(cliente)
    assert final["estado"] == "falhou"
    assert final["feitas"] == 1
    assert "modelo caiu" in final["erro"]
