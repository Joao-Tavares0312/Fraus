"""Leitura de emocao pelo Laya exportado para ONNX -- so quando ele foi treinado.

O checkpoint base do Laya responde a pergunta de emocao a frio, e responder a
frio nao e medir: por isso esta leitura so existe quando o `manifesto.json` do
artefato declara a pergunta `emocao`, que e o que o notebook 07 grava depois do
fine-tuning. Artefato do notebook 06 (so ironia) nao tem a chave, e a resposta
aqui e "indisponivel", nunca um chute.

Usa o MESMO grafo carregado pela cabeca de ironia: um modelo, duas perguntas.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from fraus.treino_laya import PERGUNTA_EMOCAO, probabilidades_emocao


class EmocaoLayaIndisponivelError(RuntimeError):
    pass


def perguntas_do_artefato(diretorio: Path) -> tuple[str, ...]:
    """Perguntas que o artefato foi treinado para responder, pelo manifesto."""
    manifesto = Path(diretorio) / "manifesto.json"
    if not manifesto.is_file():
        return ("ironia",)
    perguntas = json.loads(manifesto.read_text(encoding="utf-8")).get("perguntas")
    return tuple(perguntas) if perguntas else ("ironia",)


class ClassificadorEmocaoLayaOnnx:
    """``prever_mensagens`` no formato do ``ClassificadorEmocao``: sete probabilidades."""

    def __init__(self, agente: Any) -> None:
        self._agente = agente

    def prever_mensagens(self, textos: list[str]) -> list[list[float]]:
        # Uma frase por chamada: o grafo exportado conserva batch 1 (ver
        # `ClassificadorIroniaLayaOnnx.prever_mensagens`).
        return [
            probabilidades_emocao(
                self._agente.predict_batch(
                    [texto], PERGUNTA_EMOCAO, lang="pt", sort_by_length=False
                )[0]
            )
            for texto in textos
        ]


def _diretorio_do_artefato() -> Path:
    from fraus.api.caminhos import CAMINHO_ONNX_LAYA

    return CAMINHO_ONNX_LAYA


@lru_cache(maxsize=1)
def obter_classificador_emocao_laya_onnx() -> ClassificadorEmocaoLayaOnnx:
    if "emocao" not in perguntas_do_artefato(_diretorio_do_artefato()):
        raise EmocaoLayaIndisponivelError(
            "o artefato Laya carregado é o checkpoint sem treino de emoção"
        )
    from fraus.sinais.ironia_laya import obter_classificador_ironia_laya_onnx

    return ClassificadorEmocaoLayaOnnx(obter_classificador_ironia_laya_onnx()._agente)
