"""Retreina o fusor LOCALMENTE, reproduzindo o notebook 02, e so grava com --promover.

POR QUE EXISTE. O notebook 02 roda no Colab, mas nao treina nada pesado: os
BERTimbau ja existem e so extraem features, e o que treina e uma
`LogisticRegression`. Em CPU com `FRAUS_BACKEND=onnx` a extracao das 1.200
conversas leva ~10 min -- e isso tornou possivel MEDIR uma mudanca de feature
antes de decidir, em vez de ir e voltar do Colab.

A HISTORIA DELE. Nasceu em 15/09/2026 como `medir_compressao_do_tempo.py`, que
comparou as tres saidas do P0 do tempo (teto p99, log1p, os dois) contra o
fusor vigente reproduzido -- a tabela esta em `docs/treinamento.md`. A escolha
foi `log1p`, que agora mora em `fraus.fusor.vetorizar`; as variantes deixaram de
fazer sentido aqui, e o instrumento virou a ferramenta de retreino.

O QUE ELE CONFERE ANTES DE GRAVAR:

1. o mesmo B2W, balanceamento, sementes e `montar_features` do notebook -- a
   regra de feature nao e redigitada;
2. acuracia e F1-macro no conjunto de teste disjunto;
3. quantas CATEGORIAS mudam contra o artefato em disco, que pode ser de uma
   escala anterior (lido cru, sem a recusa de `Fusor.carregar`, so para medir).

Sem `--promover` nao escreve nada. Com ele, guarda o artefato anterior ao lado
(`fusor.joblib.bak-<escala>`) e grava `fusor.joblib` e `importancias.json`.

    FRAUS_BACKEND=onnx uv run --with pandas python scripts/retreinar_fusor_local.py \\
        --cache features-fusor.json [--promover]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from fraus.api.caminhos import CAMINHO_FUSOR, backend_declarado  # noqa: E402
from fraus.api.main import montar_classificadores  # noqa: E402
from fraus.fusor import (ESCALA_DO_TEMPO, NOMES_FEATURES,  # noqa: E402
                         PESO_NEUTRO_NO_SCORE, Fusor, montar_features, vetorizar)
from fraus.indicadores import categoria_nps, nota_0_10  # noqa: E402
from fraus.ingest.simulador import gerar_lote  # noqa: E402

URL_B2W = "https://raw.githubusercontent.com/americanas-tech/b2w-reviews01/main/B2W-Reviews01.csv"


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
    ap.add_argument("--promover", action="store_true", help="grava modelos/fusor.joblib")
    args = ap.parse_args()

    if args.cache.exists():
        dados = json.loads(args.cache.read_text())
    else:
        dados = _extrair(args.b2w)
        args.cache.write_text(json.dumps(dados))
    xt, yt, xe, ye = dados["xt"], dados["yt"], dados["xe"], dados["ye"]

    import joblib
    from sklearn.metrics import accuracy_score, f1_score

    novo = Fusor()
    novo.treinar(xt, yt)
    preditos = [novo.prever(e) for e in xe]
    acuracia = accuracy_score(ye, preditos)
    f1 = f1_score(ye, preditos, average="macro")
    print(f"novo fusor (espera em {ESCALA_DO_TEMPO}): acuracia {acuracia:.4f}  F1-macro {f1:.4f}")

    anterior = None
    if CAMINHO_FUSOR.exists():
        pipeline = joblib.load(CAMINHO_FUSOR)
        escala = getattr(pipeline, "fraus_escala_do_tempo", "segundos")

        def score_anterior(features):
            vetor = [float(features[n]) for n in NOMES_FEATURES] if escala == "segundos" else vetorizar(features)
            classes = list(pipeline.named_steps["modelo"].classes_)
            p = dict(zip(classes, pipeline.predict_proba([vetor])[0]))
            return 100.0 * (p.get(2, 0.0) + PESO_NEUTRO_NO_SCORE * p.get(1, 0.0))

        trocas = sum(categoria_nps(score_anterior(e)) != categoria_nps(novo.pontuar(e)) for e in xe)
        notas = sum(nota_0_10(score_anterior(e)) != nota_0_10(novo.pontuar(e)) for e in xe)
        print(f"contra o artefato em disco (escala '{escala}'): {notas} notas e "
              f"{trocas} categorias diferentes em {len(xe)} conversas de teste")
        anterior = escala

    if not args.promover:
        print("\nnada gravado (use --promover).")
        return 0

    if anterior is not None:
        copia = CAMINHO_FUSOR.with_name(f"{CAMINHO_FUSOR.name}.bak-{anterior}")
        CAMINHO_FUSOR.replace(copia)
        print(f"anterior guardado em {copia}")
    novo.salvar(CAMINHO_FUSOR)
    importancias = CAMINHO_FUSOR.with_name("importancias.json")
    importancias.write_text(json.dumps({
        "importancias": novo.importancias(),
        "acuracia": float(acuracia),
        "f1_macro": float(f1),
        "conversas_treino": len(xt),
        "conversas_teste": len(xe),
        "escala_do_tempo": ESCALA_DO_TEMPO,
        "rotulo": "recommend_to_a_friend (Yes/No) + overall_rating == 3 para o neutro",
        "classes": ["insatisfeito", "neutro", "satisfeito"],
        "origem": "scripts/retreinar_fusor_local.py (reproducao local do notebook 02)",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"gravado {CAMINHO_FUSOR} e {importancias}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
