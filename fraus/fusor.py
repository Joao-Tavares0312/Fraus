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

from fraus.modelos import Conversa
from fraus.sinais.emoji import features_emoji
from fraus.sinais.tempo import features_tempo
from fraus.sinais.texto import features_texto

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
        """Score 0-100: P(satisfeito) + metade de P(neutro).

        CONSEQUENCIA CONHECIDA E ACEITA, nao mexa achando que e bug: com peso
        0.5, uma conversa classificada com certeza como NEUTRA pontua 50, que
        vira nota 5, que cai na faixa 0-6 e portanto em DETRATOR. A classe
        neutra do modelo nunca alcanca a faixa neutra do NPS (7-8), que exigiria
        P(satisfeito) entre 0.4 e 0.8 -- um empate, nao uma neutralidade
        confiante.

        O efeito medido em 90 conversas do simulador, 30 por classe: 67%
        detrator, 29% promotor, 4% neutro, com NPS -38 num lote equilibrado por
        construcao. Subir o peso para 0.75 alinharia as tres classes as tres
        categorias; a decisao foi manter e declarar. Ver README, "Limitacoes
        conhecidas".
        """
        probabilidades = self._pipeline.predict_proba([vetorizar(features)])[0]
        classes = list(self._pipeline.named_steps["modelo"].classes_)
        por_classe = dict(zip(classes, probabilidades))
        score = 100.0 * (por_classe.get(SATISFEITO, 0.0) + 0.5 * por_classe.get(NEUTRO, 0.0))
        return max(0.0, min(100.0, score))

    def prever(self, features: dict[str, float]) -> int:
        """Classe predita: 0 insatisfeito, 1 neutro ou 2 satisfeito."""
        return int(self._pipeline.predict([vetorizar(features)])[0])

    def contribuicoes(self, features: dict[str, float]) -> dict[str, float]:
        """Quanto cada feature empurrou a nota DESTA conversa, com sinal.

        Eixo: coeficiente da classe satisfeito menos coeficiente da classe
        insatisfeito, multiplicado pelo valor JA PADRONIZADO da feature (o
        `StandardScaler` do pipeline aplicado, nunca o valor bruto). Positivo
        empurrou a nota para cima (rumo a satisfeito); negativo puxou para
        baixo (rumo a insatisfeito). E o numero da CONVERSA, diferente de
        `importancias`, que e o peso medio GLOBAL aprendido pelo modelo.

        Se o modelo aprendeu menos de tres classes e nao tem as duas pontas
        (insatisfeito e satisfeito) para formar a diferenca, nao ha eixo
        interpretavel: a contribuicao volta zerada para todas as features,
        em vez de estourar.
        """
        modelo = self._pipeline.named_steps["modelo"]
        escala = self._pipeline.named_steps["escala"]
        classes = list(modelo.classes_)
        vetor_padronizado = escala.transform([vetorizar(features)])[0]

        if len(classes) >= 3:
            diferenca = modelo.coef_[classes.index(SATISFEITO)] - modelo.coef_[classes.index(INSATISFEITO)]
        elif len(classes) == 2 and INSATISFEITO in classes and SATISFEITO in classes:
            # Caso binario: sklearn guarda uma unica linha de coeficiente,
            # que ja representa a classe mais alta (classes_[1]) contra a
            # mais baixa (classes_[0]) -- aqui sempre satisfeito vs insatisfeito,
            # porque classes_ vem ordenado e insatisfeito (0) < satisfeito (2).
            diferenca = modelo.coef_[0]
        else:
            diferenca = [0.0] * len(NOMES_FEATURES)

        contribuicoes = [d * v for d, v in zip(diferenca, vetor_padronizado)]
        return dict(zip(NOMES_FEATURES, (float(v) for v in contribuicoes)))

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
