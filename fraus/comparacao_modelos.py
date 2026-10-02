"""Comparacao pareada de dois classificadores no MESMO conjunto de teste.

"O modelo novo acertou mais" nao e resultado enquanto nao se sabe se a
diferenca sobrevive a outra amostra do mesmo teste. Duas medidas, as duas
pareadas (os dois modelos leem exatamente os mesmos exemplos):

- McNemar exato sobre os exemplos em que SO UM dos modelos acerta -- os
  exemplos em que os dois acertam ou os dois erram nao distinguem ninguem;
- intervalo de confianca por bootstrap da diferenca de F1-macro, porque
  acuracia esconde classe rara e o corpus de emocao e desequilibrado em 43:1.

Parte pura: listas de rotulos e predicoes, sem modelo nenhum.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import comb

import numpy as np


@dataclass(frozen=True)
class ResultadoMcNemar:
    so_a: int
    so_b: int
    p_valor: float


@dataclass(frozen=True)
class ResultadoBootstrap:
    diferenca: float
    ic_inferior: float
    ic_superior: float
    reamostras: int


def f1_macro(rotulos: Sequence[int], preditos: Sequence[int], *, classes: Sequence[int]) -> float:
    """Media simples do F1 por classe; classe sem acerto conta zero."""
    rotulos, preditos = np.asarray(rotulos), np.asarray(preditos)
    f1s = []
    for classe in classes:
        acertos = int(np.sum((rotulos == classe) & (preditos == classe)))
        denominador = int(np.sum(rotulos == classe)) + int(np.sum(preditos == classe))
        f1s.append(2 * acertos / denominador if denominador else 0.0)
    return float(np.mean(f1s))


def mcnemar_exato(acertos_a: Sequence[bool], acertos_b: Sequence[bool]) -> ResultadoMcNemar:
    """Teste binomial exato bilateral sobre os pares discordantes."""
    if len(acertos_a) != len(acertos_b):
        raise ValueError("os dois modelos precisam ser avaliados nos mesmos exemplos")
    so_a = sum(1 for a, b in zip(acertos_a, acertos_b) if a and not b)
    so_b = sum(1 for a, b in zip(acertos_a, acertos_b) if b and not a)
    discordantes = so_a + so_b
    if discordantes == 0:
        return ResultadoMcNemar(0, 0, 1.0)
    cauda = sum(comb(discordantes, i) for i in range(min(so_a, so_b) + 1)) / 2**discordantes
    return ResultadoMcNemar(so_a, so_b, min(1.0, 2 * cauda))


def bootstrap_da_diferenca(
    rotulos: Sequence[int],
    preditos_a: Sequence[int],
    preditos_b: Sequence[int],
    *,
    classes: Sequence[int],
    reamostras: int = 2000,
    semente: int = 42,
) -> ResultadoBootstrap:
    """IC 95% percentil de F1-macro(A) - F1-macro(B), reamostrando exemplos."""
    if not len(rotulos) == len(preditos_a) == len(preditos_b):
        raise ValueError("os dois modelos precisam ser avaliados nos mesmos exemplos")
    rotulos, preditos_a, preditos_b = map(np.asarray, (rotulos, preditos_a, preditos_b))
    gerador = np.random.default_rng(semente)
    diferencas = np.empty(reamostras)
    for i in range(reamostras):
        amostra = gerador.integers(0, len(rotulos), len(rotulos))
        diferencas[i] = f1_macro(rotulos[amostra], preditos_a[amostra], classes=classes) - f1_macro(
            rotulos[amostra], preditos_b[amostra], classes=classes
        )
    inferior, superior = np.percentile(diferencas, [2.5, 97.5])
    return ResultadoBootstrap(
        diferenca=f1_macro(rotulos, preditos_a, classes=classes)
        - f1_macro(rotulos, preditos_b, classes=classes),
        ic_inferior=float(inferior),
        ic_superior=float(superior),
        reamostras=reamostras,
    )
