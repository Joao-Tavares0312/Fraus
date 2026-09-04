"""Fusor das sete familias de sinal que entram no vetor (de oito no sistema --
a ironia continua existindo, so nao pontua mais; ver `NOMES_FEATURES`).

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
from fraus.sinais.emocao import features_emocao
from fraus.sinais.emoji import features_emoji
from fraus.sinais.estilo import features_estilo
from fraus.sinais.incongruencia import features_incongruencia
from fraus.sinais.lexico import features_lexico
from fraus.sinais.tempo import features_tempo
from fraus.sinais.texto import features_texto

# Ordem canonica das 39 features, agrupadas por familia de sinal. A ordem
# importa: `vetorizar` produz o vetor nesta sequencia e o fusor treinado espera
# exatamente ela. Reordenar sem retreinar troca os pesos de lugar em silencio.
#
# Subiu de 16 para 35 em 21/08/2026: emocao, lexico e ironia ja existiam e
# estavam FORA do vetor esperando os notebooks 03 e 04, que agora existem;
# estilo nasceu junto. Ver a spec de 21/08/2026.
#
# Subiu de 35 para 40 em 03/09/2026: a familia `incongruencia_*` entrou para
# complementar o classificador de ironia, cuja transferencia de dominio
# (IDPT 2021, tweet e noticia) nunca foi verificada em atendimento. Ver a
# spec de 03/09/2026 e a bibliografia dela.
#
# Caiu de 40 para 38 em 04/09/2026: `ironia_prob_media` e `ironia_prob_max`
# SAIRAM do vetor. Medicao sobre o proprio corpus de treino (B2W-Reviews01,
# 500 resenhas por rotulo, semente 20260904) mostrou que a cabeca de ironia --
# treinada no IDPT 2021, tweet e noticia -- funciona em resenha de e-commerce
# como um detector de sentimento POSITIVO, nao de ironia:
#
#   resenha negativa: media P(ironia) = 0,1012  frac(P>0,5) = 0,092
#   resenha positiva: media P(ironia) = 0,7146  frac(P>0,5) = 0,740
#
# O fusor de 40 features aprendeu +0,77 de peso para `ironia_prob_media` no
# eixo satisfeito-menos-insatisfeito (o de 35 ja tinha +0,48, entao nao e
# regressao nova) -- mais ironia empurrando para SATISFEITO, o inverso do que
# o nome da feature promete. Consequencia: a frase canonica de ironia do
# proprio projeto, "que atendimento maravilhoso, so esperei 3 horas", pontuava
# 99,98 (nota 10, promotor) nesse fusor, porque as duas features que deveriam
# derruba-la empurravam para cima. A cabeca isolada acerta essa frase (0,998);
# quem lia ao contrario era o fusor, e so por causa do corpus.
#
# A cabeca de ironia CONTINUA carregada e obrigatoria (invariante 7) e
# CONTINUA aparecendo por mensagem na dashboard, onde e honesta -- so parou de
# PONTUAR. Se voce esta se perguntando por que existe `fraus/sinais/ironia.py`
# mas nenhuma `ironia_*` aqui: e por isto. Ver `docs/treinamento.md` para a
# medicao completa antes de reconsiderar.
NOMES_FEATURES = [
    # texto (4)
    "texto_prob_insatisfeito_media",
    "texto_prob_satisfeito_media",
    "texto_prob_insatisfeito_max",
    "texto_prob_satisfeito_ultima",
    # emoji (5)
    "emoji_score_medio",
    "emoji_frac_positivos",
    "emoji_frac_negativos",
    "emoji_contagem",
    "emoji_posicao_relativa_media",
    # tempo (7)
    "latencia_mediana_s",
    "latencia_p90_s",
    "latencia_primeira_resposta_s",
    "duracao_total_s",
    "qtd_turnos_cliente",
    "escalou",
    "abandonou",
    # emocao (8)
    "emocao_alegria_media",
    "emocao_tristeza_media",
    "emocao_raiva_media",
    "emocao_medo_media",
    "emocao_nojo_media",
    "emocao_surpresa_media",
    "emocao_neutro_media",
    "emocao_desprezo_derivado",
    # lexico (3)
    "lexico_polaridade_media",
    "lexico_cobertura",
    "lexico_frac_negados",
    # estilo (6)
    "estilo_frac_caixa_alta",
    "estilo_pontuacao_enfatica",
    "estilo_frac_alongamento",
    "estilo_palavrao_intensidade",
    "estilo_palavrao_dirigido",
    "estilo_frac_censurado",
    # incongruencia (5)
    "incongruencia_polaridade",
    "incongruencia_emoji_texto",
    "incongruencia_marcador_contraste",
    "incongruencia_hiperbole",
    "incongruencia_aspas_ironicas",
    "incongruencia_situacao_negativa",
]

INSATISFEITO, NEUTRO, SATISFEITO = 0, 1, 2

# Quanto P(neutro) vale no score 0-100. E o que faz a classe neutra do modelo
# alcancar a faixa neutra do NPS (7-8), e nao ha nada de arbitrario no valor:
#
#   classe pura      score              nota   categoria
#   insatisfeito     0                  0      detrator
#   neutro           100 * 0.75 = 75    8      neutro
#   satisfeito       100                10     promotor
#
# Com 0.5 -- o valor anterior -- a linha do meio dava score 50, nota 5, e caia
# em 0-6: DETRATOR. Nao numa borda rara, mas a classe neutra inteira, e num
# lote equilibrado por construcao isso produzia NPS negativo sem que o modelo
# tivesse errado nada. Ver `scripts/medir_faixas.py`, que mede as duas reguas.
#
# NAO e configuracao, e a diferenca importa: a faixa de NPS pode ser
# configuravel porque `categoria` e derivada na LEITURA e refatia dado que ja
# existe; o peso muda o `score` GRAVADO. Um botao aqui deixaria o banco com
# scores de duas reguas somados no mesmo agregado, e nenhuma leitura
# conseguiria separa-los. Mudar isto e mudar codigo e repontuar o banco --
# e e honesto que custe isso.
#
# O valor exato depende de arredondamento bancario: `round(7.5)` da 8 porque 8
# e par. Com 0.65 daria `round(6.5)` = 6, de volta a detrator. A fronteira esta
# fixada em tests/test_indicadores.py de proposito -- ela e fragil.
PESO_NEUTRO_NO_SCORE = 0.75


def montar_features(
    conversa: Conversa,
    classificador,
    classificador_emocao,
    curadoria=None,
) -> dict[str, float]:
    """Junta as SETE familias de sinal do vetor numa linha unica de features.

    Sao sete familias NO VETOR -- oito sinais existem no sistema, porque a
    ironia continua sendo lida por mensagem (ver `Motor._ironia_de`), so nao
    entra aqui. Ver o comentario acima de `NOMES_FEATURES` para o porque.

    Os dois classificadores (texto e emocao) sao OBRIGATORIOS desde que o
    contrato subiu para 35: emocao deixou de ser leitura decorativa e passou a
    mover a nota. Aceitar `None` aqui produziria vetor incompleto, e vetor
    incompleto vira `KeyError` la em `vetorizar` -- com a diferenca de que o
    erro apontaria para o lugar errado. Note que NAO ha `classificador_ironia`
    aqui: a cabeca de ironia continua obrigatoria para o Motor (invariante 7),
    mas este montador de vetor nao precisa mais dela.

    `curadoria` e opcional e chega POR PARAMETRO, nunca por estado global: e o
    que o analista ensinou ao lexico, lido a cada requisicao. Ela alcanca TRES
    familias -- `lexico_*`, `emoji_*` e `incongruencia_*`, que le os dois
    lexicos por dentro e portanto herda a curadoria deles -- e MAIS NENHUMA: o
    contrato continua de 39 chaves (invariante 9), e o que ela muda e o VALOR
    dessas familias, jamais o conjunto de features.
    """
    return {
        **features_texto(conversa, classificador),
        **features_emoji(conversa, curadoria),
        **features_tempo(conversa),
        **features_emocao(conversa, classificador_emocao),
        **features_lexico(conversa, curadoria),
        **features_estilo(conversa),
        **features_incongruencia(conversa, curadoria),
    }


class FusorIncompativelError(RuntimeError):
    """Artefato treinado (`.joblib`) nao bate com `NOMES_FEATURES` vigente.

    Distinta de `ModeloAusenteError` (fraus/sinais/texto.py) de proposito: as
    duas impedem servir predicao (invariante 7), mas o remedio e diferente. Um
    modelo AUSENTE pede treinar do zero; um modelo INCOMPATIVEL ja existe e
    foi treinado com um contrato antigo -- o remedio e RETREINAR com o
    contrato atual, nao gerar um artefato novo do nada. Misturar as duas
    mensagens levaria quem le o erro a rodar o notebook errado.
    """


def vetorizar(features: dict[str, float]) -> list[float]:
    """Ordem canonica. Feature faltando e KeyError; feature sobrando e ValueError.

    Nenhum dos dois casos pode virar zero silencioso (invariante 9): falta
    ja estourava; sobra nao estourava -- um dict com as 39 chaves certas MAIS
    uma extra passava batido, gerando um vetor do tamanho certo por acaso. E
    justamente o cenario que aconteceria se uma familia de sinal saisse do
    contrato (como `ironia_*` saiu em 04/09/2026) mas continuasse sendo
    produzida por engano em algum chamador: o vetor ficaria certo e a
    regressao passaria despercebida.
    """
    excedentes = set(features) - set(NOMES_FEATURES)
    if excedentes:
        raise ValueError(
            f"Chave(s) fora do contrato de {len(NOMES_FEATURES)} features: "
            f"{sorted(excedentes)}. Remova do dict antes de vetorizar, ou "
            "adicione a NOMES_FEATURES se a intencao e que ela entre no vetor."
        )
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
        """Score 0-100: P(satisfeito) mais P(neutro) pesado por
        `PESO_NEUTRO_NO_SCORE`.

        O score e uma PROJECAO das tres probabilidades num eixo, nao uma quarta
        predicao: o modelo continua o mesmo, treinado do mesmo jeito. O peso do
        neutro decide onde a classe do meio pousa nesse eixo -- e, por
        composicao com a faixa de NPS, em qual categoria ela cai. A tabela e o
        raciocinio estao na constante.

        O que este metodo NAO e: um lugar para consertar predicao. Se o modelo
        confunde as classes, o conserto e treino -- as medianas por classe do
        `scripts/medir_faixas.py` sao justamente o que separa os dois casos.
        """
        probabilidades = self._pipeline.predict_proba([vetorizar(features)])[0]
        classes = list(self._pipeline.named_steps["modelo"].classes_)
        por_classe = dict(zip(classes, probabilidades))
        score = 100.0 * (
            por_classe.get(SATISFEITO, 0.0)
            + PESO_NEUTRO_NO_SCORE * por_classe.get(NEUTRO, 0.0)
        )
        return max(0.0, min(100.0, score))

    def prever(self, features: dict[str, float]) -> int:
        """Classe predita: 0 insatisfeito, 1 neutro ou 2 satisfeito."""
        return int(self._pipeline.predict([vetorizar(features)])[0])

    def _diferenca(self):
        """O eixo satisfeito-menos-insatisfeito dos coeficientes aprendidos.

        Mora aqui porque `contribuicoes` (por conversa) e `eixo_global` (peso
        do modelo) precisam da MESMA regra de qual diferenca usar conforme as
        classes que o treino de fato viu -- duas copias divergiriam em silencio
        no caso binario, que e justamente o que ninguem testa a mao.
        """
        modelo = self._pipeline.named_steps["modelo"]
        classes = list(modelo.classes_)

        if len(classes) >= 3:
            return modelo.coef_[classes.index(SATISFEITO)] - modelo.coef_[classes.index(INSATISFEITO)]
        if len(classes) == 2 and INSATISFEITO in classes and SATISFEITO in classes:
            # Caso binario: sklearn guarda uma unica linha de coeficiente, que
            # ja representa a classe mais alta (classes_[1]) contra a mais
            # baixa (classes_[0]) -- aqui sempre satisfeito vs insatisfeito,
            # porque classes_ vem ordenado e insatisfeito (0) < satisfeito (2).
            return modelo.coef_[0]
        return [0.0] * len(NOMES_FEATURES)

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
        escala = self._pipeline.named_steps["escala"]
        vetor_padronizado = escala.transform([vetorizar(features)])[0]
        contribuicoes = [d * v for d, v in zip(self._diferenca(), vetor_padronizado)]
        return dict(zip(NOMES_FEATURES, (float(v) for v in contribuicoes)))

    def eixo_global(self) -> dict[str, float]:
        """Quanto cada feature empurra a nota NO MODELO INTEIRO, com sinal.

        Diferente de `importancias`, que e o peso ABSOLUTO (diz que a feature
        pesa, nao para que lado), e de `contribuicoes`, que e o numero de UMA
        conversa. O grafo da memoria consome este: ele responde "o que o modelo
        aprendeu que caracteriza um detrator".

        Nao ha padronizacao aqui porque nao ha conversa: e o coeficiente cru.

        Fusor nao treinado devolve `{}` -- e a ausencia de eixo, que o grafo
        distingue de "todas as features pesam zero".
        """
        if not hasattr(self._pipeline.named_steps["modelo"], "coef_"):
            return {}
        return dict(zip(NOMES_FEATURES, (float(v) for v in self._diferenca())))

    def importancias(self) -> dict[str, float]:
        """Peso absoluto medio de cada feature -- alimenta a explicacao na dashboard."""
        coeficientes = self._pipeline.named_steps["modelo"].coef_
        medias = coeficientes.__abs__().mean(axis=0)
        return dict(zip(NOMES_FEATURES, (float(v) for v in medias)))

    def salvar(self, caminho: Path) -> None:
        joblib.dump(self._pipeline, caminho)

    @classmethod
    def carregar(cls, caminho: Path) -> "Fusor":
        """Carrega o artefato e VALIDA a forma contra `NOMES_FEATURES` antes de devolver.

        `joblib.load` puro (o comportamento anterior) nao checava nada: um
        artefato de 40 features carregava sem erro contra um contrato de 38,
        a API subia normalmente, `/modelo/simular` funcionava (nao passa pelo
        fusor) e enganava quem testava a mao -- o `ValueError` do
        `StandardScaler` so estourava como HTTP 500 na primeira pontuacao
        real, em `/ingestao` ou `/conversas/importar`. Isso confundiu duas
        vezes na mesma semana. A invariante 7 pede falha alta e EXPLICITA
        para modelo incompativel, e "explicita" nao basta se so acontece na
        primeira predicao -- precisa ser na CARGA, que e quando a API sobe.
        """
        fusor = cls()
        fusor._pipeline = joblib.load(caminho)

        esperado = len(NOMES_FEATURES)
        recebido = fusor._pipeline.named_steps["escala"].n_features_in_
        if recebido != esperado:
            raise FusorIncompativelError(
                f"Fusor em {caminho} foi treinado com {recebido} features, "
                f"mas o contrato vigente (NOMES_FEATURES) tem {esperado}. "
                "Retreine notebooks/02_treino_fusor.ipynb com o contrato "
                "atual e substitua o artefato. Ver docs/treinamento.md."
            )
        return fusor
