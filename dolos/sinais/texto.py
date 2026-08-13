"""Sinal de texto: BERTimbau fine-tunado, rodando em CPU.

Predicao POR MENSAGEM, nunca por conversa inteira -- e isso que permite a
atribuicao por sentenca na dashboard ("quais trechos puxaram a nota").

BERTimbau supera as variantes multilingues em classificacao de sentimento
PT-BR (Souza, Nogueira, Lotufo -- arXiv:2201.03382).
"""

from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from dolos.modelos import Conversa

INSATISFEITO, NEUTRO, SATISFEITO = 0, 1, 2
TAMANHO_MAXIMO = 192


class ModeloAusenteError(RuntimeError):
    """Modelo nao encontrado ou ilegivel. Falha alta: sem modelo nao ha predicao."""


class ClassificadorTexto:
    def __init__(self, caminho_modelo: Path) -> None:
        if not Path(caminho_modelo).is_dir():
            raise ModeloAusenteError(
                f"Modelo nao encontrado em {caminho_modelo}. "
                "Rode notebooks/01_treino_bertimbau.ipynb e copie o artefato. "
                "Ver docs/treinamento.md."
            )
        try:
            self._tokenizador = AutoTokenizer.from_pretrained(str(caminho_modelo))
            self._modelo = AutoModelForSequenceClassification.from_pretrained(str(caminho_modelo))
        except Exception as erro:
            raise ModeloAusenteError(f"Modelo em {caminho_modelo} ilegivel: {erro}") from erro
        self._modelo.eval()

    @torch.inference_mode()
    def prever_mensagens(self, textos: list[str]) -> list[list[float]]:
        """Probabilidades [insatisfeito, neutro, satisfeito] para cada texto."""
        if not textos:
            return []
        entradas = self._tokenizador(
            textos, truncation=True, max_length=TAMANHO_MAXIMO, padding=True, return_tensors="pt"
        )
        logits = self._modelo(**entradas).logits
        return torch.softmax(logits, dim=-1).tolist()


def features_texto(conversa: Conversa, classificador) -> dict[str, float]:
    textos = [m.texto for m in conversa.mensagens_cliente]
    if not textos:
        return {
            "texto_prob_insatisfeito_media": 0.0,
            "texto_prob_satisfeito_media": 0.0,
            "texto_prob_insatisfeito_max": 0.0,
            "texto_prob_satisfeito_ultima": 0.0,
        }

    probabilidades = classificador.prever_mensagens(textos)
    insatisfeito = [p[INSATISFEITO] for p in probabilidades]
    satisfeito = [p[SATISFEITO] for p in probabilidades]

    return {
        "texto_prob_insatisfeito_media": sum(insatisfeito) / len(insatisfeito),
        "texto_prob_satisfeito_media": sum(satisfeito) / len(satisfeito),
        "texto_prob_insatisfeito_max": max(insatisfeito),
        "texto_prob_satisfeito_ultima": satisfeito[-1],
    }
