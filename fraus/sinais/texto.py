"""Sinal de texto: BERTimbau fine-tunado, rodando em CPU.

Predicao POR MENSAGEM, nunca por conversa inteira -- e isso que permite a
atribuicao por sentenca na dashboard ("quais trechos puxaram a nota").

BERTimbau supera as variantes multilingues em classificacao de sentimento
PT-BR (Souza, Nogueira, Lotufo -- arXiv:2201.03382).
"""

from pathlib import Path

from fraus.modelos import Conversa

INSATISFEITO, NEUTRO, SATISFEITO = 0, 1, 2
TAMANHO_MAXIMO = 192


class ModeloAusenteError(RuntimeError):
    """Modelo nao encontrado ou ilegivel. Falha alta: sem modelo nao ha predicao."""


def carregar_torch(caminho_modelo: Path, rotulo: str):
    """Tokenizador e modelo do checkpoint, com o torch importado SO AQUI.

    O torch (497 MB) deixou de ser dependencia principal: com
    `FRAUS_BACKEND=onnx` a API pontua sem ele. Importar no topo do modulo faria
    `fraus.motor` -- que todo mundo importa -- exigir torch mesmo quando nenhum
    checkpoint torch vai ser carregado. Faltar o torch quando o backend E torch
    continua falha alta (invariante 7), com o remedio escrito.
    """
    try:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        import torch  # noqa: F401 - o from_pretrained precisa dele de verdade
    except ImportError as erro:
        raise ModeloAusenteError(
            f"{rotulo}: FRAUS_BACKEND=torch mas o torch nao esta instalado. "
            "Rode `uv sync --extra torch`, ou use FRAUS_BACKEND=onnx "
            "(ver docs/encolhimento.md)."
        ) from erro
    try:
        tokenizador = AutoTokenizer.from_pretrained(str(caminho_modelo))
        modelo = AutoModelForSequenceClassification.from_pretrained(str(caminho_modelo))
    except Exception as erro:
        raise ModeloAusenteError(f"{rotulo} em {caminho_modelo} ilegivel: {erro}") from erro
    modelo.eval()
    return tokenizador, modelo


def prever_torch(tokenizador, modelo, textos: list[str]) -> list[list[float]]:
    """Softmax por texto, num lote com padding pela mensagem mais longa."""
    if not textos:
        return []
    import torch

    with torch.inference_mode():
        entradas = tokenizador(
            textos, truncation=True, max_length=TAMANHO_MAXIMO, padding=True, return_tensors="pt"
        )
        logits = modelo(**entradas).logits
        return torch.softmax(logits, dim=-1).tolist()


class ClassificadorTexto:
    def __init__(self, caminho_modelo: Path) -> None:
        if not Path(caminho_modelo).is_dir():
            raise ModeloAusenteError(
                f"Modelo nao encontrado em {caminho_modelo}. "
                "Rode notebooks/01_treino_bertimbau.ipynb e copie o artefato. "
                "Ver docs/treinamento.md."
            )
        self._tokenizador, self._modelo = carregar_torch(caminho_modelo, "Modelo")

    def prever_mensagens(self, textos: list[str]) -> list[list[float]]:
        """Probabilidades [insatisfeito, neutro, satisfeito] para cada texto."""
        return prever_torch(self._tokenizador, self._modelo, textos)


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
