"""Conjunto conformal por classe (Mondrian) sobre o score 0-100 gravado.

Metodo (split conformal condicional ao rotulo). Para cada classe ``y``:

1. ordenam-se os ``n`` scores de calibracao dessa classe;
2. ``k_inf = floor((n + 1) * (1 - alvo) / 2)`` e
   ``k_sup = ceil((n + 1) * (1 - (1 - alvo) / 2))``;
3. ``inferior = s_(k_inf)`` se ``k_inf >= 1``, senao ``0.0``;
   ``superior = s_(k_sup)`` se ``k_sup <= n``, senao ``100.0``.

O conjunto de um score ``s`` e o das classes ``y`` com
``inferior_y <= s <= superior_y``. Sob permutabilidade entre o score novo e a
calibracao da mesma classe, ``P(S < inferior) <= (1 - alvo)/2`` e
``P(S > superior) <= (1 - alvo)/2``, logo a cobertura POR CLASSE e de pelo menos
``alvo``. A garantia nao vale sob mudanca de distribuicao (ver ``GARANTIA``).

Conjunto vazio ou com mais de uma classe e abstencao: o modulo apenas marca; o
score, a nota e a categoria gravados nao mudam.

Referencias: Vovk, Gammerman e Shafer, *Algorithmic Learning in a Random World*
(predicao Mondrian / condicional ao rotulo); Angelopoulos e Bates (2021),
*A Gentle Introduction to Conformal Prediction and Distribution-Free
Uncertainty Quantification*.
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

GARANTIA = (
    "cobertura de pelo menos {alvo} por classe, sob permutabilidade com o conjunto "
    "de calibração; não vale sob mudança de distribuição, e atendimento real é "
    "mudança de distribuição em relação ao holdout B2W (texto de resenha real, "
    "tempo sintético); o sinal de tempo do fusor foi treinado em dados sintéticos"
)

METODO = "conformal Mondrian por classe sobre o score 0-100"

# Guarda de ponto flutuante: 1 - 0.9 vale 0.09999999999999998, entao
# 20 * (1 - (1 - 0.9) / 2) da 19.000000000000004 e ceil daria 20 em vez de 19.
_EPS = 1e-9


class ConformalIndisponivel(RuntimeError):
    """Artefato ausente, malformado ou de outra regua: nao ha garantia a oferecer."""


def ajustar(scores_por_classe: dict[int, list[float]], alvo: float) -> dict[int, dict]:
    """Limites ``{"inferior", "superior", "n"}`` por classe a partir da calibracao."""
    if not 0.0 < alvo < 1.0:
        raise ValueError(f"alvo deve estar em (0, 1), recebido {alvo}")
    limites: dict[int, dict] = {}
    for classe, valores in scores_por_classe.items():
        n = len(valores)
        if n == 0:
            raise ValueError(
                f"classe {classe} sem exemplo na calibracao: nao existe garantia para ela"
            )
        ordem = sorted(float(v) for v in valores)
        k_inf = math.floor((n + 1) * (1 - alvo) / 2 + _EPS)
        k_sup = math.ceil((n + 1) * (1 - (1 - alvo) / 2) - _EPS)
        inferior = ordem[k_inf - 1] if k_inf >= 1 else 0.0
        superior = ordem[k_sup - 1] if k_sup <= n else 100.0
        limites[classe] = {"inferior": inferior, "superior": superior, "n": n}
    return limites


def conjunto(score: float, limites: dict[int, dict]) -> list[int]:
    """Classes cujo intervalo contem o score (bordas incluidas), em ordem."""
    return sorted(
        classe
        for classe, lim in limites.items()
        if lim["inferior"] <= score <= lim["superior"]
    )


def abstencao(conj: list[int]) -> str | None:
    """Criterio de abstencao do conjunto, ou ``None`` se for unitario."""
    if not conj:
        return "conjunto_vazio"
    if len(conj) > 1:
        return "conjunto_multiplo"
    return None


def dividir_estratificado(
    rotulos: list[int], fracao_calibracao: float, semente: int
) -> tuple[list[int], list[int]]:
    """Indices (calibracao, avaliacao) disjuntos, estratificados por rotulo."""
    sorteio = random.Random(semente)
    calibracao: list[int] = []
    avaliacao: list[int] = []
    for classe in sorted(set(rotulos)):
        indices = [i for i, r in enumerate(rotulos) if r == classe]
        sorteio.shuffle(indices)
        corte = round(len(indices) * fracao_calibracao)
        calibracao.extend(indices[:corte])
        avaliacao.extend(indices[corte:])
    return sorted(calibracao), sorted(avaliacao)


def serializar(
    limites: dict[int, dict], alvo: float, regua: str, semente: int, origem: str
) -> dict:
    """Artefato JSON-serializavel."""
    return {
        "versao": 1,
        "metodo": METODO,
        "alvo": alvo,
        "regua": regua,
        "semente": semente,
        "origem": origem,
        "limites": {str(classe): dict(lim) for classe, lim in limites.items()},
        "garantia": GARANTIA,
    }


def _validar(artefato: dict) -> None:
    """Confere o CONTEUDO: um JSON bem formado mas absurdo nao pode virar garantia."""
    if not 0.0 < artefato["alvo"] < 1.0:
        raise ConformalIndisponivel("artefato de calibração conformal malformado: alvo")
    if not isinstance(artefato["regua"], str) or not artefato["regua"]:
        raise ConformalIndisponivel("artefato de calibração conformal malformado: regua")
    limites = artefato["limites"]
    if set(limites) != {0, 1, 2}:
        raise ConformalIndisponivel("artefato de calibração conformal malformado: limites")
    for lim in limites.values():
        inf, sup = lim["inferior"], lim["superior"]
        if not (math.isfinite(inf) and math.isfinite(sup) and 0.0 <= inf <= sup <= 100.0):
            raise ConformalIndisponivel("artefato de calibração conformal malformado: limites")
        if lim["n"] < 1:
            raise ConformalIndisponivel("artefato de calibração conformal malformado: n")


def carregar_conformal(caminho: Path, regua_vigente: str | None) -> dict:
    """Le o artefato e confere a regua; qualquer falha vira ``ConformalIndisponivel``.

    As mensagens vao para o corpo do 503: nada de caminho absoluto nem repr.
    """
    try:
        path = Path(caminho)
        if not path.is_file():
            raise ConformalIndisponivel("artefato de calibração conformal ausente")
        bruto = json.loads(path.read_text(encoding="utf-8"))
        regua = bruto["regua"]
        artefato = {
            "versao": bruto["versao"],
            "metodo": bruto["metodo"],
            "alvo": float(bruto["alvo"]),
            "regua": regua,
            "semente": bruto["semente"],
            "origem": bruto["origem"],
            "limites": {
                int(classe): {
                    "inferior": float(lim["inferior"]),
                    "superior": float(lim["superior"]),
                    "n": int(lim["n"]),
                }
                for classe, lim in bruto["limites"].items()
            },
        }
    except ConformalIndisponivel:
        raise
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as erro:
        # json.JSONDecodeError e subclasse de ValueError.
        campo = erro.args[0] if isinstance(erro, KeyError) and erro.args else "conteúdo"
        raise ConformalIndisponivel(
            f"artefato de calibração conformal malformado: {campo}"
        ) from erro
    _validar(artefato)
    if regua != regua_vigente:
        raise ConformalIndisponivel("artefato calibrado para outra régua")
    artefato["garantia"] = GARANTIA.format(alvo=f"{round(artefato['alvo'] * 100)}%")
    return artefato
