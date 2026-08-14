"""Sinal lexico: SentiLex-PT02 com escopo de negacao.

Fonte: SentiLex-PT02 -- Silva, Carvalho e Sarmento, "Building a Sentiment
Lexicon for Social Judgement Mining" (PROPOR 2012), CC-BY. 79.189 formas
flexionadas depois da conversao, em fraus/dados/sentilex_pt02.csv. O
`scripts/preparar_sentilex.py` documenta o que foi normalizado.

POR QUE um lexicon se o BERTimbau ja le o texto: porque o lexicon nao foi
treinado nos mesmos dados nem carrega os mesmos vieses. Dois sinais de
procedencia independente que concordam sustentam a nota melhor que um sozinho,
e discordancia entre eles e informacao -- e o formato tipico da IRONIA, texto
lexicamente positivo com contexto negativo.

A NEGACAO e tratada por escopo, nao por saco de palavras: "nao foi otimo"
inverte a polaridade de "otimo". Sem isso o lexicon leria a frase como
positiva, que e o erro classico de analise lexical de sentimento.

LIMITACAO DO RECURSO, a declarar no relatorio: o SentiLex e um lexicon de
JULGAMENTO SOCIAL -- anota polaridade dirigida a entidades humanas. Ele e forte
no adjetivo que julga ("pessimo", "otimo", "incompetente") e NEUTRO em verbo de
afeto do proprio falante: `gostar`, `adorar` e `odiar` valem 0 nele. Por isso o
sinal lexico COMPLEMENTA o BERTimbau e nao o substitui -- o transformer e quem
le "adorei o produto".
"""

import csv
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from fraus.modelos import Conversa

CAMINHO_LEXICON = Path(__file__).parent.parent / "dados" / "sentilex_pt02.csv"

# Marcadores de negacao do portugues. `sem` entra porque "sem paciencia" e
# negacao real; `nada` e `nunca` idem. A lista e curta de proposito: marcador
# duvidoso inverte polaridade correta e faz mais estrago que a negacao perdida.
NEGACOES = frozenset(
    ["nao", "não", "nunca", "jamais", "nem", "nada", "ninguem", "ninguém",
     "nenhum", "nenhuma", "sem"]
)

# Quantos tokens a negacao alcanca depois de si. Tres e o valor usual na
# literatura de analise de sentimento; alem disso a inversao passa a pegar
# oracao seguinte ("nao chegou, mas o atendimento foi otimo").
ALCANCE_NEGACAO = 3

# Maior idioma do SentiLex tem varias palavras ("e uma copia mal feita"), entao
# a busca tenta n-gramas do maior para o menor antes de cair no token solto.
MAIOR_NGRAMA = 5

_TOKEN = re.compile(r"[0-9a-zà-ÿA-ZÀ-Ý\-]+")
# Pontuacao forte encerra o escopo da negacao: "nao chegou. otimo atendimento".
_FRONTEIRA = re.compile(r"[.!?;]")


@lru_cache(maxsize=1)
def _lexicon() -> dict[str, int]:
    tabela: dict[str, int] = {}
    with CAMINHO_LEXICON.open(encoding="utf-8", newline="") as arquivo:
        for linha in csv.DictReader(arquivo):
            tabela[linha["forma"]] = int(linha["polaridade"])
    return tabela


def sem_acento(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


@lru_cache(maxsize=1)
def _lexicon_sem_acento() -> dict[str, int]:
    """Indice de reserva: o SentiLex e acentuado, o cliente de chat nem sempre.

    Sem isto, "otimo" digitado corrido nao acha "otimo" com acento e a palavra
    mais comum de elogio some do sinal. Remover acento cria colisao em apenas
    24 chaves de 74.443 (`incomodo`/`incomodo`, `ingenua`/`ingenua`), e essas
    ficam ZERADAS: chute de polaridade errado e pior que termo ausente.
    """
    tabela: dict[str, int] = {}
    conflitantes: set[str] = set()
    for forma, polaridade in _lexicon().items():
        chave = sem_acento(forma)
        if chave in tabela and tabela[chave] != polaridade:
            conflitantes.add(chave)
        tabela[chave] = polaridade
    for chave in conflitantes:
        tabela[chave] = 0
    return tabela


def _polaridade(termo: str) -> int | None:
    """Busca exata primeiro; sem acento como reserva. None se nao existe."""
    exato = _lexicon().get(termo)
    if exato is not None:
        return exato
    return _lexicon_sem_acento().get(sem_acento(termo))


def polaridade_do_termo(termo: str) -> int:
    """Polaridade em -1/0/1. Termo fora do lexicon vale 0."""
    resultado = _polaridade(termo.lower())
    return 0 if resultado is None else resultado


def _segmentos(texto: str) -> list[str]:
    """Quebra em trechos delimitados por pontuacao forte, onde a negacao morre."""
    return [t for t in _FRONTEIRA.split(texto.lower()) if t.strip()]


def anotar_texto(texto: str) -> list[tuple[str, int, bool]]:
    """Termos do lexicon achados em `texto`: (termo, polaridade final, negado).

    A polaridade final ja vem com a negacao aplicada. `negado` diz se ela foi
    invertida -- e o que alimenta a feature de negacao, e o que permite mostrar
    na dashboard POR QUE um termo positivo contou como negativo.
    """
    achados: list[tuple[str, int, bool]] = []
    for segmento in _segmentos(texto):
        tokens = _TOKEN.findall(segmento)
        negacao_ate = -1
        indice = 0
        while indice < len(tokens):
            if tokens[indice] in NEGACOES:
                negacao_ate = indice + ALCANCE_NEGACAO
                indice += 1
                continue

            # Maior n-grama primeiro: o idioma vence o token solto que o compoe.
            for tamanho in range(min(MAIOR_NGRAMA, len(tokens) - indice), 0, -1):
                termo = " ".join(tokens[indice:indice + tamanho])
                polaridade = _polaridade(termo)
                if polaridade is None:
                    continue
                negado = indice <= negacao_ate
                achados.append((termo, -polaridade if negado else polaridade, negado))
                indice += tamanho
                break
            else:
                indice += 1
    return achados


def features_lexico(conversa: Conversa) -> dict[str, float]:
    """Tres features do lexicon sobre as falas do cliente.

    `lexico_cobertura` existe para o fusor saber QUANTA evidencia lexical
    sustenta a polaridade media: media de -1 apoiada em um termo vale menos que
    a mesma media apoiada em dez.
    """
    textos = [m.texto for m in conversa.mensagens_cliente]
    if not textos:
        return {
            "lexico_polaridade_media": 0.0,
            "lexico_frac_negados": 0.0,
            "lexico_cobertura": 0.0,
        }

    achados = [a for texto in textos for a in anotar_texto(texto)]
    total_tokens = sum(len(_TOKEN.findall(texto.lower())) for texto in textos)

    if not achados:
        return {
            "lexico_polaridade_media": 0.0,
            "lexico_frac_negados": 0.0,
            "lexico_cobertura": 0.0,
        }

    return {
        "lexico_polaridade_media": sum(p for _, p, _ in achados) / len(achados),
        "lexico_frac_negados": sum(1 for _, _, n in achados if n) / len(achados),
        "lexico_cobertura": len(achados) / total_tokens if total_tokens else 0.0,
    }
