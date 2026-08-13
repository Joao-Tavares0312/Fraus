from datetime import datetime, timezone
from pathlib import Path

import pytest

from dolos.modelos import Conversa, Mensagem
from dolos.sinais.texto import ClassificadorTexto, ModeloAusenteError, features_texto

BASE = datetime(2026, 8, 13, 10, 0, 0, tzinfo=timezone.utc)


class ClassificadorFalso:
    """Dubla o modelo real: mapeia texto conhecido para probabilidade fixa."""

    TABELA = {
        "pessimo": [0.9, 0.05, 0.05],
        "ok": [0.2, 0.6, 0.2],
        "otimo": [0.05, 0.05, 0.9],
    }

    def prever_mensagens(self, textos: list[str]) -> list[list[float]]:
        return [self.TABELA.get(t, [0.34, 0.33, 0.33]) for t in textos]


def _conversa(textos: list[str]) -> Conversa:
    return Conversa(
        id="c1",
        canal="csv",
        iniciada_em=BASE,
        mensagens=[Mensagem(autor="cliente", texto=t, enviada_em=BASE) for t in textos],
    )


def test_modelo_ausente_falha_alto():
    with pytest.raises(ModeloAusenteError):
        ClassificadorTexto(Path("modelos/nao-existe"))


def test_media_das_probabilidades_das_mensagens_do_cliente():
    features = features_texto(_conversa(["pessimo", "otimo"]), ClassificadorFalso())
    assert features["texto_prob_insatisfeito_media"] == pytest.approx(0.475)
    assert features["texto_prob_satisfeito_media"] == pytest.approx(0.475)


def test_max_captura_o_pior_momento_da_conversa():
    features = features_texto(_conversa(["ok", "pessimo", "ok"]), ClassificadorFalso())
    assert features["texto_prob_insatisfeito_max"] == pytest.approx(0.9)


def test_ultima_fala_do_cliente_e_isolada():
    features = features_texto(_conversa(["pessimo", "otimo"]), ClassificadorFalso())
    assert features["texto_prob_satisfeito_ultima"] == pytest.approx(0.9)


def test_conversa_sem_fala_do_cliente_zera_as_features():
    conversa = Conversa(
        id="c1",
        canal="csv",
        iniciada_em=BASE,
        mensagens=[Mensagem(autor="bot", texto="otimo", enviada_em=BASE)],
    )
    features = features_texto(conversa, ClassificadorFalso())
    assert features["texto_prob_satisfeito_media"] == 0.0
    assert features["texto_prob_insatisfeito_max"] == 0.0
