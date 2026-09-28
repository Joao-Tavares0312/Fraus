import pytest
from fastapi import HTTPException

from fraus.api.esquemas import PedidoSimulacao
from fraus.api.rotas import modelo


class ClassificadorFalso:
    def prever_mensagens(self, textos):
        assert textos == ["ótimo, caiu de novo"]
        return [[0.12, 0.88]]


def test_rota_laya_retorna_somente_parametros_de_ironia(monkeypatch):
    import fraus.sinais.ironia_laya as modulo

    monkeypatch.setattr(modulo, "obter_classificador_ironia_laya", lambda: ClassificadorFalso())
    resposta = modelo.simular_ironia_laya(PedidoSimulacao(texto=" ótimo, caiu de novo "))

    assert resposta["classe"] == "ironico"
    assert resposta["prob_nao_ironico"] == 0.12
    assert resposta["prob_ironia"] == 0.88
    assert resposta["checkpoint"] == "multilingual"
    assert resposta["pontua"] is False
    assert "prob_satisfeito" not in resposta
    assert "emocao" not in resposta


def test_rota_laya_recusa_texto_vazio():
    with pytest.raises(HTTPException, match="texto vazio"):
        modelo.simular_ironia_laya(PedidoSimulacao(texto="  "))
