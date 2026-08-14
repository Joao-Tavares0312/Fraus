from datetime import datetime, timezone
from pathlib import Path

import pytest

from fraus.modelos import Conversa, Mensagem
from fraus.sinais.ironia import ClassificadorIronia, features_ironia
from fraus.sinais.texto import ModeloAusenteError

BASE = datetime(2026, 8, 13, 10, 0, 0, tzinfo=timezone.utc)


class ClassificadorFalso:
    """Dubla o modelo real. Ordem: [nao_ironico, ironico]."""

    TABELA = {
        "otimo servico, so esperei 3 horas": [0.1, 0.9],
        "qual o prazo de entrega": [0.95, 0.05],
    }

    def prever_mensagens(self, textos: list[str]) -> list[list[float]]:
        return [self.TABELA.get(t, [0.5, 0.5]) for t in textos]


def _conversa(textos: list[str], autor: str = "cliente") -> Conversa:
    return Conversa(
        id="c1",
        canal="csv",
        iniciada_em=BASE,
        mensagens=[Mensagem(autor=autor, texto=t, enviada_em=BASE) for t in textos],
    )


def test_modelo_de_ironia_ausente_falha_alto():
    with pytest.raises(ModeloAusenteError):
        ClassificadorIronia(Path("modelos/nao-existe-ironia"))


def test_ironia_alta_na_frase_ironica():
    features = features_ironia(
        _conversa(["otimo servico, so esperei 3 horas"]), ClassificadorFalso()
    )
    assert features["ironia_prob_media"] == pytest.approx(0.9)
    assert features["ironia_prob_max"] == pytest.approx(0.9)


def test_ironia_baixa_na_pergunta_neutra():
    features = features_ironia(_conversa(["qual o prazo de entrega"]), ClassificadorFalso())
    assert features["ironia_prob_media"] == pytest.approx(0.05)


def test_max_nao_deixa_a_media_diluir_uma_frase_ironica():
    """Uma ironia no fim reverte a conversa; a media sozinha esconderia isso."""
    features = features_ironia(
        _conversa([
            "qual o prazo de entrega",
            "qual o prazo de entrega",
            "otimo servico, so esperei 3 horas",
        ]),
        ClassificadorFalso(),
    )
    assert features["ironia_prob_max"] == pytest.approx(0.9)
    assert features["ironia_prob_media"] < 0.4


def test_fala_do_bot_nao_conta_como_ironia_do_cliente():
    features = features_ironia(
        _conversa(["otimo servico, so esperei 3 horas"], autor="bot"), ClassificadorFalso()
    )
    assert features == {"ironia_prob_media": 0.0, "ironia_prob_max": 0.0}
