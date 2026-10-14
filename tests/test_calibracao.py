import pytest

from fraus.calibracao import bootstrap, ece, ece_por_classe, faixas, mce


def test_perfeitamente_calibrado_tem_ece_zero():
    # confianca 1.0 e sempre acerta
    probs = [[1.0, 0.0, 0.0]] * 10 + [[0.0, 0.0, 1.0]] * 10
    rotulos = [0] * 10 + [2] * 10
    assert ece(probs, rotulos) == pytest.approx(0.0)


def test_superconfiante_mede_a_distancia():
    # confianca 0.9, acerta metade -> ECE = |0.9 - 0.5| = 0.4 (uma faixa so)
    probs = [[0.9, 0.05, 0.05]] * 10
    rotulos = [0] * 5 + [1] * 5
    assert ece(probs, rotulos) == pytest.approx(0.4)
    assert mce(probs, rotulos) == pytest.approx(0.4)


def test_faixa_vazia_e_none_e_nao_zero():
    f = faixas([[0.95, 0.05, 0.0]], [0], n_faixas=10)
    vazias = [x for x in f if x["n"] == 0]
    assert vazias and all(x["acuracia"] is None and x["confianca_media"] is None for x in vazias)


def test_ece_por_classe_tem_as_tres_classes():
    probs = [[0.7, 0.2, 0.1], [0.1, 0.8, 0.1], [0.2, 0.2, 0.6]]
    assert set(ece_por_classe(probs, [0, 1, 2])) == {0, 1, 2}


def test_bootstrap_reprodutivel_e_contem_o_ponto():
    probs = [[0.9, 0.05, 0.05]] * 20 + [[0.6, 0.3, 0.1]] * 20
    rotulos = [0] * 15 + [1] * 5 + [0] * 12 + [2] * 8
    a = bootstrap(ece, probs, rotulos)
    assert a == bootstrap(ece, probs, rotulos)
    assert a[0] <= ece(probs, rotulos) <= a[1]
