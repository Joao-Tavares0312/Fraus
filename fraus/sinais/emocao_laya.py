"""Leitura de emocao pelo Laya exportado para ONNX.

Usa o MESMO grafo carregado pela cabeca de ironia: um modelo, duas perguntas.

O checkpoint base do Laya responde a pergunta de emocao a frio, e responder a
frio nao e o mesmo que ter sido treinado para isso. Ate 02/10/2026 esta leitura
era recusada quando o artefato nao declarava a pergunta `emocao`; o efeito era
a comparacao ao vivo nunca fechar em producao, onde o Laya carregado e o
checkpoint base. Agora a leitura acontece e quem consome pergunta a
`laya_treinado_pelo_fraus` para ROTULAR: "Laya sem treino" e um dos tres
modelos do laudo (F1-macro de 0,296 em emocao no teste interno), e mostra-lo
com esse nome e medicao, nao chute.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from fraus.treino_laya import PERGUNTA_EMOCAO, probabilidades_emocao


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


def laya_treinado_pelo_fraus(diretorio: Path) -> bool:
    """O artefato saiu do fine-tuning do notebook 07? So ele declara `emocao`."""
    return "emocao" in perguntas_do_artefato(diretorio)


@lru_cache(maxsize=1)
def obter_classificador_emocao_laya_onnx() -> ClassificadorEmocaoLayaOnnx:
    from fraus.sinais.ironia_laya import obter_classificador_ironia_laya_onnx

    return ClassificadorEmocaoLayaOnnx(obter_classificador_ironia_laya_onnx()._agente)
