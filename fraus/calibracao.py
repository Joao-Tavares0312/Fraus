"""Medição de calibração de probabilidade: ECE, MCE, por classe e bootstrap.

Implementa estimadores de calibração conforme Guo et al. (2017) para ECE e
Kull et al. (2019) para classwise-ECE. Bootstrap com numpy para intervalos
de confiança de 95%.
"""

from typing import Callable

import numpy as np


def faixas(
    probs: list[list[float]], rotulos: list[int], n_faixas: int = 10
) -> list[dict]:
    """Particiona predições em faixas de confiança e calcula acurácia por faixa.

    Cria `n_faixas` bins de largura igual em [0, 1], sendo o último bin
    incluindo 1.0. Para cada faixa não vazia, calcula a confiança média
    (máximo da distribuição por amostra) e a acurácia (proporção de acertos).
    Faixas vazias têm n=0 e confianca_media/acuracia como None.

    Args:
        probs: lista de distribuições de probabilidade, uma por amostra.
        rotulos: lista de rótulos verdadeiros (inteiros).
        n_faixas: número de bins (padrão: 10).

    Returns:
        Lista de dicts, cada um com chaves:
        - "inferior": limite inferior do intervalo [0, 1).
        - "superior": limite superior do intervalo (0, 1].
        - "n": quantidade de amostras nesta faixa.
        - "confianca_media": confiança média (max prob) ou None se n=0.
        - "acuracia": proporção de acertos ou None se n=0.
    """
    probs = np.array(probs)
    rotulos = np.array(rotulos)

    # Confiança máxima por amostra (maior probabilidade)
    max_probs = np.max(probs, axis=1)

    # Predições: classe com maior probabilidade
    predicoes = np.argmax(probs, axis=1)

    # Acertos: predição == rótulo
    acertos = predicoes == rotulos

    # Limites dos bins: largura igual em [0, 1]
    bins = np.linspace(0, 1, n_faixas + 1)
    resultado = []

    for i in range(n_faixas):
        inferior = bins[i]
        superior = bins[i + 1]

        # Última faixa inclui 1.0; outras não incluem o limite superior
        if i == n_faixas - 1:
            mascara = (max_probs >= inferior) & (max_probs <= superior)
        else:
            mascara = (max_probs >= inferior) & (max_probs < superior)

        n = np.sum(mascara)

        if n > 0:
            confianca_media = float(np.mean(max_probs[mascara]))
            acuracia = float(np.mean(acertos[mascara]))
        else:
            confianca_media = None
            acuracia = None

        resultado.append(
            {
                "inferior": float(inferior),
                "superior": float(superior),
                "n": int(n),
                "confianca_media": confianca_media,
                "acuracia": acuracia,
            }
        )

    return resultado


def ece(probs: list[list[float]], rotulos: list[int], n_faixas: int = 10) -> float:
    """Erro Esperado de Calibração (ECE) sobre confiança máxima.

    Implementa ECE conforme Guo et al. (2017):
    ECE = Σ (n_b / N) |acc_b − conf_b|

    onde a soma é feita apenas sobre faixas não vazias.

    Args:
        probs: lista de distribuições de probabilidade.
        rotulos: lista de rótulos verdadeiros.
        n_faixas: número de bins (padrão: 10).

    Returns:
        ECE como float em [0, 1].
    """
    f = faixas(probs, rotulos, n_faixas)
    N = len(rotulos)

    ece_valor = 0.0
    for faixa in f:
        if faixa["n"] > 0:
            n_b = faixa["n"]
            acc_b = faixa["acuracia"]
            conf_b = faixa["confianca_media"]
            ece_valor += (n_b / N) * abs(acc_b - conf_b)

    return float(ece_valor)


def mce(probs: list[list[float]], rotulos: list[int], n_faixas: int = 10) -> float:
    """Erro Máximo de Calibração (MCE) sobre confiança máxima.

    MCE = max_b |acc_b − conf_b|, calculado apenas sobre faixas não vazias.

    Args:
        probs: lista de distribuições de probabilidade.
        rotulos: lista de rótulos verdadeiros.
        n_faixas: número de bins (padrão: 10).

    Returns:
        MCE como float em [0, 1].
    """
    f = faixas(probs, rotulos, n_faixas)

    mce_valor = 0.0
    for faixa in f:
        if faixa["n"] > 0:
            acc_b = faixa["acuracia"]
            conf_b = faixa["confianca_media"]
            mce_valor = max(mce_valor, abs(acc_b - conf_b))

    return float(mce_valor)


def ece_por_classe(
    probs: list[list[float]], rotulos: list[int], n_faixas: int = 10
) -> dict[int, float]:
    """ECE por classe (classwise-ECE conforme Kull et al. 2019).

    Para cada classe c, calcula ECE usando p_c (probabilidade da classe)
    como confiança e (rotulo == c) como indicadora de acerto.

    Args:
        probs: lista de distribuições de probabilidade.
        rotulos: lista de rótulos verdadeiros.
        n_faixas: número de bins (padrão: 10).

    Returns:
        Dict mapeando classe (int) para ECE (float).
    """
    probs = np.array(probs)
    rotulos = np.array(rotulos)

    # Encontra as classes presentes nos rótulos
    classes = np.unique(rotulos)

    resultado = {}

    for classe in classes:
        # Probabilidade da classe c para cada amostra
        if classe < probs.shape[1]:
            probs_classe = probs[:, classe]
        else:
            # Classe fora do intervalo de probs
            continue

        # Indicadora: 1 se rótulo == classe, 0 caso contrário
        acertos = (rotulos == classe).astype(int)

        # Binning por confiança (probabilidade da classe)
        bins = np.linspace(0, 1, n_faixas + 1)
        ece_classe = 0.0
        N = len(rotulos)

        for i in range(n_faixas):
            inferior = bins[i]
            superior = bins[i + 1]

            # Última faixa inclui 1.0
            if i == n_faixas - 1:
                mascara = (probs_classe >= inferior) & (probs_classe <= superior)
            else:
                mascara = (probs_classe >= inferior) & (probs_classe < superior)

            n_b = np.sum(mascara)

            if n_b > 0:
                conf_b = float(np.mean(probs_classe[mascara]))
                acc_b = float(np.mean(acertos[mascara]))
                ece_classe += (n_b / N) * abs(acc_b - conf_b)

        resultado[int(classe)] = float(ece_classe)

    return resultado


def bootstrap(
    funcao: Callable, probs: list[list[float]], rotulos: list[int], reamostras: int = 1000, semente: int = 20261014,
    com_mediana: bool = False,
) -> tuple[float, float] | tuple[float, float, float]:
    """Bootstrap para intervalo de confiança de 95% (percentis 2.5/97.5).

    Reamostra os índices com reposição `reamostras` vezes, aplica `funcao`
    a cada reamostra e retorna os percentis 2.5 e 97.5 dos resultados.

    Args:
        funcao: função que recebe (probs, rotulos) e retorna float.
        probs: lista de distribuições de probabilidade.
        rotulos: lista de rótulos verdadeiros.
        reamostras: número de reamostras (padrão: 1000).
        semente: seed para np.random.default_rng (padrão: 20261014).

    Returns:
        Tupla (lower, upper) com os percentis 2.5 e 97.5 dos valores de `funcao`.
    """
    rng = np.random.default_rng(semente)
    N = len(rotulos)
    probs = np.array(probs)
    rotulos = np.array(rotulos)

    resultados = []

    for _ in range(reamostras):
        # Reamostra índices com reposição
        indices = rng.integers(0, N, size=N)

        # Seleciona os dados reamostrados
        probs_reamostra = probs[indices].tolist()
        rotulos_reamostra = rotulos[indices].tolist()

        # Aplica a função
        valor = funcao(probs_reamostra, rotulos_reamostra)
        resultados.append(valor)

    # Calcula percentis 2.5 e 97.5
    lower = float(np.percentile(resultados, 2.5))
    upper = float(np.percentile(resultados, 97.5))

    if com_mediana:
        return (lower, upper, float(np.percentile(resultados, 50)))
    return (lower, upper)
