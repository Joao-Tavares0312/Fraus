"""Sinal de emocao: segundo BERTimbau fine-tunado, rodando em CPU.

Requisito de banca: distinguir as SETE emocoes humanas. A cabeca treinada tem
sete classes -- as seis basicas de Ekman (1992) mais o neutro, que nao e
emocao e sim a ausencia dela. A setima emocao, o DESPREZO, nao e treinada:
nenhum corpus rotulado em portugues a anota, e treinar so ela em corpus de
outra procedencia ensinaria o modelo a reconhecer o estilo do texto em vez do
desprezo. Ela e derivada da diade primaria raiva + nojo, que e como o Plutchik
(1980) a define -- ver `desprezo_derivado`.

Corpus: `go_emotions_ptbr`, traducao PT-BR do GoEmotions (Demszky et al.,
2020: 58k comentarios do Reddit, 27 emocoes + neutro), reduzido as seis de
Ekman pelo mapeamento oficial que o proprio GoEmotions publica.

LIMITACAO METODOLOGICA, a declarar no relatorio: o corpus foi traduzido por
maquina, sem revisao humana. Por isso a avaliacao reporta tambem o XED-pt, que
nao passou por traducao automatica. Ver docs/treinamento.md.
"""

from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from fraus.modelos import Conversa
from fraus.sinais.texto import ModeloAusenteError

# A ORDEM E CANONICA e vale no notebook 03, aqui e no fusor. Inverter nao gera
# erro: faz o sistema atribuir a emocao errada em silencio. Mesma armadilha da
# invariante 8, e mesma regra.
ALEGRIA, TRISTEZA, RAIVA, MEDO, NOJO, SURPRESA, NEUTRO = range(7)

NOMES_EMOCOES = ["alegria", "tristeza", "raiva", "medo", "nojo", "surpresa", "neutro"]

TAMANHO_MAXIMO = 192


def desprezo_derivado(prob_raiva: float, prob_nojo: float) -> float:
    """Desprezo como diade primaria raiva + nojo (Plutchik, 1980).

    Media GEOMETRICA, nao aritmetica: desprezo exige as DUAS emocoes juntas, e
    a media aritmetica daria 0.5 para raiva pura sem nojo nenhum -- o que e
    raiva, nao desprezo. O produto puro subestimaria (0.7 e 0.7 viram 0.49); a
    geometrica devolve 0.7, que e a leitura certa de "as duas altas".
    """
    return (max(0.0, prob_raiva) * max(0.0, prob_nojo)) ** 0.5


class ClassificadorEmocao:
    def __init__(self, caminho_modelo: Path) -> None:
        if not Path(caminho_modelo).is_dir():
            raise ModeloAusenteError(
                f"Modelo de emocao nao encontrado em {caminho_modelo}. "
                "Rode notebooks/03_treino_emocao.ipynb e copie o artefato. "
                "Ver docs/treinamento.md."
            )
        try:
            self._tokenizador = AutoTokenizer.from_pretrained(str(caminho_modelo))
            self._modelo = AutoModelForSequenceClassification.from_pretrained(str(caminho_modelo))
        except Exception as erro:
            raise ModeloAusenteError(f"Modelo de emocao em {caminho_modelo} ilegivel: {erro}") from erro
        self._modelo.eval()

    @torch.inference_mode()
    def prever_mensagens(self, textos: list[str]) -> list[list[float]]:
        """Probabilidades das sete classes, na ordem de NOMES_EMOCOES."""
        if not textos:
            return []
        entradas = self._tokenizador(
            textos, truncation=True, max_length=TAMANHO_MAXIMO, padding=True, return_tensors="pt"
        )
        logits = self._modelo(**entradas).logits
        return torch.softmax(logits, dim=-1).tolist()


def features_emocao(conversa: Conversa, classificador) -> dict[str, float]:
    """Media de cada emocao nas falas do cliente, mais o desprezo derivado.

    Sao OITO features: as sete classes treinadas e o desprezo da diade. A media
    e sobre as mensagens do cliente, coerente com o sinal de texto -- fala do
    bot nao carrega emocao do cliente.
    """
    textos = [m.texto for m in conversa.mensagens_cliente]
    if not textos:
        return {f"emocao_{nome}_media": 0.0 for nome in NOMES_EMOCOES} | {
            "emocao_desprezo_derivado": 0.0
        }

    probabilidades = classificador.prever_mensagens(textos)
    medias = [
        sum(p[indice] for p in probabilidades) / len(probabilidades)
        for indice in range(len(NOMES_EMOCOES))
    ]

    features = {f"emocao_{nome}_media": medias[i] for i, nome in enumerate(NOMES_EMOCOES)}
    features["emocao_desprezo_derivado"] = desprezo_derivado(medias[RAIVA], medias[NOJO])
    return features
