"""A curadoria e um DICIONARIO BURRO, e e de proposito.

Ela nao normaliza, nao valida escala e nao sabe o que e acento. Quem normaliza e
quem escreve (a rota) e quem consulta (o lexico, que ja calcula `sem_acento`
para o proprio indice de reserva). Ensinar normalizacao a este objeto criaria
uma segunda regra de normalizacao no projeto, e duas regras divergem.
"""

import dataclasses

import pytest

from fraus.sinais.curadoria import CURADORIA_VAZIA, Curadoria


def test_vazia_nao_conhece_nada():
    assert CURADORIA_VAZIA.polaridade_de("lentissimo") is None
    assert CURADORIA_VAZIA.score_de("🙄") is None
    assert CURADORIA_VAZIA.versao == 0


def test_palavra_curada_responde_a_polaridade():
    c = Curadoria(palavras={"lentissimo": -1}, emojis={}, versao=3)
    assert c.polaridade_de("lentissimo") == -1
    assert c.versao == 3


def test_termo_nao_curado_devolve_None_e_nao_zero():
    # None e "nao curado" -- o lexico base decide. Zero seria "curado como
    # neutro", que e uma afirmacao diferente e silencia o termo.
    c = Curadoria(palavras={"lentissimo": -1}, emojis={}, versao=1)
    assert c.polaridade_de("otimo") is None


def test_palavra_curada_como_zero_e_diferente_de_ausente():
    c = Curadoria(palavras={"cobranca": 0}, emojis={}, versao=1)
    assert c.polaridade_de("cobranca") == 0


def test_emoji_curado_responde_ao_score():
    c = Curadoria(palavras={}, emojis={"🙄": -0.62}, versao=1)
    assert c.score_de("🙄") == -0.62
    assert c.score_de("🎉") is None


def test_contagens_para_a_ficha_do_modelo():
    c = Curadoria(palavras={"a": 1, "b": -1}, emojis={"🙄": -0.5}, versao=7)
    assert c.total_de_palavras() == 2
    assert c.total_de_emojis() == 1


def test_e_imutavel():
    c = Curadoria(palavras={}, emojis={}, versao=0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        c.versao = 9
