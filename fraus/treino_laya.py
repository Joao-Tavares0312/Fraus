"""Formato de treino do Laya para as duas perguntas do Fraus: emocao e ironia.

O Laya nao tem cabeca por tarefa: ele responde perguntas ``choice`` sobre um
estado, pontuando cada opcao. Fine-tuning, entao, e ensinar o MESMO checkpoint
a responder estas duas perguntas -- e por isso elas moram aqui, em codigo
testado, e nao digitadas no notebook: treinar numa redacao e servir outra e
treinar o modelo errado sem erro nenhum.

Cada caso e uma linha de JSONL no esquema do upstream (``state`` /
``questions`` / ``gold``), lido por ``research/scripts/finetune_single_device.py``
do repositorio do Laya. O alvo e uma DISTRIBUICAO por opcao, nao um rotulo
duro: a perda RLCD imita a distribuicao, e o GoEmotions publica o voto de cada
anotador -- a discordancia entre eles e sinal, nao ruido a apagar.

Nada aqui importa torch nem o pacote ``laya``.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from fraus.sinais.emocao import NOMES_EMOCOES
from fraus.sinais.ironia_laya import PERGUNTA_IRONIA

# Um criterio por classe, na redacao de quem le atendimento. As CHAVES sao os
# nomes de NOMES_EMOCOES e a ordem e a dele: e por ela que as probabilidades
# sao lidas de volta em `probabilidades_emocao`.
_CRITERIOS_EMOCAO = {
    "alegria": "contentamento, satisfação, gratidão ou alívio",
    "tristeza": "tristeza, decepção ou desânimo",
    "raiva": "raiva, irritação ou indignação",
    "medo": "medo, preocupação ou insegurança",
    "nojo": "nojo, repulsa ou aversão",
    "surpresa": "surpresa, espanto ou confusão",
    "neutro": "nenhuma emoção aparente, apenas informação ou pedido",
}

PERGUNTA_EMOCAO = {
    "emocao": {
        "type": "choice",
        "instructions": "Qual emoção predomina na fala do cliente?",
        "criteria": {nome: _CRITERIOS_EMOCAO[nome] for nome in NOMES_EMOCOES},
    }
}


def distribuicao_de_votos(votos: Sequence[float]) -> list[float]:
    """Votos por classe viram probabilidade por classe.

    Soma zero LEVANTA. O script do Laya trocaria por distribuicao uniforme em
    silencio, e um exemplo sem rotulo passaria a ensinar "nao sei".
    """
    if any(voto < 0 for voto in votos):
        raise ValueError("voto negativo")
    total = sum(votos)
    if total <= 0:
        raise ValueError("exemplo sem nenhum voto: nao ha distribuicao a ensinar")
    return [voto / total for voto in votos]


def distribuicao_de_rotulo(indice: int, total: int, *, suavizacao: float = 0.0) -> list[float]:
    """Rotulo duro como distribuicao, com label smoothing opcional."""
    if not 0 <= indice < total:
        raise ValueError(f"rotulo {indice} fora de 0..{total - 1}")
    if not 0.0 <= suavizacao < 1.0:
        raise ValueError("suavizacao fora de [0, 1)")
    piso = suavizacao / total
    distribuicao = [piso] * total
    distribuicao[indice] += 1.0 - suavizacao
    return distribuicao


def _estado(texto: str) -> str:
    if not texto or not texto.strip():
        raise ValueError("caso de treino sem texto")
    return texto


def caso_emocao(texto: str, distribuicao: Sequence[float]) -> dict[str, Any]:
    """Uma linha do JSONL de treino para a pergunta de emocao."""
    if len(distribuicao) != len(NOMES_EMOCOES):
        raise ValueError(
            f"distribuicao com {len(distribuicao)} valores para {len(NOMES_EMOCOES)} emocoes"
        )
    return {
        "state": _estado(texto),
        "questions": PERGUNTA_EMOCAO,
        "gold": {
            "emocao": {
                "probabilities": {
                    nome: float(p) for nome, p in zip(NOMES_EMOCOES, distribuicao)
                }
            }
        },
    }


def caso_ironia(texto: str, probabilidade_ironia: float) -> dict[str, Any]:
    """Uma linha do JSONL de treino para a pergunta de ironia (A ironica, B literal)."""
    if not 0.0 <= probabilidade_ironia <= 1.0:
        raise ValueError("probabilidade de ironia fora de 0..1")
    return {
        "state": _estado(texto),
        "questions": PERGUNTA_IRONIA,
        "gold": {
            "ironia": {
                "probabilities": {
                    "A": float(probabilidade_ironia),
                    "B": 1.0 - float(probabilidade_ironia),
                }
            }
        },
    }


def repeticoes_por_classe(contagens: Sequence[int], *, teto: int = 4) -> list[int]:
    """Quantas vezes repetir cada exemplo da classe no treino.

    O script do Laya nao aceita peso de classe na perda, e o corpus de emocao
    e desequilibrado em 43:1. A compensacao vai para o dado: raiz quadrada da
    razao para a classe majoritaria, com teto. Raiz e nao a razao inteira
    porque repetir `nojo` 43 vezes e ensinar o modelo a decorar 444 frases.
    """
    maior = max(contagens, default=0)
    return [
        0 if contagem <= 0 else max(1, min(teto, round((maior / contagem) ** 0.5)))
        for contagem in contagens
    ]


def probabilidades_emocao(resultado: dict[str, Any]) -> list[float]:
    """Probabilidades da resposta do Laya na ordem de ``NOMES_EMOCOES``.

    Classe ausente levanta ``KeyError`` -- nunca zero silencioso.
    """
    probabilidades = resultado["answers"]["emocao"]["probabilities"]
    return [float(probabilidades[nome]) for nome in NOMES_EMOCOES]


def mapa_de_poda(
    ids_mantidos: Iterable[int], *, tamanho: int, id_desconhecido: int
) -> tuple[list[int], list[int]]:
    """Mapa id-original -> linha da tabela de embeddings podada.

    O checkpoint multilingue carrega 256 mil tokens e quase dois tercos dos
    pesos estao nessa tabela; um modelo que so le portugues usa uma fracao
    dela. Devolve ``(mapa, mantidos)``: ``mantidos`` sao os ids originais em
    ordem crescente (as linhas que ficam) e ``mapa[id]`` e a nova linha. Token
    descartado cai na linha do desconhecido, que sempre fica.
    """
    mantidos = sorted(set(ids_mantidos) | {id_desconhecido})
    if mantidos[0] < 0 or mantidos[-1] >= tamanho:
        raise ValueError("id mantido fora do vocabulario")
    nova_linha = {original: linha for linha, original in enumerate(mantidos)}
    desconhecido = nova_linha[id_desconhecido]
    return [nova_linha.get(original, desconhecido) for original in range(tamanho)], mantidos
