"""Mede a virada retrospectiva (E6) contra o baseline "so o score final".

Para cada limiar de "abaixo", compara, sobre conversas do simulador:

- `recall_virada`: dos casos de rotulo 0 (insatisfeito), quantos tem virada;
- `recall_fim`: dos mesmos, quantos tem o ULTIMO score definido abaixo;
- `falso_alarme`: dos casos de rotulo diferente de 0, quantos tem virada;
- o lead time (falas e segundos entre a virada e o fim), mediana dos que viraram.

Por construcao `recall_virada == recall_fim`: ha virada se e so se o ultimo
score definido esta abaixo. A virada acrescenta lead time, nao recall.

O que NAO mede: o simulador sorteia todas as falas do cliente de UM rotulo
(`gerar_conversa(rotulo, frases_cliente, semente)`), entao nao ha trajetoria
dentro da conversa. O lead time daqui e artefato do gerador, nao previsao de
producao (ver `conferir_trajetoria`).

Falha ALTO: sem fusor ou cabecas, imprime "nao verificado" e sai com 2
(invariante 7). Nao ha motor duble. Nao escreve nada.

    uv run python scripts/medir_deterioracao.py [--n 300] [--semente 20261014]
"""

from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from fraus.deterioracao import indice_de_virada  # noqa: E402

SEMENTE = 20261014
QUANTIDADE = 300
LIMIARES_FIXOS = (30, 40, 50, 60, 70)


def conferir_trajetoria() -> str:
    return (
        "O simulador sorteia todas as falas do cliente do conjunto de frases de UM "
        "rótulo (gerar_conversa(rotulo, frases_cliente, semente)): não há trajetória "
        "dentro da conversa. Lead time medido aqui é artefato do gerador, não "
        "previsão de produção."
    )


def montar_motor_real():
    from fraus.api.caminhos import CAMINHO_FUSOR, backend_declarado
    from fraus.api.main import montar_classificadores
    from fraus.fusor import Fusor
    from fraus.motor import Motor

    fusor = Fusor.carregar(CAMINHO_FUSOR)  # primeiro: falha antes de carregar as cabecas
    texto, emocao, ironia = montar_classificadores(backend_declarado())
    return Motor(texto, fusor, emocao, ironia)


def _razao(numerador: int, denominador: int):
    return numerador / denominador if denominador else None


def _mediana(valores: list):
    return statistics.median(valores) if valores else None


def medir(casos, limiares) -> dict:
    """`casos`: lista de (scores, conversa, rotulo); `limiares`: nome -> predicado `abaixo`."""
    resultado = {}
    for nome, abaixo in limiares.items():
        positivos = negativos = com_virada = com_fim = falsos = 0
        falas, segundos = [], []
        for scores, conversa, rotulo in casos:
            virada = indice_de_virada(scores, abaixo)
            definidos = [s for s in scores if s is not None]
            fim_abaixo = bool(definidos) and abaixo(definidos[-1])
            if rotulo == 0:
                positivos += 1
                com_fim += fim_abaixo
                if virada is not None:
                    com_virada += 1
                    mensagens = conversa.mensagens
                    falas.append(len(mensagens) - 1 - virada)
                    fim = conversa.encerrada_em or mensagens[-1].enviada_em
                    segundos.append((fim - mensagens[virada].enviada_em).total_seconds())
            else:
                negativos += 1
                falsos += virada is not None
        resultado[nome] = {
            "recall_virada": _razao(com_virada, positivos),
            "recall_fim": _razao(com_fim, positivos),
            "falso_alarme": _razao(falsos, negativos),
            "lead_falas_mediana": _mediana(falas),
            "lead_segundos_mediana": _mediana(segundos),
        }
    return resultado


def _fmt(valor) -> str:
    return "n/d" if valor is None else f"{valor:.2f}"


def principal(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--n", type=int, default=QUANTIDADE)
    parser.add_argument("--semente", type=int, default=SEMENTE)
    argumentos = parser.parse_args(argv)

    print(conferir_trajetoria())
    try:
        motor = montar_motor_real()
    except Exception as erro:
        print(f"não verificado — modelos ausentes: {erro}")
        return 2

    from fraus.indicadores import FAIXAS_NPS, categoria_nps
    from fraus.ingest.simulador import FRASES_POR_ROTULO, gerar_lote

    print("frases: FRASES_POR_ROTULO do simulador (as mesmas de medir_aditividade.py)")
    lote = gerar_lote(FRASES_POR_ROTULO, argumentos.n, argumentos.semente)
    casos = [(motor.scores_do_replay(c), c, rotulo) for c, rotulo in lote]
    limiares = {"faixa de fábrica (detrator)": lambda s: categoria_nps(s, FAIXAS_NPS) == "detrator"}
    limiares.update({f"score < {n}": (lambda s, n=n: s < n) for n in LIMIARES_FIXOS})
    print(f"{len(casos)} conversas, semente {argumentos.semente}")
    print(f"{'limiar':30} recall_virada recall_fim falso_alarme lead_falas lead_s")
    for nome, r in medir(casos, limiares).items():
        print(f"{nome:30} {_fmt(r['recall_virada']):>13} {_fmt(r['recall_fim']):>10} "
              f"{_fmt(r['falso_alarme']):>12} {_fmt(r['lead_falas_mediana']):>10} "
              f"{_fmt(r['lead_segundos_mediana']):>6}")
    print("recall_virada = recall_fim por construção: a virada acrescenta lead time, não recall")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
