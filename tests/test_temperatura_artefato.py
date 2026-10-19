"""A temperatura gravada pela receita de treino, lida pelos dois backends.

Artefato sem `fraus_receita.json` (todos os de antes de 19/10/2026) le T=1:
o softmax de sempre, nenhuma probabilidade muda. Arquivo presente com valor
invalido e falha alta (invariante 7), nunca um T=1 silencioso.
"""

import json

import numpy as np
import pytest

from fraus.sinais.onnx import SessaoOnnx, _softmax
from fraus.sinais.texto import ModeloAusenteError, temperatura_do_artefato


def test_sem_arquivo_a_temperatura_e_um(tmp_path):
    assert temperatura_do_artefato(tmp_path) == 1.0


def test_le_a_temperatura_gravada(tmp_path):
    (tmp_path / "fraus_receita.json").write_text(json.dumps({"temperatura": 1.7}))
    assert temperatura_do_artefato(tmp_path) == pytest.approx(1.7)


@pytest.mark.parametrize("conteudo", ['{"temperatura": 0}', '{"temperatura": -1}',
                                      '{"temperatura": "x"}', '{}', "nao e json"])
def test_temperatura_invalida_falha_alto(tmp_path, conteudo):
    (tmp_path / "fraus_receita.json").write_text(conteudo)
    with pytest.raises(ModeloAusenteError):
        temperatura_do_artefato(tmp_path)


def test_softmax_com_temperatura_achata_sem_trocar_a_ordem():
    logits = np.array([[3.0, 1.0, 2.0]], dtype=np.float32)
    frio, quente = _softmax(logits)[0], _softmax(logits, temperatura=2.0)[0]
    assert quente.max() < frio.max()
    assert list(np.argsort(quente)) == list(np.argsort(frio))


def test_sessao_onnx_aplica_a_temperatura_do_diretorio():
    sessao = SessaoOnnx.__new__(SessaoOnnx)
    sessao._tokenizador = lambda *a, **k: {"input_ids": np.array([[1, 2]]),
                                           "attention_mask": np.array([[1, 1]])}
    sessao._entradas = {"input_ids", "attention_mask"}

    class _Grafo:
        def run(self, saidas, entradas):
            return [np.array([[2.0, 0.0]], dtype=np.float32)]

    sessao._sessao = _Grafo()
    sessao._temperatura = 1.0
    (frio,) = sessao.prever(["x"])
    sessao._temperatura = 4.0
    (quente,) = sessao.prever(["x"])
    assert quente[0] < frio[0]
