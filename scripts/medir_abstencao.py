"""Mede cobertura, abstencao e risco x cobertura do conjunto conformal.

Instrumento, nao botao: so imprime. Para cada `alvo` ajusta na metade de
calibracao do holdout B2W e mede na de avaliacao. A "abstencao" aqui e a
marca do conjunto (vazio ou multiplo); o score e a nota gravados nao mudam.
O ponto de operacao e 0,90.

    uv run python scripts/medir_abstencao.py --cache features-fusor.json
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _confianca_comum import (CAMINHO_FUSOR_PADRAO, CLASSES,  # noqa: E402
                              carregar_fusor, carregar_holdout, condicoes,
                              exigir_todas_as_classes, preparar,
                              scores_por_classe)
from fraus.conformal import GARANTIA, ajustar, abstencao, conjunto  # noqa: E402

ALVOS = (0.80, 0.85, 0.90, 0.95)
PONTO_DE_OPERACAO = 0.90


def tolerancia_binomial(alvo: float, n: int) -> float:
    """2*sqrt(alvo(1-alvo)/n): quanto a cobertura medida pode fugir do alvo so por amostra."""
    return 2.0 * math.sqrt(alvo * (1 - alvo) / n)


def medir_alvo(preparado: dict, rotulos: list[int], alvo: float) -> dict:
    grupos = scores_por_classe(preparado["scores"], rotulos, preparado["cal"])
    exigir_todas_as_classes(grupos)
    limites = ajustar(grupos, alvo)
    ava = preparado["ava"]
    por_classe = {c: [0, 0] for c in CLASSES}
    tamanhos, abstidas, nao_abstidas_acertos, nao_abstidas = [], 0, 0, 0
    for i in ava:
        conj = conjunto(preparado["scores"][i], limites)
        tamanhos.append(len(conj))
        por_classe[rotulos[i]][0] += rotulos[i] in conj
        por_classe[rotulos[i]][1] += 1
        if abstencao(conj) is not None:
            abstidas += 1
            continue
        nao_abstidas += 1
        probs = preparado["probs"][i]
        nao_abstidas_acertos += max(range(3), key=lambda c: probs[c]) == rotulos[i]
    n = len(ava)
    return {
        "alvo": alvo,
        "n": n,
        "cobertura": sum(a for a, _ in por_classe.values()) / n,
        "cobertura_por_classe": {c: (a / t if t else None) for c, (a, t) in por_classe.items()},
        "tamanho_medio": sum(tamanhos) / n,
        "abstencao": abstidas / n,
        "cobertura_de_conversas": nao_abstidas / n,
        "acuracia_nao_abstidas": (nao_abstidas_acertos / nao_abstidas) if nao_abstidas else None,
        "tolerancia": tolerancia_binomial(alvo, n),
    }


def curva_risco_cobertura(preparado: dict, rotulos: list[int]) -> list[tuple[float, float]]:
    """(fracao retida, risco) retendo as conversas de maior confianca maxima primeiro."""
    ava = preparado["ava"]
    ordem = sorted(ava, key=lambda i: -max(preparado["probs"][i]))
    pontos, erros = [], 0
    for k, i in enumerate(ordem, start=1):
        probs = preparado["probs"][i]
        erros += max(range(3), key=lambda c: probs[c]) != rotulos[i]
        if k % max(1, len(ordem) // 10) == 0 or k == len(ordem):
            pontos.append((k / len(ordem), erros / k))
    return pontos


def _fmt(valor: float | None) -> str:
    return "  n/d" if valor is None else f"{valor:.3f}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cache", type=Path, required=True)
    ap.add_argument("--fusor", type=Path, default=CAMINHO_FUSOR_PADRAO)
    args = ap.parse_args(argv)

    fusor = carregar_fusor(args.fusor)
    xe, ye = carregar_holdout(args.cache)
    preparado = preparar(fusor, xe, ye)

    print(condicoes(preparado["regua"], len(ye)))
    print(f"garantia: {GARANTIA.format(alvo='(alvo)')}\n")
    print("alvo   cobert.  c0     c1     c2     tam.   abst.  acur.(não abst.)  tol.±")
    for alvo in ALVOS:
        m = medir_alvo(preparado, ye, alvo)
        marca = "  <- ponto de operação" if alvo == PONTO_DE_OPERACAO else ""
        c = m["cobertura_por_classe"]
        print(
            f"{alvo:.2f}   {m['cobertura']:.3f}   {_fmt(c[0])} {_fmt(c[1])} {_fmt(c[2])}  "
            f"{m['tamanho_medio']:.2f}   {m['abstencao']:.3f}   {_fmt(m['acuracia_nao_abstidas'])}"
            f"             {m['tolerancia']:.3f}{marca}"
        )
    print("\nRisco x cobertura (conversas retidas por confiança máxima decrescente):")
    print("retidas  risco")
    for fracao, risco in curva_risco_cobertura(preparado, ye):
        print(f"{fracao:>7.2f}  {risco:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
