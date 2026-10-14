"""Partes comuns dos tres instrumentos de confianca (calibracao, abstencao, conformal).

Nao e um script: so reune o que os tres repetiriam -- ler o cache, carregar o
fusor FALHANDO ALTO, dividir o holdout e obter as probabilidades. Nenhum
instrumento escreve nada alem do que o seu proprio `--gravar` declara.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from fraus.conformal import dividir_estratificado  # noqa: E402
from fraus.fusor import Fusor, vetorizar  # noqa: E402
from fraus.motor import regua_do_fusor  # noqa: E402

CAMINHO_FUSOR_PADRAO = RAIZ / "modelos" / "fusor.joblib"
SEMENTE_DIVISAO = 20261014
CLASSES = (0, 1, 2)


def condicoes(regua: str | None, n: int) -> str:
    """A linha que acompanha toda saida: sem ela o numero nao se interpreta."""
    return (
        f"holdout B2W n={n} (semente 999) → {n // 2} calibração / {n - n // 2} avaliação "
        f"(semente {SEMENTE_DIVISAO}); tempo sintético; fusor {regua}"
    )


def carregar_fusor(caminho: Path) -> Fusor:
    """`Fusor.carregar` ou SystemExit nao zero. Nunca ha fusor substituto."""
    try:
        return Fusor.carregar(caminho)
    except Exception as erro:  # arquivo ausente, joblib ilegivel, incompativel
        raise SystemExit(
            f"fusor indisponível em {caminho}: {type(erro).__name__}: {erro}\n"
            "Sem fusor vigente não há o que medir (invariante 7); não há substituto."
        ) from erro


def carregar_holdout(caminho: Path) -> tuple[list[dict], list[int]]:
    """So `xe`/`ye`. `xt` e o treino e nunca entra."""
    try:
        dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
        return list(dados["xe"]), [int(r) for r in dados["ye"]]
    except (OSError, ValueError, KeyError) as erro:
        raise SystemExit(f"cache ilegível em {caminho}: {erro}") from erro


def probabilidades(fusor: Fusor, features: dict[str, float]) -> list[float]:
    """[P(0), P(1), P(2)] -- a ordem das classes e a da invariante 8."""
    pipeline = fusor._pipeline
    valores = pipeline.predict_proba([vetorizar(features)])[0]
    classes = [int(c) for c in pipeline.named_steps["modelo"].classes_]
    por_classe = dict(zip(classes, (float(v) for v in valores)))
    return [por_classe.get(c, 0.0) for c in CLASSES]


def preparar(fusor: Fusor, xe: list[dict], ye: list[int]) -> dict:
    """Scores, probabilidades e a divisao calibracao/avaliacao do holdout."""
    if len(xe) != len(ye) or not xe:
        raise SystemExit("holdout vazio ou com xe/ye de tamanhos diferentes")
    cal, ava = dividir_estratificado(ye, 0.5, semente=SEMENTE_DIVISAO)
    return {
        "scores": [fusor.pontuar(x) for x in xe],
        "probs": [probabilidades(fusor, x) for x in xe],
        "cal": cal,
        "ava": ava,
        "regua": regua_do_fusor(fusor),
    }


def scores_por_classe(scores: list[float], rotulos: list[int], indices: list[int]) -> dict[int, list[float]]:
    """Scores de calibracao agrupados por rotulo, com TODAS as classes presentes."""
    saida: dict[int, list[float]] = {c: [] for c in CLASSES}
    for i in indices:
        saida.setdefault(rotulos[i], []).append(scores[i])
    return saida


# Escolha sem procedencia: 5 exemplos por classe e por metade. Abaixo disso o
# limite conformal e o ECE por classe dependem de um punhado de pontos.
MINIMO_POR_CLASSE = 5


def exigir_todas_as_classes(
    grupos: dict[int, list], metade: str = "calibração", minimo: int = MINIMO_POR_CLASSE
) -> None:
    """Sem `minimo` exemplos de cada classe na metade nao ha o que afirmar por classe."""
    faltando = {c: len(grupos.get(c, [])) for c in CLASSES if len(grupos.get(c, [])) < minimo}
    if faltando:
        raise SystemExit(
            f"classe(s) com menos de {minimo} exemplos na metade de {metade} "
            f"(classe: n = {faltando}): não existe garantia nem medida confiável para elas; "
            "nada foi ajustado."
        )
