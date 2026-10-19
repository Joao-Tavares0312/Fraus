"""Benchmark local e congelado das tres cabecas (satisfacao, emocao, ironia), em CPU.

Ate 19/10/2026 a unica comparacao pareada morava DENTRO do notebook 07 e so
cobria emocao e ironia. Aqui ela vira um script local, que le os corpora pelo
mesmo `fraus.corpora` + `fraus.receita_treino.preparar_divisao` que os
notebooks usam -- e por isso chega ao mesmo teste, conferido pela impressao.

Uso:

    uv run python scripts/benchmark_motores.py satisfacao \\
        --modelo bertimbau=../Fraus/modelos/bertimbau-satisfacao \\
        [--modelo candidato=caminho/do/candidato] \\
        [--amostra 4000] --saida fraus/dados/benchmark_satisfacao.json

Com um modelo so, mede a linha de base. Com dois, o primeiro e a referencia e
o segundo o candidato, e cada conjunto ganha a comparacao pareada (McNemar +
IC da diferenca de F1-macro por bootstrap, de `fraus.comparacao_modelos`).

Os corpora sao baixados uma vez para `~/.cache/fraus/corpora` (fora do git).
Nada aqui grava modelo, chama a API ou toca o banco.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from fraus import corpora  # noqa: E402
from fraus.avaliacao_ironia import IRONIAS_SEM_MARCADOR, SINCERAS_COM_MARCADOR  # noqa: E402
from fraus.comparacao_modelos import avaliar_conjunto  # noqa: E402
from fraus.divisao import impressao_dos_textos  # noqa: E402
from fraus.receita_treino import (  # noqa: E402
    amostra_estratificada,
    metricas_completas,
    preparar_divisao,
)

CACHE = Path.home() / ".cache" / "fraus" / "corpora"
SCHEMA = 1


def baixar(url: str, destino: Path) -> Path:
    if not destino.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        provisorio = destino.with_suffix(destino.suffix + ".parcial")
        print(f"baixando {url}", file=sys.stderr)
        urllib.request.urlretrieve(url, provisorio)
        provisorio.rename(destino)
    return destino


# --- conjuntos por tarefa -------------------------------------------------------
#
# Cada conjunto: id, nome, independente, Exemplos e ressalvas. "Independente"
# quer dizer que NENHUM modelo comparado viu dado daquela procedencia no
# treino; a linha de base ja treinada so e comparavel de fato nos independentes.

_RESSALVA_INTERNO_ANTIGO = (
    "O teste interno vem da divisao nova (sem duplicatas, agrupada, 19/10/2026). "
    "Os modelos treinados ANTES dessa data usaram outra divisao do mesmo corpus "
    "e podem ter visto parte deste teste no treino: para eles, o numero e otimista."
)


def conjuntos_satisfacao(amostra: int | None) -> list[dict]:
    b2w = corpora.ler_b2w(baixar(corpora.URL_B2W, CACHE / "b2w" / "B2W-Reviews01.csv"))
    teste_b2w = preparar_divisao(b2w)["teste"]
    saida = [{
        "id": "satisfacao_b2w", "nome": "B2W-Reviews01, teste interno", "independente": False,
        "exemplos": teste_b2w, "ressalvas": [_RESSALVA_INTERNO_ANTIGO],
    }]
    zip_consumerbr = CACHE / "consumerbr" / "ConsumerBR.zip"
    if zip_consumerbr.exists():
        # Empresa grande (banco, operadora) tem dezenas de milhares de linhas:
        # agrupar por empresa nao cabe em 15%. Divisao estratificada.
        consumerbr = corpora.ler_consumerbr(zip_consumerbr)
        teste_cbr = preparar_divisao(consumerbr, agrupar=False)["teste"]
        saida.append({
            "id": "satisfacao_consumerbr",
            "nome": "ConsumerBR, comentario da avaliacao (atendimento)",
            "independente": True, "exemplos": teste_cbr,
            "ressalvas": [
                "Rotulo = nota 1-5 que o consumidor deu ao desfecho, com o comentario "
                "escrito junto. Independente para modelo treinado so em B2W; deixa de "
                "ser para o candidato treinado com o ConsumerBR (a divisao e a mesma, "
                "entao o teste continua disjunto do treino)."
            ],
        })
    else:
        print(f"AVISO: {zip_consumerbr} ausente -- baixe {corpora.URL_CONSUMERBR}",
              file=sys.stderr)
    return _amostrar(saida, amostra)


def conjuntos_emocao(amostra: int | None) -> list[dict]:
    caminhos = [
        baixar(corpora.URL_GOEMOTIONS_PTBR.format(i), CACHE / "goemotions" / f"goemotions_{i}_pt.csv")
        for i in (1, 2, 3)
    ]
    mapa = json.loads(baixar(corpora.URL_EKMAN, CACHE / "goemotions" / "ekman_mapping.json")
                      .read_text(encoding="utf-8"))
    teste_ge = preparar_divisao(corpora.ler_goemotions_ptbr(caminhos, mapa))["teste"]
    xed = corpora.ler_xed_pt(baixar(corpora.URL_XED_PT, CACHE / "xed" / "pt-projections.tsv"))
    saida = [
        {"id": "emocao_goemotions", "nome": "GoEmotions-PT, teste interno",
         "independente": False, "exemplos": teste_ge, "ressalvas": [_RESSALVA_INTERNO_ANTIGO]},
        {"id": "emocao_xed_pt", "nome": "XED-pt (legendas, portugues europeu)",
         "independente": True, "exemplos": xed,
         "ressalvas": ["Rotulos projetados de outras linguas, sem a classe neutro: "
                       "o F1-macro conta so as classes presentes."]},
    ]
    return _amostrar(saida, amostra)


def conjuntos_ironia(amostra: int | None) -> list[dict]:
    regua = corpora.Exemplos(
        textos=list(SINCERAS_COM_MARCADOR) + list(IRONIAS_SEM_MARCADOR),
        rotulos=[0] * len(SINCERAS_COM_MARCADOR) + [1] * len(IRONIAS_SEM_MARCADOR),
        nomes_classes=["nao_ironico", "ironico"],
    )
    multipico = corpora.ler_multipico(
        baixar(corpora.URL_MULTIPICO, CACHE / "multipico" / "multipico_anonimized.csv")
    )
    teste_mp = preparar_divisao(multipico, **corpora.FRACOES_MULTIPICO)["teste"]
    return _amostrar([{
        "id": "ironia_multipico", "nome": "MultiPICo-PT, respostas de Reddit/Twitter",
        "independente": True, "exemplos": teste_mp,
        "ressalvas": [
            "Rotulo por maioria de ~5 anotadores; empates fora. As duas classes vem das "
            "mesmas fontes (sem atalho de procedencia). PT-BR e PT-PT juntos. A ironia "
            "foi anotada VENDO o post; o modelo le so a resposta.",
            "Deixa de ser independente para candidato treinado com o MultiPICo "
            "(o teste continua disjunto do treino).",
        ],
    }, {
        "id": "ironia_regua_20", "nome": "Regua de 20 frases de atendimento",
        "independente": True, "exemplos": regua,
        "ressalvas": ["20 frases: IC de cerca de +-0,22. Serve de alarme, nao de medida fina. "
                      "A regua de pares minimos substitui esta quando congelar."],
    }], amostra)


def _amostrar(conjuntos: list[dict], amostra: int | None) -> list[dict]:
    if amostra:
        for c in conjuntos:
            antes = len(c["exemplos"].textos)
            c["exemplos"] = amostra_estratificada(c["exemplos"], amostra)
            if len(c["exemplos"].textos) < antes:
                c["ressalvas"].append(
                    f"Amostra estratificada de {len(c['exemplos'].textos)} de {antes} "
                    "(semente fixa), por custo de CPU."
                )
    return conjuntos


CONJUNTOS = {"satisfacao": conjuntos_satisfacao, "emocao": conjuntos_emocao,
             "ironia": conjuntos_ironia}


# --- predicao -------------------------------------------------------------------


def prever(caminho: Path, textos: list[str], *, lote: int = 32) -> list[list[float]]:
    from fraus.sinais.texto import carregar_torch, prever_torch, temperatura_do_artefato

    # A mesma temperatura que o runtime aplicaria (1,0 nos artefatos antigos).
    temperatura = temperatura_do_artefato(caminho)
    tokenizador, modelo = carregar_torch(caminho, str(caminho))
    probs: list[list[float]] = []
    for inicio in range(0, len(textos), lote):
        probs.extend(prever_torch(tokenizador, modelo, textos[inicio:inicio + lote], temperatura))
        print(f"\r  {caminho.name}: {len(probs)}/{len(textos)}", end="", file=sys.stderr)
    print(file=sys.stderr)
    return probs


def _commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(RAIZ), "rev-parse", "--short", "HEAD"], text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def medir(tarefa: str, modelos: dict[str, Path], amostra: int | None) -> dict:
    conjuntos = []
    for c in CONJUNTOS[tarefa](amostra):
        ex = c["exemplos"]
        print(f"{c['id']}: {len(ex.textos)} exemplos", file=sys.stderr)
        probs = {nome: prever(caminho, ex.textos) for nome, caminho in modelos.items()}
        for nome, p in probs.items():
            if len(p[0]) != len(ex.nomes_classes):
                raise ValueError(
                    f"{nome} devolve {len(p[0])} classes e {c['id']} tem {len(ex.nomes_classes)}"
                )
        presentes = sorted(set(ex.rotulos))
        registro = {
            "id": c["id"], "nome": c["nome"], "independente": c["independente"],
            "exemplos": len(ex.textos), "impressao": impressao_dos_textos(ex.textos),
            "classes": ex.nomes_classes, "classes_presentes": presentes,
            "ressalvas": c["ressalvas"],
            "modelos": {nome: metricas_completas(p, ex.rotulos, nomes_classes=ex.nomes_classes)
                        for nome, p in probs.items()},
        }
        if len(presentes) < len(ex.nomes_classes):
            from fraus.comparacao_modelos import f1_macro

            for nome, p in probs.items():
                preditos = [max(range(len(x)), key=x.__getitem__) for x in p]
                registro["modelos"][nome]["f1_macro_classes_presentes"] = f1_macro(
                    ex.rotulos, preditos, classes=presentes
                )
        if len(modelos) == 2:
            referencia, candidato = list(modelos)
            pareado = avaliar_conjunto(
                identificador=c["id"], tarefa=tarefa, nome=c["nome"],
                independente=c["independente"], rotulos=ex.rotulos,
                preditos_por_modelo={
                    n: [max(range(len(x)), key=x.__getitem__) for x in p] for n, p in probs.items()
                },
                classes=list(range(len(ex.nomes_classes))), nomes_classes=ex.nomes_classes,
                classes_do_f1=presentes, candidato=candidato, referencia=referencia,
            )
            registro["comparacao"] = pareado["comparacao"]
        conjuntos.append(registro)
    return {
        "schema": SCHEMA,
        "tarefa": tarefa,
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "procedencia": {"commit": _commit(), "modelos": {n: str(p) for n, p in modelos.items()},
                        "amostra": amostra},
        "conjuntos": conjuntos,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("tarefa", choices=sorted(CONJUNTOS))
    parser.add_argument("--modelo", action="append", required=True, metavar="NOME=CAMINHO",
                        help="uma ou duas vezes; com duas, a primeira e a referencia")
    parser.add_argument("--amostra", type=int, default=None,
                        help="teto de exemplos por conjunto (amostra estratificada)")
    parser.add_argument("--saida", type=Path, required=True)
    args = parser.parse_args(argv)

    modelos: dict[str, Path] = {}
    for item in args.modelo:
        nome, _, caminho = item.partition("=")
        if not nome or not caminho:
            parser.error(f"--modelo espera NOME=CAMINHO, veio {item!r}")
        modelos[nome] = Path(caminho)
    if len(modelos) > 2:
        parser.error("no maximo dois modelos: referencia e candidato")

    laudo = medir(args.tarefa, modelos, args.amostra)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(json.dumps(laudo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for c in laudo["conjuntos"]:
        linha = ", ".join(
            f"{n} F1 {m.get('f1_macro_classes_presentes', m['f1_macro']):.3f} "
            f"acc {m['acuracia']:.3f} ECE {m['ece']:.3f}"
            for n, m in c["modelos"].items()
        )
        print(f"{c['id']} (n={c['exemplos']}): {linha}")
        if "comparacao" in c:
            k = c["comparacao"]
            print(f"  diferenca {k['diferenca_f1_macro']:+.3f} IC95 "
                  f"[{k['ic95'][0]:+.3f}, {k['ic95'][1]:+.3f}] p={k['mcnemar']['p_valor']:.2g}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
