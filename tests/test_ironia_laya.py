import sys

import pytest

from fraus.sinais.ironia_laya import (
    ClassificadorIroniaLaya,
    DependenciaLayaAusenteError,
    PERGUNTA_IRONIA,
    RespostaLayaInvalidaError,
)


class RouterFalso:
    def __init__(self, probabilidades):
        self.probabilidades = probabilidades
        self.requisicoes = None
        self.ordenou = None

    def predict_batch(self, requisicoes, sort_by_length=False):
        self.requisicoes = requisicoes
        self.ordenou = sort_by_length
        return [
            {"answers": {"ironia": {"probabilities": {"A": p, "B": 1 - p}}}}
            for p in self.probabilidades
        ]

    def predict(self, estado, perguntas, **opcoes):
        self.estado = estado
        self.perguntas = perguntas
        self.opcoes = opcoes
        p = self.probabilidades[0]
        return {"answers": {"ironia": {"probabilities": {"A": p, "B": 1 - p}}}}


def test_adapta_probabilidade_para_contrato_binario_e_forca_portugues():
    router = RouterFalso([0.8, 0.15])
    classificador = ClassificadorIroniaLaya(router=router)

    assert classificador.prever_mensagens(["ótimo, caiu de novo", "obrigado"]) == [
        [pytest.approx(0.2), 0.8],
        [0.85, 0.15],
    ]
    assert router.ordenou is True
    assert all(item["model"] == "multilingual" for item in router.requisicoes)
    assert all(item["lang"] == "pt" for item in router.requisicoes)
    assert all(item["questions"] == PERGUNTA_IRONIA for item in router.requisicoes)


def test_lista_vazia_nao_chama_modelo():
    router = RouterFalso([])
    assert ClassificadorIroniaLaya(router=router).prever_mensagens([]) == []
    assert router.requisicoes is None


def test_previsao_configurada_envia_contexto_e_criterios():
    router = RouterFalso([0.73])
    classificador = ClassificadorIroniaLaya(router=router)
    probabilidade = classificador.prever_configurado(
        "excelente, caiu de novo",
        contexto="o sistema falhou três vezes",
        instrucao="Decida se existe ironia.",
        criterio_ironico="sentido literal contradiz os fatos",
        criterio_literal="sentido literal concorda com os fatos",
    )
    assert probabilidade == 0.73
    assert router.estado == {
        "contexto_anterior": "o sistema falhou três vezes",
        "fala_do_cliente": "excelente, caiu de novo",
    }
    assert router.perguntas["ironia"]["criteria"]["A"] == "sentido literal contradiz os fatos"
    assert router.opcoes == {"model": "multilingual", "lang": "pt"}


@pytest.mark.parametrize("resultado", [
    {},
    {"answers": {"ironia": {"probabilities": {"A": 1.2}}}},
])
def test_resposta_invalida_falha_alto(resultado):
    class Router:
        def predict_batch(self, *_args, **_kwargs):
            return [resultado]

    with pytest.raises(RespostaLayaInvalidaError):
        ClassificadorIroniaLaya(router=Router()).prever_mensagens(["texto"])


def test_dependencia_ausente_da_mensagem_acionavel(monkeypatch):
    monkeypatch.setitem(sys.modules, "laya", None)
    with pytest.raises(DependenciaLayaAusenteError, match="extra laya"):
        ClassificadorIroniaLaya()
