"""Normalizacao de termo, num lugar so.

Existe como modulo proprio por uma razao de dependencia, e nao de organizacao:
`sem_acento` nasceu em `lexico.py` e agora e preciso tambem em `curadoria.py`.
Importar de um para o outro criaria ciclo (o lexico ja importa a curadoria), e
copiar as quatro linhas criaria uma SEGUNDA regra de normalizacao -- que e o
tipo de coisa que diverge em silencio no dia em que uma das duas muda.
"""

import unicodedata


def sem_acento(texto: str) -> str:
    """Remove diacriticos, preservando o resto.

    O cliente de chat nem sempre acentua, entao `otimo` precisa achar `otimo`.
    Quem consome constroi um INDICE com isto -- nunca compara termo a termo em
    laco, que seria varrer o lexicon inteiro a cada token.
    """
    return "".join(
        c
        for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
