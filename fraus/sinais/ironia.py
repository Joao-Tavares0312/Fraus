"""Sinal de ironia: terceiro BERTimbau fine-tunado, classificacao binaria.

Corpus: IDPT 2021 -- tarefa de Irony Detection in Portuguese do IberLEF, com
15,2k tweets e 18,4k noticias anotados como ironico ou nao-ironico.

POR QUE uma cabeca separada e nao mais uma classe do sinal de texto: ironia
nao e um sentimento, e uma relacao entre o que o texto DIZ e o que ele
SIGNIFICA. "Que atendimento maravilhoso, so esperei 3 horas" e lexicamente
positivo e pragmaticamente negativo -- as duas coisas ao mesmo tempo. Enfiar
isso como quarta classe de satisfacao obrigaria o modelo a escolher uma, e a
informacao de que ha conflito e justamente o que se perde.

LIMITACAO METODOLOGICA, a declarar no relatorio: o IDPT e anotado em tweets e
comentarios de noticia, nao em atendimento de chatbot. A transferencia de
dominio nao e verificada -- ironia em reclamacao de suporte pode ter forma
diferente da ironia em comentario de politica.
"""

from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from fraus.modelos import Conversa
from fraus.sinais.texto import ModeloAusenteError

# Ordem canonica das duas classes, valida no notebook 04 e aqui.
NAO_IRONICO, IRONICO = 0, 1

TAMANHO_MAXIMO = 192


class ClassificadorIronia:
    def __init__(self, caminho_modelo: Path) -> None:
        if not Path(caminho_modelo).is_dir():
            raise ModeloAusenteError(
                f"Modelo de ironia nao encontrado em {caminho_modelo}. "
                "Rode notebooks/04_treino_ironia.ipynb e copie o artefato. "
                "Ver docs/treinamento.md."
            )
        try:
            self._tokenizador = AutoTokenizer.from_pretrained(str(caminho_modelo))
            self._modelo = AutoModelForSequenceClassification.from_pretrained(str(caminho_modelo))
        except Exception as erro:
            raise ModeloAusenteError(
                f"Modelo de ironia em {caminho_modelo} ilegivel: {erro}"
            ) from erro
        self._modelo.eval()

    @torch.inference_mode()
    def prever_mensagens(self, textos: list[str]) -> list[list[float]]:
        """Probabilidades [nao_ironico, ironico] para cada texto."""
        if not textos:
            return []
        entradas = self._tokenizador(
            textos, truncation=True, max_length=TAMANHO_MAXIMO, padding=True, return_tensors="pt"
        )
        logits = self._modelo(**entradas).logits
        return torch.softmax(logits, dim=-1).tolist()


def features_ironia(conversa: Conversa, classificador) -> dict[str, float]:
    """Media e maximo da probabilidade de ironia nas falas do cliente.

    O MAXIMO importa tanto quanto a media: uma unica frase irônica no fim
    ("otimo servico, parabens") reverte a leitura da conversa inteira, e a
    media sozinha diluiria ela entre as falas neutras anteriores.
    """
    textos = [m.texto for m in conversa.mensagens_cliente]
    if not textos:
        return {"ironia_prob_media": 0.0, "ironia_prob_max": 0.0}

    probabilidades = [p[IRONICO] for p in classificador.prever_mensagens(textos)]
    return {
        "ironia_prob_media": sum(probabilidades) / len(probabilidades),
        "ironia_prob_max": max(probabilidades),
    }
