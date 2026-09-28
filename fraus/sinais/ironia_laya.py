"""Adaptador do Laya multilíngue para o contrato binário de ironia do Fraus.

O Laya continua opcional: importar o Fraus ou usar BERTimbau/ONNX não pode
arrastar torch nem baixar pesos. A dependência e o checkpoint só são tocados
quando ``FRAUS_IRONIA_BACKEND=laya`` é declarado.
"""

from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache
import os
from typing import Any


REVISAO_LAYA_PADRAO = "55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851"

PERGUNTA_IRONIA = {
    "ironia": {
        "type": "choice",
        "instructions": (
            "A fala do cliente é irônica? Considere incongruência entre o "
            "sentido literal e a situação descrita."
        ),
        # Chaves neutras evitam o viés documentado dos rótulos true/false.
        "criteria": {
            "A": "há ironia ou incongruência entre elogio literal e situação negativa",
            "B": "a fala é literal e não irônica",
        },
    }
}


class DependenciaLayaAusenteError(RuntimeError):
    pass


class RespostaLayaInvalidaError(RuntimeError):
    pass


def revisao_laya_declarada() -> str:
    return os.environ.get("FRAUS_LAYA_REVISAO") or REVISAO_LAYA_PADRAO


class ClassificadorIroniaLaya:
    """Expõe ``prever_mensagens`` no mesmo formato das cabeças existentes."""

    def __init__(
        self,
        *,
        router: Any | None = None,
        revisao: str = REVISAO_LAYA_PADRAO,
        modelo: str = "multilingual",
    ) -> None:
        if router is None:
            try:
                from laya import Router
            except ImportError as erro:
                raise DependenciaLayaAusenteError(
                    "O backend de ironia Laya exige `uv sync --extra laya`."
                ) from erro
            router = Router(revision=revisao, max_loaded=1)
        self._router = router
        self._modelo = modelo

    @staticmethod
    def _probabilidade_ironia(resultado: dict[str, Any]) -> float:
        try:
            probabilidades = resultado["answers"]["ironia"]["probabilities"]
            probabilidade = float(probabilidades["A"])
        except (KeyError, TypeError, ValueError) as erro:
            raise RespostaLayaInvalidaError(
                "Laya não devolveu answers.ironia.probabilities.A"
            ) from erro
        if not 0.0 <= probabilidade <= 1.0:
            raise RespostaLayaInvalidaError("probabilidade de ironia fora de 0..1")
        return probabilidade

    def prever_mensagens(self, textos: list[str]) -> list[list[float]]:
        if not textos:
            return []
        requisicoes = [
            {
                "state": texto,
                "questions": PERGUNTA_IRONIA,
                "model": self._modelo,
                "lang": "pt",
            }
            for texto in textos
        ]
        resultados: Sequence[dict[str, Any]] = self._router.predict_batch(
            requisicoes, sort_by_length=True
        )
        if len(resultados) != len(textos):
            raise RespostaLayaInvalidaError("Laya devolveu quantidade inesperada de respostas")
        probabilidades = [self._probabilidade_ironia(resultado) for resultado in resultados]
        return [[1.0 - probabilidade, probabilidade] for probabilidade in probabilidades]


@lru_cache(maxsize=1)
def obter_classificador_ironia_laya() -> ClassificadorIroniaLaya:
    """Uma instância por processo, compartilhada pela API e pelo Motor."""
    return ClassificadorIroniaLaya(revisao=revisao_laya_declarada())
