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

ELA NAO VALIDA ESCALA: quem impoe -1/0/+1 na palavra e [-1,1] no emoji e a rota,
onde a mensagem de recusa pode nomear a regua. Aqui ja chega valido.

O QUE ELA SABE, e precisa saber, e ACENTO -- pelo mesmo motivo que o lexicon
base tem indice de reserva: quem cura `lentissimo` com acento espera que o
cliente que digitou sem acento seja alcancado. Quem possui a chave possui o
indice dela; empurrar isso para o lexico o faria varrer os termos curados a cada
token, em vez de consultar um dicionario pronto.
"""

from dataclasses import dataclass, field
from functools import cached_property
from types import MappingProxyType
from typing import Mapping

from fraus.sinais.normalizacao import sem_acento


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

    @cached_property
    def _palavras_sem_acento(self) -> Mapping[str, int]:
        """Indice de reserva das palavras curadas, sem diacritico.

        Espelha o `_lexicon_sem_acento` do lexico base, e pelo mesmo motivo: o
        cliente de chat nem sempre acentua. Sem ele, curar `lentissimo` com
        acento nao alcancaria a fala que veio sem.

        CONFLITO ZERA, tambem como no lexico base: se duas palavras curadas
        colapsam na mesma chave sem acento com polaridades diferentes, nenhuma
        das duas responde por ela. Chute de polaridade errado e pior que termo
        ausente -- e aqui a curadora ainda pode cadastrar a forma exata.

        `cached_property` num dataclass congelado funciona porque ela escreve no
        `__dict__` da instancia diretamente, sem passar pelo `__setattr__` que o
        `frozen` bloqueia. O indice e construido uma vez por objeto, e o objeto
        vive uma requisicao.
        """
        indice: dict[str, int] = {}
        conflitantes: set[str] = set()
        for forma, polaridade in self.palavras.items():
            chave = sem_acento(forma)
            if chave in indice and indice[chave] != polaridade:
                conflitantes.add(chave)
            indice[chave] = polaridade
        for chave in conflitantes:
            del indice[chave]
        return indice

    def polaridade_de(self, termo: str) -> int | None:
        """Polaridade curada, ou `None` se o termo nao foi curado.

        `None` e "nao curado" -- o lexico base decide. ZERO e outra coisa: e
        "curado como neutro", que SILENCIA um termo que o SentiLex anota com
        polaridade errada para atendimento. As duas respostas nao podem colapsar
        numa so.
        """
        exato = self.palavras.get(termo)
        if exato is not None:
            return exato
        return self._palavras_sem_acento.get(sem_acento(termo))

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
