import pytest

from fraus.comparacao_modelos import bootstrap_da_diferenca, f1_macro, mcnemar_exato


def test_f1_macro_trata_classe_ausente_como_zero():
    rotulos = [0, 0, 1, 1, 2, 2]
    preditos = [0, 0, 1, 1, 1, 1]
    # classes 0 e 1: F1 1,0 e 0,667; classe 2 nunca prevista: 0.
    assert f1_macro(rotulos, preditos, classes=[0, 1, 2]) == pytest.approx((1.0 + 2 / 3 + 0.0) / 3)


def test_mcnemar_conta_so_os_discordantes():
    acertos_a = [True] * 10 + [True] * 8 + [False] * 1 + [False] * 5
    acertos_b = [True] * 10 + [False] * 8 + [True] * 1 + [False] * 5
    resultado = mcnemar_exato(acertos_a, acertos_b)
    assert (resultado.so_a, resultado.so_b) == (8, 1)
    # binomial exato bilateral com n=9: 2 * (C(9,0) + C(9,1)) / 2^9
    assert resultado.p_valor == pytest.approx(2 * 10 / 512)


def test_mcnemar_sem_discordancia_nao_e_evidencia():
    resultado = mcnemar_exato([True, False], [True, False])
    assert resultado.p_valor == 1.0


def test_mcnemar_recusa_listas_desalinhadas():
    with pytest.raises(ValueError):
        mcnemar_exato([True], [True, False])


def test_bootstrap_e_deterministico_e_cobre_a_diferenca_observada():
    rotulos = [0, 1] * 50
    bom = list(rotulos)
    ruim = [0] * 100
    a = bootstrap_da_diferenca(rotulos, bom, ruim, classes=[0, 1], reamostras=200, semente=7)
    b = bootstrap_da_diferenca(rotulos, bom, ruim, classes=[0, 1], reamostras=200, semente=7)
    assert a == b
    assert a.diferenca == pytest.approx(1.0 - (2 / 3) / 2)
    assert a.ic_inferior <= a.diferenca <= a.ic_superior
    assert a.ic_inferior > 0  # o modelo bom ganha em qualquer reamostra


def test_bootstrap_de_modelos_iguais_cruza_o_zero():
    rotulos = [0, 1, 1, 0] * 10
    preditos = [0, 1, 0, 0] * 10
    resultado = bootstrap_da_diferenca(rotulos, preditos, preditos, classes=[0, 1], reamostras=100)
    assert resultado.diferenca == 0.0
    assert resultado.ic_inferior == resultado.ic_superior == 0.0
