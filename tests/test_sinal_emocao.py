from datetime import datetime, timezone
from pathlib import Path

import pytest

from fraus.modelos import Conversa, Mensagem
from fraus.sinais.emocao import (NOMES_EMOCOES, ClassificadorEmocao,
                                 desprezo_derivado, features_emocao)
from fraus.sinais.texto import ModeloAusenteError

BASE = datetime(2026, 8, 13, 10, 0, 0, tzinfo=timezone.utc)


class ClassificadorFalso:
    """Dubla o modelo real. Ordem: alegria, tristeza, raiva, medo, nojo, surpresa, neutro."""

    TABELA = {
        "que alegria": [0.9, 0.02, 0.02, 0.02, 0.01, 0.02, 0.01],
        "que raiva": [0.01, 0.02, 0.9, 0.02, 0.02, 0.02, 0.01],
        "que nojo": [0.01, 0.02, 0.02, 0.02, 0.9, 0.02, 0.01],
        "desprezo": [0.01, 0.02, 0.45, 0.02, 0.45, 0.03, 0.02],
    }
    NEUTRA = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]

    def prever_mensagens(self, textos: list[str]) -> list[list[float]]:
        return [self.TABELA.get(t, self.NEUTRA) for t in textos]


def _conversa(textos: list[str], autor: str = "cliente") -> Conversa:
    return Conversa(
        id="c1",
        canal="csv",
        iniciada_em=BASE,
        mensagens=[Mensagem(autor=autor, texto=t, enviada_em=BASE) for t in textos],
    )


def test_modelo_de_emocao_ausente_falha_alto():
    """Invariante 7: sem modelo nao ha predicao, e isso e falha explicita."""
    with pytest.raises(ModeloAusenteError):
        ClassificadorEmocao(Path("modelos/nao-existe-emocao"))


def test_as_sete_classes_viram_feature_mais_o_desprezo():
    features = features_emocao(_conversa(["que alegria"]), ClassificadorFalso())
    assert set(features) == {f"emocao_{nome}_media" for nome in NOMES_EMOCOES} | {
        "emocao_desprezo_derivado"
    }
    assert len(features) == 8


def test_a_ordem_das_classes_e_respeitada():
    """Trocar a ordem nao gera erro, so atribui a emocao errada em silencio."""
    features = features_emocao(_conversa(["que raiva"]), ClassificadorFalso())
    assert features["emocao_raiva_media"] == pytest.approx(0.9)
    assert features["emocao_alegria_media"] == pytest.approx(0.01)


def test_media_das_falas_do_cliente():
    features = features_emocao(_conversa(["que alegria", "que raiva"]), ClassificadorFalso())
    assert features["emocao_alegria_media"] == pytest.approx(0.455)  # (0.9 + 0.01) / 2
    assert features["emocao_raiva_media"] == pytest.approx(0.46)  # (0.02 + 0.9) / 2


def test_fala_do_bot_nao_entra_na_emocao_do_cliente():
    features = features_emocao(_conversa(["que raiva"], autor="bot"), ClassificadorFalso())
    assert features["emocao_raiva_media"] == 0.0


def test_desprezo_exige_raiva_e_nojo_juntos():
    """Diade primaria de Plutchik: raiva pura nao e desprezo."""
    assert desprezo_derivado(0.9, 0.9) == pytest.approx(0.9)
    assert desprezo_derivado(0.9, 0.0) == pytest.approx(0.0)
    assert desprezo_derivado(0.0, 0.9) == pytest.approx(0.0)


def test_desprezo_da_media_geometrica_e_nao_da_aritmetica():
    """A aritmetica daria 0.45 para raiva pura -- meio desprezo sem nojo nenhum."""
    assert desprezo_derivado(0.9, 0.0) < 0.45


def test_desprezo_sobe_quando_raiva_e_nojo_sobem_juntos():
    conversa = _conversa(["desprezo"])
    features = features_emocao(conversa, ClassificadorFalso())
    assert features["emocao_desprezo_derivado"] == pytest.approx(0.45)
    # Mais alto que numa conversa de raiva pura, que tem raiva MAIOR (0.9).
    so_raiva = features_emocao(_conversa(["que raiva"]), ClassificadorFalso())
    assert features["emocao_desprezo_derivado"] > so_raiva["emocao_desprezo_derivado"]


def test_conversa_sem_fala_do_cliente_zera_as_oito_features():
    features = features_emocao(_conversa(["ola"], autor="bot"), ClassificadorFalso())
    assert len(features) == 8
    assert all(valor == 0.0 for valor in features.values())
