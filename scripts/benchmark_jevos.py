"""Benchmark OFFLINE do jevos contra o BERTimbau, em satisfacao e em ironia.

O jevos (https://github.com/feder-cr/jev) e um LLM pequeno que responde
perguntas de sim/nao e de escolha por HTTP, em CPU. Este script serve so para
medir se ele e "soberano" contra o BERTimbau nas duas tarefas. NADA daqui entra
em `fraus/` nem em `pyproject.toml`: a invariante 1 (sem LLM em runtime)
continua valendo, qualquer que seja o resultado.

O jevos le SO INGLES (wiki dele, "using-an-english-only-model-with-other-
languages"). Por isso ha dois bracos: texto PT cru e texto traduzido PT->EN
localmente (`--traduzir`, via argostranslate). O braco traduzido mede o jevos
MAIS o tradutor. O BERTimbau sempre le o original em portugues.

Uso, com `./jev serve --threads 8 --port 8017 --state-cache 0` de pe:

    uv run python scripts/benchmark_jevos.py satisfacao \\
        --bertimbau ../Fraus/modelos/bertimbau-satisfacao \\
        --jevos-url http://127.0.0.1:8017 --amostra 5000 \\
        --saida docs/notas/2026-11-06-benchmark-jevos-satisfacao-cru.json

    uv run --with argostranslate python scripts/benchmark_jevos.py ironia \\
        --bertimbau ../Fraus/modelos/bertimbau-ironia \\
        --jevos-url http://127.0.0.1:8017 --traduzir \\
        --saida docs/notas/2026-11-06-benchmark-jevos-ironia-traduzido.json

Os exemplos e a divisao saem de `scripts.benchmark_motores` (os mesmos
corpora, a mesma impressao). Cada resposta do jevos e gravada em
`~/.cache/fraus/experimentos/jevos-2026-11-06/` para auditoria.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from fraus.comparacao_modelos import avaliar_conjunto  # noqa: E402
from fraus.divisao import impressao_dos_textos  # noqa: E402
from fraus.receita_treino import metricas_completas  # noqa: E402
from scripts.benchmark_motores import (  # noqa: E402
    SCHEMA,
    _commit,
    conjuntos_ironia,
    conjuntos_satisfacao,
    prever,
)

RELEASE = "jevos-v5"
PASTA_RESPOSTAS = Path.home() / ".cache" / "fraus" / "experimentos" / "jevos-2026-11-06"
TIMEOUT_S = 30
AQUECIMENTO = 20

# Ordem das classes do Fraus (invariante 8): 0 insatisfeito, 1 neutro, 2 satisfeito.
NOMES_SATISFACAO = ("insatisfeito", "neutro", "satisfeito")

PERGUNTAS = {
    "satisfacao": {
        "sat": {
            "type": "choice",
            "instructions": (
                "This is a customer's review or message about a purchase or a service. "
                "How satisfied is the customer?"
            ),
            "criteria": {
                "insatisfeito": "the customer is dissatisfied, complains or is angry",
                "neutro": "the customer is neither satisfied nor dissatisfied, or mixed",
                "satisfeito": "the customer is satisfied, thankful or pleased",
            },
        }
    },
    "ironia": {
        "ironia": {"type": "noul", "instructions": "Is the writer being sarcastic or ironic?"}
    },
}

CONJUNTOS = {"satisfacao": conjuntos_satisfacao, "ironia": conjuntos_ironia}


def probabilidades_do_jevos(resposta: dict, tarefa: str) -> list[float]:
    """A resposta do jevos na ordem de classes do Fraus.

    Satisfacao: mapeada POR NOME, nunca pela ordem do JSON (invariante 8) --
    inverter nao gera erro, faz o sistema pontuar ao contrario em silencio.
    Chave ausente propaga `KeyError`.
    """
    if tarefa == "satisfacao":
        probs = resposta["answers"]["sat"]["probabilities"]
        return [float(probs[nome]) for nome in NOMES_SATISFACAO]
    p = float(resposta["answers"]["ironia"]["noul"])
    return [1.0 - p, p]


def _requisicao(url: str, corpo: dict | None = None) -> dict:
    dados = None if corpo is None else json.dumps(corpo).encode("utf-8")
    requisicao = urllib.request.Request(
        url, data=dados, headers={"Content-Type": "application/json"},
        method="GET" if corpo is None else "POST",
    )
    # Sem retry e sem pular exemplo: erro de rede ou HTTP 4xx/5xx derruba a rodada.
    with urllib.request.urlopen(requisicao, timeout=TIMEOUT_S) as resposta:
        return json.load(resposta)


def conferir_pronto(base: str) -> dict:
    try:
        saude = _requisicao(f"{base}/health")
    except (OSError, urllib.error.URLError) as erro:
        raise SystemExit(f"jevos nao esta pronto em {base}: {erro}") from erro
    if saude.get("status") != "ready":
        raise SystemExit(f"jevos nao esta pronto em {base}")
    return saude


def perguntar(base: str, tarefa: str, texto: str) -> tuple[dict, float]:
    corpo = {"model": "jev-latest", "state": texto, "questions": PERGUNTAS[tarefa]}
    inicio = time.perf_counter()
    resposta = _requisicao(f"{base}/v1/systemone", corpo)
    return resposta, (time.perf_counter() - inicio) * 1000


def traduzir_para_ingles(textos: list[str]) -> list[str]:
    try:
        import argostranslate.package
        import argostranslate.translate
    except ImportError:
        raise SystemExit(
            "rode com: uv run --with argostranslate python scripts/benchmark_jevos.py ..."
        ) from None
    instalados = {(i.code) for i in argostranslate.translate.get_installed_languages()}
    if not {"pt", "en"} <= instalados or argostranslate.translate.get_translation_from_codes(
        "pt", "en"
    ) is None:
        argostranslate.package.update_package_index()
        pacote = next(
            p for p in argostranslate.package.get_available_packages()
            if p.from_code == "pt" and p.to_code == "en"
        )
        argostranslate.package.install_from_path(pacote.download())
    traducao = argostranslate.translate.get_translation_from_codes("pt", "en")
    saida = []
    for i, texto in enumerate(textos, 1):
        saida.append(traducao.translate(texto))
        if i % 100 == 0:
            print(f"\r  traduzindo: {i}/{len(textos)}", end="", file=sys.stderr)
    print(file=sys.stderr)
    return saida


def resumir_latencias(ms: list[float]) -> dict:
    ordenadas = sorted(ms)
    p95 = ordenadas[max(0, math.ceil(0.95 * len(ordenadas)) - 1)]
    return {"n": len(ordenadas), "p50_ms": statistics.median(ordenadas), "p95_ms": p95,
            "media_ms": statistics.fmean(ordenadas)}


def ler_com_o_jevos(base: str, tarefa: str, textos_pt: list[str], textos_enviados: list[str],
                    arquivo: Path) -> tuple[list[list[float]], list[float]]:
    for texto in textos_enviados[:AQUECIMENTO]:  # aquecimento, descartado
        perguntar(base, tarefa, texto)
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    probs, duracoes = [], []
    with arquivo.open("w", encoding="utf-8") as saida:
        for i, texto in enumerate(textos_enviados):
            resposta, ms = perguntar(base, tarefa, texto)
            probs.append(probabilidades_do_jevos(resposta, tarefa))
            duracoes.append(ms)
            saida.write(json.dumps({"indice": i, "ms": ms, "resposta": resposta}) + "\n")
            if (i + 1) % 100 == 0:
                print(f"\r  jevos: {i + 1}/{len(textos_pt)}", end="", file=sys.stderr)
    print(file=sys.stderr)
    return probs, duracoes


def latencia_do_bertimbau(caminho: Path, textos: list[str], quantos: int) -> list[float]:
    """Um texto por chamada, como o jevos: lote de 1, modelo ja carregado."""
    from fraus.sinais.texto import carregar_torch, prever_torch, temperatura_do_artefato

    temperatura = temperatura_do_artefato(caminho)
    tokenizador, modelo = carregar_torch(caminho, str(caminho))
    prever_torch(tokenizador, modelo, textos[:5], temperatura)  # aquecimento
    duracoes = []
    for texto in textos[:quantos]:
        inicio = time.perf_counter()
        prever_torch(tokenizador, modelo, [texto], temperatura)
        duracoes.append((time.perf_counter() - inicio) * 1000)
    return duracoes


def medir(args: argparse.Namespace) -> dict:
    import torch

    base = args.jevos_url.rstrip("/")
    saude = conferir_pronto(base)
    nome_jevos = "jevos_traduzido" if args.traduzir else "jevos"
    braco = "traduzido" if args.traduzir else "cru"
    conjuntos = []
    for c in CONJUNTOS[args.tarefa](args.amostra):
        ex = c["exemplos"]
        print(f"{c['id']}: {len(ex.textos)} exemplos", file=sys.stderr)
        enviados = traduzir_para_ingles(ex.textos) if args.traduzir else ex.textos
        probs = {"bertimbau": prever(args.bertimbau, ex.textos)}
        probs[nome_jevos], duracoes_jevos = ler_com_o_jevos(
            base, args.tarefa, ex.textos, enviados,
            PASTA_RESPOSTAS / f"{c['id']}-{braco}.jsonl",
        )
        for nome, p in probs.items():
            if len(p[0]) != len(ex.nomes_classes):
                raise ValueError(
                    f"{nome} devolve {len(p[0])} classes e {c['id']} tem {len(ex.nomes_classes)}"
                )
        preditos = {n: [max(range(len(x)), key=x.__getitem__) for x in p] for n, p in probs.items()}
        registro = {
            "id": c["id"], "nome": c["nome"], "independente": c["independente"],
            "exemplos": len(ex.textos), "impressao": impressao_dos_textos(ex.textos),
            "classes": ex.nomes_classes, "classes_presentes": sorted(set(ex.rotulos)),
            "ressalvas": c["ressalvas"],
            "modelos": {n: metricas_completas(p, ex.rotulos, nomes_classes=ex.nomes_classes)
                        for n, p in probs.items()},
            "latencia": {
                nome_jevos: resumir_latencias(duracoes_jevos),
                "bertimbau": resumir_latencias(
                    latencia_do_bertimbau(args.bertimbau, ex.textos, args.latencia)
                ),
            },
        }
        pareado = avaliar_conjunto(
            identificador=c["id"], tarefa=args.tarefa, nome=c["nome"],
            independente=c["independente"], rotulos=ex.rotulos, preditos_por_modelo=preditos,
            classes=list(range(len(ex.nomes_classes))), nomes_classes=ex.nomes_classes,
            classes_do_f1=registro["classes_presentes"],
            candidato=nome_jevos, referencia="bertimbau",
        )
        registro["comparacao"] = pareado["comparacao"]
        conjuntos.append(registro)
    return {
        "schema": SCHEMA,
        "tarefa": args.tarefa,
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "procedencia": {
            "commit": _commit(),
            "modelos": {"bertimbau": str(args.bertimbau), nome_jevos: base},
            "amostra": args.amostra,
            "jevos": {"release": RELEASE, "health": saude, "threads": args.jevos_threads,
                      "traduzido": args.traduzir},
            "torch_threads": torch.get_num_threads(),
        },
        "conjuntos": conjuntos,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("tarefa", choices=sorted(CONJUNTOS))
    parser.add_argument("--bertimbau", type=Path, required=True)
    parser.add_argument("--jevos-url", required=True)
    parser.add_argument("--traduzir", action="store_true",
                        help="traduz PT->EN antes do jevos (o BERTimbau le o original)")
    parser.add_argument("--amostra", type=int, default=None)
    parser.add_argument("--latencia", type=int, default=200,
                        help="quantos textos cronometrar no BERTimbau, um por chamada")
    parser.add_argument("--jevos-threads", type=int, default=8,
                        help="so registra: o valor com que o `jev serve` foi iniciado")
    parser.add_argument("--saida", type=Path, required=True)
    args = parser.parse_args(argv)

    laudo = medir(args)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(json.dumps(laudo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for c in laudo["conjuntos"]:
        linha = ", ".join(
            f"{n} F1 {m.get('f1_macro_classes_presentes', m['f1_macro']):.3f} "
            f"acc {m['acuracia']:.3f} ECE {m['ece']:.3f}"
            for n, m in c["modelos"].items()
        )
        print(f"{c['id']} (n={c['exemplos']}): {linha}")
        k = c["comparacao"]
        print(f"  diferenca {k['diferenca_f1_macro']:+.3f} IC95 "
              f"[{k['ic95'][0]:+.3f}, {k['ic95'][1]:+.3f}] p={k['mcnemar']['p_valor']:.2g}")
        for n, lat in c["latencia"].items():
            print(f"  latencia {n}: p50 {lat['p50_ms']:.0f} ms, p95 {lat['p95_ms']:.0f} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
