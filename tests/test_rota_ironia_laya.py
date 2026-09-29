import pytest
from fastapi import HTTPException

from fraus.api.rotas import modelo


class ClassificadorFalso:
    def prever_configurado(self, texto, **opcoes):
        assert texto == "ótimo, caiu de novo"
        assert opcoes["contexto"] == "o sistema falhou"
        return 0.88


def test_rota_laya_retorna_somente_parametros_de_ironia(monkeypatch):
    import fraus.sinais.ironia_laya as modulo

    monkeypatch.setattr(
        modulo, "obter_classificador_ironia_laya_declarado", lambda: ClassificadorFalso()
    )
    from fraus.api.esquemas import PedidoSimulacaoIroniaLaya

    resposta = modelo.simular_ironia_laya(PedidoSimulacaoIroniaLaya(
        texto=" ótimo, caiu de novo ", contexto="o sistema falhou",
        instrucao="Há ironia?", criterio_ironico="contradição",
        criterio_literal="literal", limiar=0.7, confianca_minima=0.8,
    ))

    assert resposta["classe"] == "ironico"
    assert resposta["prob_nao_ironico"] == 0.12
    assert resposta["prob_ironia"] == 0.88
    assert resposta["checkpoint"] == "multilingual"
    assert resposta["pontua"] is False
    assert resposta["confianca"] == 0.88
    assert resposta["limiar"] == 0.7
    assert resposta["contexto_usado"] is True
    assert "prob_satisfeito" not in resposta
    assert "emocao" not in resposta


def test_rota_laya_recusa_texto_vazio():
    from fraus.api.esquemas import PedidoSimulacaoIroniaLaya

    with pytest.raises(HTTPException, match="texto vazio"):
        modelo.simular_ironia_laya(PedidoSimulacaoIroniaLaya(
            texto="  ", instrucao="Há ironia?",
            criterio_ironico="contradição", criterio_literal="literal",
        ))
