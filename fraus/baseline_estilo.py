"""Baseline que so enxerga a SUPERFICIE do texto -- nenhuma palavra.

Se um classificador de caixa, pontuacao e tamanho acerta a ironia de um
corpus, o corpus mede registro e nao ironia (foi o que o IDPT fez em
08/10/2026, ver docs/ironia.md). Na regua de pares, ele e a linha que todo
modelo de ironia tem de vencer para ser promovido.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

import numpy as np
from sklearn.linear_model import LogisticRegression

NOMES_TRACOS = (
    "comprimento_log", "prop_maiusculas", "inicio_minusculo", "termina_ponto",
    "exclamacoes", "interrogacoes", "reticencias", "tem_digito", "tem_reais",
    "tem_url", "tem_arroba", "tem_hashtag", "tem_emoji", "alongamento", "risada",
)
TRACOS_BINARIOS = (
    "inicio_minusculo", "termina_ponto", "reticencias", "tem_digito", "tem_reais",
    "tem_url", "tem_arroba", "tem_hashtag", "tem_emoji", "alongamento", "risada",
)

_EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
_URL = re.compile(r"https?://|www\.")
_ALONGAMENTO = re.compile(r"([^\W\d_])\1{2,}")
_RISADA = re.compile(r"\b(k{3,}|(?:ha){2,}|(?:rs){2,})\b")


def tracos_de_superficie(texto: str) -> dict[str, float]:
    """Os 15 tracos, na ordem de `NOMES_TRACOS`."""
    texto = str(texto)
    aparado = texto.strip()
    letras = [c for c in texto if c.isalpha()]
    minusculo = texto.lower()
    return {
        "comprimento_log": float(np.log1p(len(texto))),
        "prop_maiusculas": sum(c.isupper() for c in letras) / len(letras) if letras else 0.0,
        "inicio_minusculo": float(bool(aparado) and aparado[0].isalpha() and aparado[0].islower()),
        "termina_ponto": float(aparado.endswith(".") and not aparado.endswith("...")),
        "exclamacoes": float(texto.count("!")),
        "interrogacoes": float(texto.count("?")),
        "reticencias": float("..." in texto or "…" in texto),
        "tem_digito": float(any(c.isdigit() for c in texto)),
        "tem_reais": float("r$" in minusculo),
        "tem_url": float(bool(_URL.search(texto))),
        "tem_arroba": float("@" in texto),
        "tem_hashtag": float("#" in texto),
        "tem_emoji": float(bool(_EMOJI.search(texto))),
        "alongamento": float(bool(_ALONGAMENTO.search(minusculo))),
        "risada": float(bool(_RISADA.search(minusculo))),
    }


def matriz_de_tracos(textos: Sequence[str]) -> np.ndarray:
    return np.array(
        [[tracos_de_superficie(t)[nome] for nome in NOMES_TRACOS] for t in textos], dtype=float
    ).reshape(len(textos), len(NOMES_TRACOS))


class BaselineEstilo:
    """Regressao logistica sobre os tracos de superficie."""

    def __init__(self, semente: int = 42):
        self._modelo = LogisticRegression(max_iter=1000, random_state=semente)

    def treinar(self, textos: Sequence[str], rotulos: Sequence[int]) -> "BaselineEstilo":
        self._modelo.fit(matriz_de_tracos(textos), np.asarray(rotulos, dtype=int))
        return self

    def prever(self, textos: Sequence[str]) -> list[int]:
        return [int(c) for c in self._modelo.predict(matriz_de_tracos(textos))]

    def prever_probabilidades(self, textos: Sequence[str]) -> list[float]:
        classes = list(self._modelo.classes_)
        return [float(p[classes.index(1)]) for p in self._modelo.predict_proba(matriz_de_tracos(textos))]
