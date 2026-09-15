"""Mede as saidas do P0 do tempo -- teto, log, os dois -- SEM promover nenhuma.

`scripts/medir_dominio_do_tempo.py` mostrou o defeito: o relogio empata com o
texto em ~411 s e manda sozinho dali em diante, sem teto. `docs/treinamento.md`
(secao 10 do notebook 02) descreve o conserto e o acoplamento que o torna
indivisivel. Este instrumento responde a pergunta que faltava para DECIDIR: o
que cada saida faz com a acuracia, com a categoria das conversas e com o caso
canonico.

Ele REPRODUZ o notebook 02 localmente -- mesmo B2W, mesmo balanceamento, mesmas
sementes, mesmo `montar_features` -- e confere a reproducao contra o artefato
vigente antes de acreditar em qualquer outro numero (em 15/09/2026: acuracia
0,9500 nos dois, score diferindo no maximo 0,0001). Instrumento, nao botao:
nunca escreve em `modelos/`.

A extracao (1.200 conversas pelas cabecas) e o caro, ~10 min em CPU com ONNX,
entao as features ficam em cache no `--cache`. A segunda rodada leva segundos.

    FRAUS_BACKEND=onnx uv run --with pandas python scripts/medir_compressao_do_tempo.py \\
        --b2w B2W-Reviews01.csv --cache features-fusor.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from fraus.api.caminhos import CAMINHO_FUSOR, backend_declarado  # noqa: E402
from fraus.api.main import montar_classificadores  # noqa: E402
from fraus.fusor import NOMES_FEATURES, Fusor, montar_features  # noqa: E402
from fraus.indicadores import categoria_nps, nota_0_10  # noqa: E402
from fraus.ingest.simulador import gerar_lote  # noqa: E402

URL_B2W = "https://raw.githubusercontent.com/americanas-tech/b2w-reviews01/main/B2W-Reviews01.csv"
TEMPO = ("latencia_mediana_s", "latencia_p90_s", "latencia_primeira_resposta_s", "duracao_total_s")
# A frase canonica le 0,858 de satisfeito na cabeca de texto (medido em 08/09).
PROB_CANONICA = 0.858
ESPERAS_S = (60, 300, 600, 1800, 10800)


def _extrair(b2w: str) -> dict:
    """Celulas 3-5 do notebook 02, sem redigitar regra nenhuma de feature."""
    import pandas as pd

    dados = pd.read_csv(b2w, low_memory=False)
    dados = dados[["review_text", "overall_rating", "recommend_to_a_friend"]].dropna()
    dados = dados.rename(columns={"review_text": "texto"})
    dados["recomenda"] = dados["recommend_to_a_friend"].str.strip().str.lower()
    dados = dados[dados["recomenda"].isin(["yes", "no"])]
    dados["rotulo"] = [
        1 if nota == 3 else 2 if rec == "yes" else 0
        for nota, rec in zip(dados["overall_rating"], dados["recomenda"])
    ]
    menor = dados["rotulo"].value_counts().min()
    # `concat` e nao `groupby.apply`: o pandas 3 tira a coluna do grupo de
    # dentro do apply. Mesma ordem de grupos, mesmas sementes do notebook.
    dados = (
        pd.concat([g.sample(menor, random_state=42) for _, g in dados.groupby("rotulo")])
        .sample(frac=1, random_state=42)
        .reset_index(drop=True)
    )

    def frases(rotulo, inicio, fim):
        textos = dados[dados["rotulo"] == rotulo]["texto"].tolist()[inicio:fim]
        return [t.strip() for t in textos if t and t.strip()]

    corte = 400 * 3 // 4
    treino = gerar_lote({r: frases(r, 0, corte) for r in (0, 1, 2)}, quantidade=900, semente=20260813)
    teste = gerar_lote({r: frases(r, corte, 400) for r in (0, 1, 2)}, quantidade=300, semente=999)
    texto, emocao, _ironia = montar_classificadores(backend_declarado())

    def vetores(lote):
        return [montar_features(c, texto, emocao) for c, _ in lote], [r for _, r in lote]

    xt, yt = vetores(treino)
    xe, ye = vetores(teste)
    return {"xt": xt, "yt": yt, "xe": xe, "ye": ye}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--b2w", default=URL_B2W)
    ap.add_argument("--cache", type=Path, required=True)
    args = ap.parse_args()

    if args.cache.exists():
        dados = json.loads(args.cache.read_text())
    else:
        dados = _extrair(args.b2w)
        args.cache.write_text(json.dumps(dados))
    xt, yt, xe, ye = dados["xt"], dados["yt"], dados["xe"], dados["ye"]

    import numpy as np
    from sklearn.metrics import accuracy_score, f1_score

    p99 = {n: float(np.percentile([e[n] for e in xt], 99)) for n in TEMPO}
    variantes = {
        "vigente": None,
        "so log1p": lambda e: {**e, **{n: math.log1p(max(e[n], 0.0)) for n in TEMPO}},
        "so teto p99": lambda e: {**e, **{n: min(e[n], p99[n]) for n in TEMPO}},
        "p99+log1p": lambda e: {**e, **{n: math.log1p(min(max(e[n], 0.0), p99[n])) for n in TEMPO}},
    }

    vigente = Fusor.carregar(CAMINHO_FUSOR)
    reproducao = Fusor()
    reproducao.treinar(xt, yt)
    desvio = max(abs(vigente.pontuar(e) - reproducao.pontuar(e)) for e in xe)
    print(f"reproducao do artefato vigente: max |score| = {desvio:.4f}")
    if desvio > 0.01:
        print("A REPRODUCAO NAO BATE -- os numeros abaixo nao comparam com o artefato.")
        return 1

    media = dict(zip(NOMES_FEATURES, vigente._pipeline.named_steps["escala"].mean_))
    print(f"teto p99 do treino (s): { {k: round(v) for k, v in p99.items()} }\n")
    print(f"| variante | acurácia | F1 | categorias ≠ vigente (de {len(xe)}) | "
          + " | ".join(f"{s} s" for s in ESPERAS_S) + " |")
    print("|---" * (4 + len(ESPERAS_S)) + "|")
    for nome, t in variantes.items():
        t = t or (lambda e: e)
        fusor = vigente
        if nome != "vigente":
            fusor = Fusor()
            fusor.treinar([t(e) for e in xt], yt)
        preditos = [fusor.prever(t(e)) for e in xe]
        trocas = sum(categoria_nps(vigente.pontuar(e)) != categoria_nps(fusor.pontuar(t(e))) for e in xe)
        casos = []
        for espera in ESPERAS_S:
            e = dict(media)
            e["texto_prob_satisfeito_media"] = PROB_CANONICA
            for n in TEMPO:
                e[n] = float(espera)
            e["duracao_total_s"] = espera + 30.0
            s = fusor.pontuar(t(e))
            casos.append(f"{s:.1f} ({nota_0_10(s)}, {categoria_nps(s)})")
        print(f"| {nome} | {accuracy_score(ye, preditos):.4f} | {f1_score(ye, preditos, average='macro'):.4f} "
              f"| {trocas} | " + " | ".join(casos) + " |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
