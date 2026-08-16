"""Chave de ACESSO: autoriza a leitura da API inteira, nao uma fonte.

Mesmo desenho de fraus/credencial.py (segredo sorteado, hash no banco,
mostrada uma vez) com prefixo proprio -- `fra_` contra `frs_` -- porque os
papeis nao se misturam: chave de fonte so empurra atendimento para dentro
(`POST /ingestao`), chave de acesso le todo o resto. Uma chave de um papel
apresentada no lugar do outro falha na leitura do prefixo, antes de qualquer
consulta ao banco.
"""

import secrets

from fraus import credencial

PREFIXO = "fra"


def gerar(chave_id: int) -> tuple[str, str]:
    """Cria uma chave nova. Devolve `(chave_em_claro, hash)`.

    O id vem do banco (a linha nasce antes da chave) e vai embutido em texto
    claro para a conferencia achar o hash sem varrer a tabela -- quem autoriza
    e o hash, nunca o id. Ver credencial.py, decisao 3.
    """
    segredo = secrets.token_hex(credencial.BYTES_DO_SEGREDO)
    chave = f"{PREFIXO}_{chave_id}_{segredo}"
    return chave, credencial.hash_da_chave(chave)


def id_da_chave(chave: str) -> int | None:
    """Le o id embutido, sem confiar nele. `None` para tudo fora do formato."""
    partes = chave.split("_")
    if len(partes) != 3 or partes[0] != PREFIXO:
        return None
    try:
        return int(partes[1])
    except ValueError:
        return None
