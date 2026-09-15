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


from fraus.modelos import Conversa
from fraus.sinais.texto import ModeloAusenteError, carregar_torch, prever_torch

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
        self._tokenizador, self._modelo = carregar_torch(caminho_modelo, "Modelo de ironia")

    def prever_mensagens(self, textos: list[str]) -> list[list[float]]:
        """Probabilidades [nao_ironico, ironico] para cada texto."""
        return prever_torch(self._tokenizador, self._modelo, textos)


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
