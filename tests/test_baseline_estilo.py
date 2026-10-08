import pytest

from fraus.baseline_estilo import (NOMES_TRACOS, TRACOS_BINARIOS, BaselineEstilo,
                                   tracos_de_superficie)
from fraus.comparacao_modelos import acuracia_por_par


def test_tracos_tem_nomes_fixos_e_nenhum_lexico():
    tracos = tracos_de_superficie("Ótimo serviço!!! kkkk https://x.y @loja #fail R$ 10...")
    assert tuple(tracos) == NOMES_TRACOS
    assert tracos["exclamacoes"] == 3.0
    assert tracos["risada"] == 1.0
    assert tracos["tem_url"] == tracos["tem_arroba"] == tracos["tem_hashtag"] == 1.0
    assert tracos["tem_reais"] == tracos["reticencias"] == 1.0
    assert set(TRACOS_BINARIOS) <= set(NOMES_TRACOS)


def test_emoji_e_acento_nao_quebram_os_tracos():
    tracos = tracos_de_superficie("ok, obrigado 🙂")
    assert tracos["tem_emoji"] == 1.0
    assert tracos["inicio_minusculo"] == 1.0
    assert tracos_de_superficie("ÉÉÉ")["prop_maiusculas"] == 1.0
    assert tracos_de_superficie("") == {nome: 0.0 for nome in NOMES_TRACOS}


def test_baseline_aprende_atalho_de_pontuacao():
    textos = [f"frase numero {i}." for i in range(30)] + [f"frase numero {i}" for i in range(30)]
    rotulos = [0] * 30 + [1] * 30
    modelo = BaselineEstilo().treinar(textos, rotulos)
    assert modelo.prever(["outra frase.", "outra frase"]) == [0, 1]


def test_baseline_nao_resolve_par_de_mesmo_registro():
    textos = [f"frase numero {i}." for i in range(30)] + [f"frase numero {i}" for i in range(30)]
    modelo = BaselineEstilo().treinar(textos, [0] * 30 + [1] * 30)
    # Os dois lados de cada par tem a mesma superficie: o baseline responde
    # igual para os dois, entao nunca acerta um par inteiro.
    regua = ["abc def", "ghi jkl", "mno pqr.", "stu vwx."]
    preditos = modelo.prever(regua)
    assert acuracia_por_par([0, 1, 0, 1], preditos, ["a", "a", "b", "b"]) == 0.0
