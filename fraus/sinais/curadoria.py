"""O que o analista ensinou ao lexico, e que o treino nao pegou.

O SentiLex-PT02 tem 79.189 formas e nao tem `lentissimo`. O Emoji Sentiment
Ranking tem 751 emojis anotados em 2015. Nem um nem outro conhece o jargao da
empresa que opera o atendimento. Este objeto e o que o analista acrescentou.

A CURADORIA VENCE O LEXICO BASE, e isso a faz servir aos dois casos: preencher
buraco (o termo nao existe) e corrigir polaridade errada para o dominio.

O QUE ELA NAO FAZ: corrigir score. Ela alimenta o sinal lexico, e quem pontua
continua sendo o fusor treinado -- o analista conserta o dicionario, nao a nota.
Um ajuste por cima do numero do modelo criaria uma SEGUNDA REGUA, que e a dor
que o README ja documenta com `PESO_NEUTRO_NO_SCORE`.

E UM DICIONARIO BURRO, DE PROPOSITO: nao normaliza, nao valida escala e nao sabe
o que e acento. Quem normaliza e quem escreve (a rota) e quem consulta (o
lexico, que ja calcula `sem_acento` para o proprio indice de reserva). Ensinar
normalizacao aqui criaria uma segunda regra de normalizacao, e duas regras
divergem.
"""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class Curadoria:
    """Os termos curados nesta instalacao, e a versao do conjunto.

    `versao` acompanha o objeto porque ela e gravada na conversa no momento da
    pontuacao: e o que permite a tela dizer depois "41 de 62 atendimentos foram
    pontuados com um lexico anterior" em vez de misturar duas reguas em
    silencio.
    """

    palavras: Mapping[str, int] = field(default_factory=dict)
    emojis: Mapping[str, float] = field(default_factory=dict)
    versao: int = 0

    def polaridade_de(self, termo: str) -> int | None:
        """Polaridade curada, ou `None` se o termo nao foi curado.

        `None` e "nao curado" -- o lexico base decide. ZERO e outra coisa: e
        "curado como neutro", que SILENCIA um termo que o SentiLex anota com
        polaridade errada para atendimento. As duas respostas nao podem colapsar
        numa so.
        """
        return self.palavras.get(termo)

    def score_de(self, caractere: str) -> float | None:
        """Score curado do emoji, ou `None` se nao foi curado."""
        return self.emojis.get(caractere)

    def total_de_palavras(self) -> int:
        return len(self.palavras)

    def total_de_emojis(self) -> int:
        return len(self.emojis)


# O padrao de todo chamador que nao tem curadoria: um objeto real e vazio, nunca
# `None` espalhado por dentro dos sinais. `None` continua sendo o valor do
# PARAMETRO das assinaturas publicas -- quem converte um no outro e o proprio
# sinal, num lugar so.
CURADORIA_VAZIA = Curadoria(
    palavras=MappingProxyType({}), emojis=MappingProxyType({}), versao=0
)
