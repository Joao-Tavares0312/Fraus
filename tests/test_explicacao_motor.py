"""A explicacao viaja na atribuicao e bate com o score que o Motor da."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.db import Banco
from fraus.modelos import Conversa, Mensagem
from tests.test_motor import _motor

BASE = datetime(2026, 9, 4, 10, 0, 0, tzinfo=timezone.utc)


def _conversa(id_="c1", com_cliente=True):
    mensagens = [Mensagem(autor="bot", texto="ola", enviada_em=BASE)]
    if com_cliente:
        mensagens += [
            Mensagem(autor="cliente", texto="demorou demais", enviada_em=BASE + timedelta(seconds=5)),
            Mensagem(autor="bot", texto="desculpe", enviada_em=BASE + timedelta(seconds=65)),
        ]
    return Conversa(id=id_, canal="csv", iniciada_em=BASE, mensagens=mensagens)


def test_motor_anexa_explicacao_que_reproduz_o_score():
    motor = _motor()
    conversa = _conversa()
    explicacao = motor.atribuir_conversa(conversa)["explicacao"]
    assert explicacao["decomposicao"]["score"] == pytest.approx(motor.pontuar_conversa(conversa), abs=1e-9)
    assert set(explicacao["efeitos"]) == set(explicacao["familia_da_feature"].values())
    assert explicacao["frases"]


def test_sem_fala_do_cliente_explicacao_e_none():
    assert _motor().atribuir_conversa(_conversa(com_cliente=False))["explicacao"] is None


def test_rota_de_atribuicao_devolve_explicacao_sem_mudar_o_score(tmp_path):
    motor = _motor()
    banco = Banco(tmp_path / "f.db")
    banco.migrar()
    conversa = _conversa()
    score = motor.pontuar_conversa(conversa)
    banco.salvar_lote([(conversa, score, "neutro")], lexico_versao=0, regua=motor.regua())
    cliente = TestClient(criar_app(banco=banco, motor=motor))
    resposta = cliente.get("/conversas/c1/atribuicao")
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["explicacao"]["decomposicao"]["score"] == pytest.approx(corpo["score"], abs=1e-9)
    assert banco.buscar("c1")[1] == score


def test_fusor_sem_a_classe_satisfeito_falha_explicito_na_contribuicao_por_familia():
    from fraus.fusor import Fusor, montar_features
    from fraus.motor import Motor
    from tests.test_motor import _EmocaoDuble, _IroniaDuble, _TextoDuble

    texto, emocao = _TextoDuble(), _EmocaoDuble()
    conversa = _conversa()
    features = montar_features(conversa, texto, emocao)
    fusor = Fusor()
    fusor.treinar([features, {k: v + 1 for k, v in features.items()}] * 3, [0, 1] * 3)
    motor = Motor(texto, fusor, emocao, _IroniaDuble())
    with pytest.raises(RuntimeError, match="satisfeito"):
        motor.contribuicao_por_familia(conversa)
