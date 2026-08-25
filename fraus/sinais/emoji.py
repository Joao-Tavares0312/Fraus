"""Sinal de emoji.

Emojis NAO sao removidos no pre-processamento: carregam sinal de polaridade.
Lexicon: Emoji Sentiment Ranking (Kralj Novak et al., PLOS ONE 2015) --
751 emojis anotados por 83 anotadores sobre ~70k tweets.

A posicao relativa entra como feature porque a polaridade do emoji aumenta
conforme ele se aproxima do fim da mensagem.
"""

import csv
from functools import lru_cache
from pathlib import Path

import emoji as lib_emoji

from fraus.modelos import Conversa
from fraus.sinais.curadoria import CURADORIA_VAZIA, Curadoria

CAMINHO_LEXICON = Path(__file__).parent.parent / "dados" / "emoji_sentiment_ranking.csv"
LIMIAR_POLARIDADE = 0.1


@lru_cache(maxsize=1)
def _lexicon() -> dict[str, float]:
    tabela: dict[str, float] = {}
    with CAMINHO_LEXICON.open(encoding="utf-8", newline="") as arquivo:
        for linha in csv.DictReader(arquivo):
            negativo = float(linha["negativo"])
            neutro = float(linha["neutro"])
            positivo = float(linha["positivo"])
            total = negativo + neutro + positivo
            if total == 0:
                continue
            tabela[linha["emoji"]] = (positivo - negativo) / total
    return tabela


def score_do_emoji(caractere: str, curadoria: Curadoria | None = None) -> float:
    """Polaridade em [-1, 1]. Emoji fora do lexicon e nao curado vale 0.

    A CURADORIA VEM PRIMEIRO. O Emoji Sentiment Ranking anotou 751 emojis em
    2015: tudo que o Unicode acrescentou depois vale 0 aqui, e e exatamente esse
    buraco que o analista preenche. Vencer o ranking, e nao so complementa-lo,
    tambem permite corrigir um emoji cuja leitura mudou de uso desde 2015.
    """
    curado = (curadoria or CURADORIA_VAZIA).score_de(caractere)
    if curado is not None:
        return curado
    return _lexicon().get(caractere, 0.0)


def emojis_com_posicao(texto: str) -> list[tuple[str, float]]:
    """Emojis encontrados em `texto`, cada um com sua posicao relativa em [0, 1].

    Publica porque tanto `features_emoji` (agregado por conversa) quanto a
    rota de simulacao da API (emoji a emoji, texto avulso) precisam da mesma
    extracao -- reimplementar isso na API duplicaria a formula de posicao.
    """
    if not texto:
        return []
    achados = lib_emoji.emoji_list(texto)
    ultimo_indice = max(len(texto) - 1, 1)
    return [
        (achado["emoji"], achado["match_start"] / ultimo_indice)
        for achado in achados
    ]


@lru_cache(maxsize=1)
def linhas_lexicon() -> list[dict]:
    """Lexicon cru: uma linha por emoji, com as contagens de anotacao.

    Publica para a rota `/modelo/lexicon` da API poder paginar e buscar sem
    reler o CSV por conta propria -- a API so enxerga esta funcao, nunca o
    caminho do arquivo.
    """
    linhas: list[dict] = []
    with CAMINHO_LEXICON.open(encoding="utf-8", newline="") as arquivo:
        for linha in csv.DictReader(arquivo):
            linhas.append({
                "emoji": linha["emoji"],
                "negativo": int(float(linha["negativo"])),
                "neutro": int(float(linha["neutro"])),
                "positivo": int(float(linha["positivo"])),
            })
    return linhas


def features_emoji(
    conversa: Conversa, curadoria: Curadoria | None = None
) -> dict[str, float]:
    """Agrega os emojis das mensagens DO CLIENTE numa linha de features."""
    pares: list[tuple[str, float]] = []
    for mensagem in conversa.mensagens_cliente:
        pares.extend(emojis_com_posicao(mensagem.texto))

    if not pares:
        return {
            "emoji_score_medio": 0.0,
            "emoji_frac_positivos": 0.0,
            "emoji_frac_negativos": 0.0,
            "emoji_contagem": 0.0,
            "emoji_posicao_relativa_media": 0.0,
        }

    scores = [score_do_emoji(caractere, curadoria) for caractere, _ in pares]
    posicoes = [posicao for _, posicao in pares]
    total = len(scores)

    return {
        "emoji_score_medio": sum(scores) / total,
        "emoji_frac_positivos": sum(1 for s in scores if s > LIMIAR_POLARIDADE) / total,
        "emoji_frac_negativos": sum(1 for s in scores if s < -LIMIAR_POLARIDADE) / total,
        "emoji_contagem": float(total),
        "emoji_posicao_relativa_media": sum(posicoes) / total,
    }
