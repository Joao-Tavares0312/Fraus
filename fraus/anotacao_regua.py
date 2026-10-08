"""O que a pagina de anotacao recebe: id opaco e texto. Nada mais.

Par, estrato e rotulo pretendido ficam no repositorio. Cada
frase leva `g`, um numero de grupo compartilhado pelos dois lados do par e
sorteado por permutacao -- nao revela estrato, rotulo nem ordem. A pagina
embaralha por anotador e usa `g` so para nunca por os dois lados em sequencia.
A ordem que sai daqui tambem ja nao tem lados vizinhos, nem na volta.

Na anotacao DENTRO do Fraus (`fraus/api/rotas/anotacao.py`) quem embaralha e
o servidor: `ordem_do_anotador` sorteia com semente derivada do id opaco do
anotador e entrega so `id` e `texto` -- nem `g` sai, porque a pagina ja nao
precisa dele.
"""

from __future__ import annotations

import hashlib
import random
from collections.abc import Sequence

from fraus.avaliacao_ironia import FraseDoRascunho


def frases_para_anotacao(
    frases: Sequence[FraseDoRascunho], *, semente: int = 42
) -> list[dict]:
    gerador = random.Random(semente)
    pares = sorted({f.par_id for f in frases})
    numeros = list(range(len(pares)))
    gerador.shuffle(numeros)
    grupo = dict(zip(pares, numeros))
    for _ in range(1000):
        ordem = list(frases)
        gerador.shuffle(ordem)
        vizinhos = zip(ordem, ordem[1:] + ordem[:1])
        if all(a.par_id != b.par_id for a, b in vizinhos):
            return [{"id": f.frase_id, "texto": f.texto, "g": grupo[f.par_id]} for f in ordem]
    raise RuntimeError("nao achei ordem sem par vizinho em 1000 tentativas")


def semente_do_anotador(anotador: str) -> int:
    """Semente estavel entre processos -- `hash()` de str nao e (PYTHONHASHSEED)."""
    return int.from_bytes(hashlib.sha256(anotador.encode("utf-8")).digest()[:8], "big")


def ordem_do_anotador(frases: Sequence[FraseDoRascunho], anotador: str) -> list[dict]:
    """A ordem DESTE anotador: so id e texto, sem lados do par em sequencia."""
    ordem = frases_para_anotacao(frases, semente=semente_do_anotador(anotador))
    return [{"id": item["id"], "texto": item["texto"]} for item in ordem]


def respostas_do_anotador(registros: Sequence[dict], anotador: str) -> dict[str, str]:
    """Ultima resposta (maior `instante`) deste anotador por frase.

    `instante` e carimbado pelo servidor sempre na mesma forma ISO UTC, entao
    comparar como texto e comparar no tempo.
    """
    ultima: dict[str, dict] = {}
    for registro in registros:
        if registro["anotador"] != anotador:
            continue
        atual = ultima.get(registro["frase_id"])
        if atual is None or registro["instante"] > atual["instante"]:
            ultima[registro["frase_id"]] = registro
    return {frase_id: r["resposta"] for frase_id, r in ultima.items()}
