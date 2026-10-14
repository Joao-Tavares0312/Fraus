"""Mede se as probabilidades do fusor merecem ser lidas como probabilidades.

Instrumento, nao botao: so imprime (e, com `--png`, desenha). ECE e MCE da
confianca maxima, ECE por classe, todos com IC de 95% por bootstrap, na metade
de avaliacao e no holdout inteiro; tabela de faixas; tabela por fatia. Se o
ECE passa de 0,05 e o IC nao cruza 0,05, imprime uma PROPOSTA de temperatura --
que nunca e aplicada: aplicar mudaria a regua e exigiria repontuar.

    uv run python scripts/medir_calibracao.py --cache features-fusor.json
    uv run --with matplotlib python scripts/medir_calibracao.py --cache features-fusor.json --png rel.png
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _confianca_comum import (CAMINHO_FUSOR_PADRAO, CLASSES,  # noqa: E402
                              carregar_fusor, carregar_holdout, condicoes,
                              exigir_todas_as_classes, preparar)
import numpy as np  # noqa: E402
from fraus.calibracao import bootstrap, ece, ece_por_classe, faixas, mce  # noqa: E402
from fraus.fatias import metricas_por_fatia  # noqa: E402

LIMIAR_ECE = 0.05
AVISO_VIES = "ECE binado é enviesado para cima em amostra pequena; o IC percentil pode não conter a estimativa"
AVISO_TEMPERATURA = "PROPOSTA — não aplicada; aplicar mudaria a régua e exigiria repontuar"


def fatias_das_features(f: dict[str, float]) -> dict[str, str]:
    """Os mesmos eixos e cortes de `fraus.fatias.fatias_de`, lidos das features.

    O cache guarda features, nao conversas, entao `fatias_de` nao pode ser
    chamada direto; os cortes sao os dela (falas 1/2-3/4+, latencia 30/180 s).
    """
    n = f["qtd_turnos_cliente"]
    m = f["latencia_mediana_s"]
    # Heuristica: `features_tempo` grava 0.0 quando nao ha latencia (mediana e
    # p90 ficam ambos 0), e `fatias_de` chama isso de "sem medida". Uma latencia
    # real de exatamente 0 s nos dois seria indistinguivel; o teste de paridade
    # com `fatias_de` fixa o resto.
    sem_medida = m == 0 and f["latencia_p90_s"] == 0
    return {
        "falas do cliente": "1" if n == 1 else "2-3" if n <= 3 else "4+",
        "latencia mediana": (
            "sem medida" if sem_medida
            else "<30 s" if m < 30 else "30-180 s" if m <= 180 else ">180 s"
        ),
        "emoji": "com" if f["emoji_contagem"] > 0 else "sem",
        "escalou para humano": "sim" if f["escalou"] else "nao",
    }


def temperar(probs: list[list[float]], temperatura: float) -> list[list[float]]:
    """softmax(log P / T). T=1 devolve as probabilidades originais."""
    saida = []
    for p in probs:
        logits = [math.log(max(v, 1e-12)) / temperatura for v in p]
        pico = max(logits)
        exps = [math.exp(v - pico) for v in logits]
        soma = sum(exps)
        saida.append([e / soma for e in exps])
    return saida


def ajustar_temperatura(probs: list[list[float]], rotulos: list[int]) -> float:
    """T que minimiza a log-loss (busca limitada em [0.05, 10])."""
    from scipy.optimize import minimize_scalar  # sklearn ja depende de scipy

    def perda(t: float) -> float:
        q = temperar(probs, t)
        return -sum(math.log(max(q[i][r], 1e-12)) for i, r in enumerate(rotulos)) / len(rotulos)

    return float(minimize_scalar(perda, bounds=(0.05, 10.0), method="bounded").x)


def _ic_da_classe(classe: int, probs, rotulos, reamostras: int):
    """IC95% e mediana do ECE da classe; reamostra sem a classe e NaN, nunca 0.

    Mais da metade das reamostras sem a classe -> None (IC indisponivel).
    """
    def da_classe(p, r):
        return ece_por_classe(p, r).get(classe, float("nan"))

    rng = np.random.default_rng(20261014)
    p_arr, r_arr = np.array(probs), np.array(rotulos)
    valores = []
    for _ in range(reamostras):
        idx = rng.integers(0, len(r_arr), size=len(r_arr))
        valores.append(da_classe(p_arr[idx].tolist(), r_arr[idx].tolist()))
    valores = np.array(valores)
    if np.isnan(valores).mean() > 0.5:
        return None
    return (
        float(np.nanpercentile(valores, 2.5)),
        float(np.nanpercentile(valores, 97.5)),
        float(np.nanmedian(valores)),
    )


def medir(probs: list[list[float]], rotulos: list[int], reamostras: int = 1000) -> dict:
    """ECE, MCE e ECE por classe, cada um com (estimativa, IC)."""
    saida = {
        "ece": (ece(probs, rotulos), bootstrap(ece, probs, rotulos, reamostras, com_mediana=True)),
        "mce": (mce(probs, rotulos), bootstrap(mce, probs, rotulos, reamostras, com_mediana=True)),
    }
    por_classe = ece_por_classe(probs, rotulos)
    for c in CLASSES:
        saida[f"ece_classe_{c}"] = (por_classe[c], _ic_da_classe(c, probs, rotulos, reamostras))
    return saida


def propor_temperatura(medidas: dict) -> bool:
    """Ha motivo para propor? ECE acima do limiar e IC inteiro acima dele."""
    estimativa, (inferior, *_) = medidas["ece"]
    return estimativa > LIMIAR_ECE and inferior > LIMIAR_ECE


def reliability_png(probs: list[list[float]], rotulos: list[int], caminho: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as erro:
        raise SystemExit(
            "matplotlib não está instalado: rode com `uv run --with matplotlib` "
            "(não é dependência do projeto)."
        ) from erro
    pontos = [(f["confianca_media"], f["acuracia"]) for f in faixas(probs, rotulos) if f["n"]]
    fig, eixo = plt.subplots(figsize=(4.5, 4.5))
    eixo.plot([0, 1], [0, 1], "--", color="gray", label="calibração perfeita")
    eixo.plot([p[0] for p in pontos], [p[1] for p in pontos], "o-", label="fusor")
    eixo.set_xlabel("confiança máxima")
    eixo.set_ylabel("acurácia")
    eixo.legend()
    fig.tight_layout()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(caminho, dpi=150)
    plt.close(fig)


MINIMO_ECE_FATIA = 5


def texto_ece(probs: list[list[float]], rotulos: list[int]) -> str:
    """ECE (confianca maxima) da fatia; abaixo de 5 exemplos e "n/d", nunca 0."""
    if len(rotulos) < MINIMO_ECE_FATIA:
        return "n/d"
    return f"{ece(probs, rotulos):.3f}"


def _imprimir_medidas(titulo: str, probs: list[list[float]], rotulos: list[int]) -> dict:
    m = medir(probs, rotulos)
    print(f"\n{titulo} (n={len(rotulos)})")
    for nome, (valor, ic) in m.items():
        if ic is None:
            print(f"  {nome:<14} {valor:.4f}  IC indisponível (classe rara nesta metade)")
            continue
        lo, hi, mediana = ic
        print(f"  {nome:<14} {valor:.4f}  IC95% [{lo:.4f}, {hi:.4f}]  mediana bootstrap {mediana:.4f}")
    print("  " + AVISO_VIES)
    return m


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cache", type=Path, required=True)
    ap.add_argument("--fusor", type=Path, default=CAMINHO_FUSOR_PADRAO)
    ap.add_argument("--png", type=Path, default=None, help="reliability diagram da avaliação")
    args = ap.parse_args(argv)

    fusor = carregar_fusor(args.fusor)
    xe, ye = carregar_holdout(args.cache)
    p = preparar(fusor, xe, ye)
    ava, cal = p["ava"], p["cal"]
    for nome, indices in (("avaliação", ava), ("calibração", cal)):
        exigir_todas_as_classes(
            {c: [i for i in indices if ye[i] == c] for c in CLASSES}, metade=nome
        )
    probs_ava, y_ava = [p["probs"][i] for i in ava], [ye[i] for i in ava]
    probs_cal, y_cal = [p["probs"][i] for i in cal], [ye[i] for i in cal]

    print(condicoes(p["regua"], len(ye)))
    medidas_ava = _imprimir_medidas("Metade de avaliação", probs_ava, y_ava)
    _imprimir_medidas("Holdout inteiro", p["probs"], ye)

    print("\nFaixas de confiança (avaliação)")
    print("  faixa         n   confiança  acurácia")
    for f in faixas(probs_ava, y_ava):
        if f["n"]:
            print(f"  {f['inferior']:.1f}-{f['superior']:.1f}  {f['n']:>5}   {f['confianca_media']:.3f}     {f['acuracia']:.3f}")

    fatias = {i: fatias_das_features(xe[i]) for i in ava}
    registros = [
        (fatias[i], ye[i], max(range(3), key=lambda c: p["probs"][i][c])) for i in ava
    ]
    print("\nPor fatia (avaliação)")
    for eixo, valores in metricas_por_fatia(registros).items():
        for valor, m in valores.items():
            idx = [i for i in ava if fatias[i][eixo] == valor]
            e = texto_ece([p["probs"][i] for i in idx], [ye[i] for i in idx])
            print(f"  {eixo:<20} {valor:<10} n={m['n']:>4}  acurácia {m['acuracia']:.3f}  F1-macro {m['f1_macro']:.3f}  ECE {e}")

    if args.png:
        reliability_png(probs_ava, y_ava, args.png)
        print(f"\nReliability diagram em {args.png}")

    if propor_temperatura(medidas_ava):
        t = ajustar_temperatura(probs_cal, y_cal)
        depois = ece(temperar(probs_ava, t), y_ava)
        print(f"\nTemperatura T={t:.3f} (ajustada na calibração); ECE na avaliação {medidas_ava['ece'][0]:.4f} -> {depois:.4f}")
        print(f"Critério: ECE > {LIMIAR_ECE} e limite inferior do IC > {LIMIAR_ECE}; o IC herda o viés do ECE binado (ver aviso acima).")
        print(AVISO_TEMPERATURA)
    else:
        print(f"\nECE não excede {LIMIAR_ECE} com IC acima do limiar: nenhuma temperatura proposta.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
