"""Sinal de ironia: terceiro BERTimbau fine-tunado, classificacao binaria.

Corpus: MultiPICo-PT (Casola et al., ACL 2024, CC BY 4.0), ~1,9 mil pares
post-resposta de Reddit e Twitter, com as duas classes vindas das mesmas
fontes; publicado em 13/11/2026. A cabeca anterior, de agosto, era treinada no
IDPT 2021 (tweets e noticias), que entrega o rotulo pela procedencia.

POR QUE uma cabeca separada e nao mais uma classe do sinal de texto: ironia
nao e um sentimento, e uma relacao entre o que o texto DIZ e o que ele
SIGNIFICA. "Que atendimento maravilhoso, so esperei 3 horas" e lexicamente
positivo e pragmaticamente negativo -- as duas coisas ao mesmo tempo. Enfiar
isso como quarta classe de satisfacao obrigaria o modelo a escolher uma, e a
informacao de que ha conflito e justamente o que se perde.

LIMITACAO METODOLOGICA, a declarar no relatorio: o MultiPICo e anotado em posts
de redes sociais, nao em atendimento de chatbot. A transferencia de dominio
nao e verificada -- a frase canonica de atendimento sai com 0,16 de ironia, e
o F1-macro de 0,66 e medido no teste do proprio corpus.
"""

from pathlib import Path


from fraus.modelos import Conversa
from fraus.sinais.texto import (
    ModeloAusenteError,
    carregar_torch,
    prever_torch,
    temperatura_do_artefato,
)

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
        self._temperatura = temperatura_do_artefato(caminho_modelo)

    def prever_mensagens(self, textos: list[str]) -> list[list[float]]:
        """Probabilidades [nao_ironico, ironico] para cada texto."""
        return prever_torch(self._tokenizador, self._modelo, textos, self._temperatura)


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
