"""Fusor dos tres sinais.

LogisticRegression com padronizacao: interpretavel de proposito -- o trabalho
precisa defender POR QUE um atendimento recebeu a nota, e coeficiente de
regressao logistica responde isso; floresta densa nao.

O peso da latencia e APRENDIDO aqui, nunca arbitrado: a relacao com satisfacao
e nao-linear e moderada por contexto.
"""

from pathlib import Path

import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from dolos.modelos import Conversa
from dolos.sinais.emoji import features_emoji
from dolos.sinais.tempo import features_tempo
from dolos.sinais.texto import features_texto

NOMES_FEATURES = [
    "texto_prob_insatisfeito_media",
    "texto_prob_satisfeito_media",
    "texto_prob_insatisfeito_max",
    "texto_prob_satisfeito_ultima",
    "emoji_score_medio",
    "emoji_frac_positivos",
    "emoji_frac_negativos",
    "emoji_contagem",
    "emoji_posicao_relativa_media",
    "latencia_mediana_s",
    "latencia_p90_s",
    "latencia_primeira_resposta_s",
    "duracao_total_s",
    "qtd_turnos_cliente",
    "escalou",
    "abandonou",
]

INSATISFEITO, NEUTRO, SATISFEITO = 0, 1, 2


def montar_features(conversa: Conversa, classificador) -> dict[str, float]:
    """Junta os tres sinais numa linha unica de features."""
    return {
        **features_texto(conversa, classificador),
        **features_emoji(conversa),
        **features_tempo(conversa),
    }


def vetorizar(features: dict[str, float]) -> list[float]:
    """Ordem canonica. Feature faltando e KeyError -- nunca zero silencioso."""
    return [float(features[nome]) for nome in NOMES_FEATURES]


class Fusor:
    def __init__(self) -> None:
        self._pipeline = Pipeline([
            ("escala", StandardScaler()),
            ("modelo", LogisticRegression(max_iter=1000)),
        ])

    def treinar(self, exemplos: list[dict[str, float]], rotulos: list[int]) -> None:
        self._pipeline.fit([vetorizar(e) for e in exemplos], rotulos)

    def pontuar(self, features: dict[str, float]) -> float:
        """Score 0-100: P(satisfeito) + metade de P(neutro)."""
        probabilidades = self._pipeline.predict_proba([vetorizar(features)])[0]
        classes = list(self._pipeline.named_steps["modelo"].classes_)
        por_classe = dict(zip(classes, probabilidades))
        score = 100.0 * (por_classe.get(SATISFEITO, 0.0) + 0.5 * por_classe.get(NEUTRO, 0.0))
        return max(0.0, min(100.0, score))

    def importancias(self) -> dict[str, float]:
        """Peso absoluto medio de cada feature -- alimenta a explicacao na dashboard."""
        coeficientes = self._pipeline.named_steps["modelo"].coef_
        medias = coeficientes.__abs__().mean(axis=0)
        return dict(zip(NOMES_FEATURES, (float(v) for v in medias)))

    def salvar(self, caminho: Path) -> None:
        joblib.dump(self._pipeline, caminho)

    @classmethod
    def carregar(cls, caminho: Path) -> "Fusor":
        fusor = cls()
        fusor._pipeline = joblib.load(caminho)
        return fusor
