"""O que a pagina de anotacao recebe: id opaco e texto. Nada mais.

Par, estrato e rotulo pretendido ficam no repositorio. Cada
frase leva `g`, um numero de grupo compartilhado pelos dois lados do par e
sorteado por permutacao -- nao revela estrato, rotulo nem ordem. A pagina
embaralha por anotador e usa `g` so para nunca por os dois lados em sequencia.
A ordem que sai daqui tambem ja nao tem lados vizinhos, nem na volta.
"""

from __future__ import annotations

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
