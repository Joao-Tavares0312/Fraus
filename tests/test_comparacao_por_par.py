import numpy as np
import pytest

from fraus.comparacao_modelos import acuracia_por_par, avaliar_conjunto, bootstrap_por_par, ece


def test_par_so_conta_quando_os_dois_lados_acertam():
    rotulos = [0, 1, 0, 1]
    preditos = [0, 1, 0, 0]
    assert acuracia_por_par(rotulos, preditos, ["a", "a", "b", "b"]) == pytest.approx(0.5)


def test_par_incompleto_e_recusado():
    with pytest.raises(ValueError, match="um lado de cada rotulo"):
        acuracia_por_par([0, 1, 0], [0, 1, 0], ["a", "a", "b"])
    with pytest.raises(ValueError, match="um lado de cada rotulo"):
        acuracia_por_par([0, 0], [0, 0], ["a", "a"])


def test_classificador_aleatorio_fica_perto_de_um_quarto():
    gerador = np.random.default_rng(0)
    pares = [f"p{i}" for i in range(5000) for _ in range(2)]
    rotulos = [0, 1] * 5000
    preditos = gerador.integers(0, 2, 10000).tolist()
    assert acuracia_por_par(rotulos, preditos, pares) == pytest.approx(0.25, abs=0.02)


def test_bootstrap_por_par_e_deterministico_e_degenera_sem_quebrar():
    rotulos, pares = [0, 1] * 4, [p for p in "abcd" for _ in range(2)]
    perfeito = bootstrap_por_par(rotulos, rotulos, pares)
    assert (perfeito.valor, perfeito.ic_inferior, perfeito.ic_superior) == (1.0, 1.0, 1.0)
    metade = [0, 1, 0, 1, 1, 1, 1, 1]
    um = bootstrap_por_par(rotulos, metade, pares, semente=7)
    dois = bootstrap_por_par(rotulos, metade, pares, semente=7)
    assert um == dois
    assert um.valor == pytest.approx(0.5)


def test_bootstrap_da_diferenca_por_par():
    rotulos, pares = [0, 1] * 20, [f"p{i}" for i in range(20) for _ in range(2)]
    metade = [0, 1] * 10 + [1, 1] * 10
    resultado = bootstrap_por_par(rotulos, rotulos, pares, preditos_referencia=metade)
    assert resultado.valor == pytest.approx(0.5)
    assert 0.0 < resultado.ic_inferior <= 0.5 <= resultado.ic_superior <= 1.0


def test_ece_zero_quando_calibrado_e_positivo_quando_superconfiante():
    assert ece([0.8] * 10, [1] * 8 + [0] * 2) == pytest.approx(0.0)
    assert ece([1.0] * 10, [1] * 5 + [0] * 5) == pytest.approx(0.5)
    with pytest.raises(ValueError, match="0..1"):
        ece([1.2], [1])


def _conjunto(par_ids=None):
    rotulos = [0, 1] * 20
    return avaliar_conjunto(
        identificador="regua_pares", tarefa="ironia", nome="Régua de pares",
        independente=True, rotulos=rotulos,
        preditos_por_modelo={"laya_treinado": rotulos, "bertimbau": [1, 1] * 20},
        classes=[0, 1], nomes_classes=["não irônico", "irônico"],
        par_ids=par_ids, reamostras=200,
    )


def test_conjunto_com_pares_traz_acuracia_por_par_e_comparacao():
    resultado = _conjunto([f"p{i}" for i in range(20) for _ in range(2)])
    assert resultado["modelos"]["laya_treinado"]["acuracia_por_par"] == 1.0
    assert resultado["modelos"]["bertimbau"]["acuracia_por_par"] == 0.0
    assert resultado["comparacao"]["diferenca_acuracia_por_par"] == 1.0
    assert resultado["comparacao"]["por_par_demonstrada"] is True


def test_conjunto_sem_pares_nao_muda():
    resultado = _conjunto()
    assert "acuracia_por_par" not in resultado["modelos"]["laya_treinado"]
    assert "diferenca_acuracia_por_par" not in resultado["comparacao"]
