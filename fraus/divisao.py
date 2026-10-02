"""Divisao treino/teste por autor, compartilhada pelos notebooks 04 e 07.

A regra e a mesma dos dois lados da comparacao BERTimbau x Laya: quem treina e
quem compara chamam `dividir_por_autor` e conferem o resultado com
`conferir_divisao`. A `impressao_dos_textos` do teste vai gravada junto do
artefato, e a comparacao so vale se as duas impressoes forem iguais.

Em 02/10/2026 a divisao do corpus de ironia saiu com 63% das linhas no teste
(o pedido era 15%) e com o treino 86% ironico contra 43% no teste. A regra
estava escrita nos notebooks como `autores.astype(str)`, que transforma o campo
vazio no autor "nan": as 18.373 noticias, que nao tem autor, viraram uma pessoa
so e cairam inteiras no teste. Ninguem viu porque nada conferia o resultado.

`sklearn` so e importado dentro de `dividir_por_autor`.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from collections.abc import Iterable, Sequence

_SEM_AUTOR = "\x00sem-autor:"


def grupos_por_autor(autores: Iterable[object]) -> list[str]:
    """Um grupo por autor; cada linha sem autor e um grupo proprio.

    Sem autor quer dizer `None`, NaN ou texto em branco. O valor entra como
    veio do corpus -- converter para texto antes e o que criava o autor "nan".
    """
    grupos = []
    for posicao, autor in enumerate(autores):
        nome = autor.strip() if isinstance(autor, str) else ""
        grupos.append(nome or f"{_SEM_AUTOR}{posicao}")
    return grupos


def dividir_por_autor(
    autores: Sequence[object], *, fracao_teste: float = 0.15, semente: int = 42
) -> tuple[list[int], list[int]]:
    """Posicoes de treino e de teste, sem autor repetido entre os dois lados."""
    from sklearn.model_selection import GroupShuffleSplit

    grupos = grupos_por_autor(autores)
    divisor = GroupShuffleSplit(n_splits=1, test_size=fracao_teste, random_state=semente)
    treino, teste = next(divisor.split(grupos, groups=grupos))
    return [int(i) for i in treino], [int(i) for i in teste]


def conferir_divisao(
    rotulos_treino: Sequence[int],
    rotulos_teste: Sequence[int],
    *,
    fracao_teste: float,
    tolerancia_fracao: float = 0.05,
    tolerancia_classe: float = 0.05,
) -> None:
    """Levanta `ValueError` se a divisao nao e a que foi pedida.

    Confere o tamanho do teste e a participacao de cada classe nos dois lados.
    A tolerancia e em pontos de proporcao: 0.05 aceita 15% pedido e 19% obtido.
    """
    total = len(rotulos_treino) + len(rotulos_teste)
    if not rotulos_treino or not rotulos_teste:
        raise ValueError("divisao com um dos lados vazio")
    obtida = len(rotulos_teste) / total
    if abs(obtida - fracao_teste) > tolerancia_fracao:
        raise ValueError(
            f"o teste ficou com {obtida:.0%} das linhas e o pedido era {fracao_teste:.0%}: "
            "ha um grupo grande demais na divisao"
        )
    no_treino, no_teste = Counter(rotulos_treino), Counter(rotulos_teste)
    for classe in sorted(set(no_treino) | set(no_teste)):
        parte_treino = no_treino[classe] / len(rotulos_treino)
        parte_teste = no_teste[classe] / len(rotulos_teste)
        if abs(parte_treino - parte_teste) > tolerancia_classe or 0 in (
            no_treino[classe], no_teste[classe]
        ):
            raise ValueError(
                f"classe {classe}: {parte_treino:.0%} do treino e {parte_teste:.0%} do teste. "
                "O modelo aprenderia a proporcao do treino, e o teste mediria outra coisa"
            )


def impressao_dos_textos(textos: Iterable[object]) -> str:
    """SHA-256 do conjunto de textos, indiferente a ordem.

    Dois notebooks que dizem usar "o mesmo teste" comparam esta impressao.
    """
    resumo = hashlib.sha256()
    for texto in sorted(str(t) for t in textos):
        dados = texto.encode("utf-8")
        resumo.update(len(dados).to_bytes(8, "big"))
        resumo.update(dados)
    return resumo.hexdigest()
