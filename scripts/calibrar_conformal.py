"""Ajusta os limites conformais por classe e, so com --gravar, escreve o artefato.

Instrumento, nao botao: sem `--gravar` apenas imprime. Ajusta na METADADE DE
CALIBRACAO do holdout B2W (`xe`/`ye` do cache; `xt` e treino e nunca entra) e
mede cobertura e tamanho do conjunto na metade de avaliacao. O artefato gravado
e atrelado a regua do fusor: trocou o fusor, o artefato deixa de valer.

    uv run python scripts/calibrar_conformal.py --cache features-fusor.json
    uv run python scripts/calibrar_conformal.py --cache features-fusor.json --alvo 0.9 --gravar
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _confianca_comum import (CAMINHO_FUSOR_PADRAO, CLASSES, RAIZ,  # noqa: E402
                              SEMENTE_DIVISAO, carregar_fusor, carregar_holdout,
                              condicoes, exigir_todas_as_classes, preparar,
                              scores_por_classe)
from fraus.conformal import GARANTIA, ajustar, conjunto, serializar  # noqa: E402

SAIDA_PADRAO = RAIZ / "fraus" / "dados" / "conformal_fusor.json"
ORIGEM = "holdout B2W semente 999, metade de calibracao semente 20261014"


def medir_cobertura(limites: dict, scores: list[float], rotulos: list[int], indices: list[int]) -> dict:
    """Cobertura geral e por classe e tamanho medio do conjunto nos `indices`."""
    por_classe = {c: [0, 0] for c in CLASSES}
    tamanhos = []
    for i in indices:
        conj = conjunto(scores[i], limites)
        tamanhos.append(len(conj))
        por_classe[rotulos[i]][0] += rotulos[i] in conj
        por_classe[rotulos[i]][1] += 1
    cobertos = sum(c for c, _ in por_classe.values())
    return {
        "cobertura": cobertos / len(indices),
        "cobertura_por_classe": {c: (a / n if n else None) for c, (a, n) in por_classe.items()},
        "n_por_classe": {c: n for c, (_, n) in por_classe.items()},
        "tamanho_medio": sum(tamanhos) / len(tamanhos),
    }


def calibrar(preparado: dict, rotulos: list[int], alvo: float) -> tuple[dict, dict]:
    """(limites, medida na avaliacao). Recusa se faltar classe na calibracao."""
    grupos = scores_por_classe(preparado["scores"], rotulos, preparado["cal"])
    exigir_todas_as_classes(grupos, metade="calibração")
    limites = ajustar(grupos, alvo)
    return limites, medir_cobertura(limites, preparado["scores"], rotulos, preparado["ava"])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cache", type=Path, required=True)
    ap.add_argument("--fusor", type=Path, default=CAMINHO_FUSOR_PADRAO)
    ap.add_argument("--alvo", type=float, default=0.9)
    ap.add_argument("--gravar", action="store_true", help="escreve o artefato (único efeito colateral)")
    ap.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    args = ap.parse_args(argv)
    if not 0.0 < args.alvo < 1.0:
        ap.error("--alvo deve estar em (0, 1)")

    fusor = carregar_fusor(args.fusor)
    xe, ye = carregar_holdout(args.cache)
    preparado = preparar(fusor, xe, ye)
    limites, medida = calibrar(preparado, ye, args.alvo)

    print(condicoes(preparado["regua"], len(ye)))
    print(f"alvo {args.alvo:.2f}  |  garantia: {GARANTIA.format(alvo=args.alvo)}\n")
    print("classe  n(cal)  inferior  superior")
    for c in CLASSES:
        lim = limites[c]
        print(f"{c:>6}  {lim['n']:>6}  {lim['inferior']:>8.2f}  {lim['superior']:>8.2f}")
    print("\nNa metade de avaliação:")
    print(f"  cobertura geral {medida['cobertura']:.3f}  |  tamanho médio do conjunto {medida['tamanho_medio']:.2f}")
    for c in CLASSES:
        cob = medida["cobertura_por_classe"][c]
        texto = "sem exemplo" if cob is None else f"{cob:.3f}"
        print(f"  classe {c}: cobertura {texto} (n={medida['n_por_classe'][c]})")

    if not args.gravar:
        print("\nNada gravado (use --gravar para escrever o artefato).")
        return 0
    if preparado["regua"] is None:
        raise SystemExit("fusor sem régua: o artefato não teria a que se atrelar")
    artefato = serializar(limites, args.alvo, preparado["regua"], SEMENTE_DIVISAO, ORIGEM)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(json.dumps(artefato, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nArtefato gravado em {args.saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
