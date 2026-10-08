"""O que a pagina de anotacao recebe: id opaco e texto. Nada mais.

Par, estrato e rotulo pretendido ficam no repositorio. A pagina mostra a
mesma sequencia a todos, girada por anotador; por isso a sequencia ja sai
daqui sem os dois lados de um par vizinhos -- nem o ultimo com o primeiro.
"""

from __future__ import annotations

import random
from collections.abc import Sequence

from fraus.avaliacao_ironia import FraseDoRascunho


def frases_para_anotacao(
    frases: Sequence[FraseDoRascunho], *, semente: int = 42
) -> list[dict[str, str]]:
    gerador = random.Random(semente)
    for _ in range(1000):
        ordem = list(frases)
        gerador.shuffle(ordem)
        vizinhos = zip(ordem, ordem[1:] + ordem[:1])
        if all(a.par_id != b.par_id for a, b in vizinhos):
            return [{"id": f.frase_id, "texto": f.texto} for f in ordem]
    raise RuntimeError("nao achei ordem sem par vizinho em 1000 tentativas")
