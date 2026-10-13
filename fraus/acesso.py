"""Chave de ACESSO: credencial de operador da API inteira, nao de uma fonte.

Mesmo desenho de fraus/credencial.py (segredo sorteado, hash no banco,
mostrada uma vez) com prefixo proprio -- `fra_` contra `frs_` -- porque os
papeis nao se misturam: chave de fonte so empurra atendimento para dentro
(`POST /ingestao`), chave de acesso le e ESCREVE todo o resto (configuracoes,
lexico, importacao, fontes, acesso de usuarios) -- nao e somente leitura. So
a gestao de chaves (`/acesso/chaves`, chave e segredo de fonte) exige a
mestra (`exigir_mestra`), e o proxy da dashboard usa esta chave para escrever
no modo local. Uma chave de um papel apresentada no lugar do outro falha na
leitura do prefixo, antes de qualquer consulta ao banco.
"""

import secrets

from fraus import credencial

PREFIXO = "fra"

# A mestra gerada pela tela. Prefixo proprio pelo mesmo motivo dos outros dois:
# varredura de segredo em repositorio reconhece o que e, e chave apresentada no
# papel errado falha na leitura do prefixo antes de qualquer consulta.
PREFIXO_MESTRA = "frm"


def gerar(chave_id: int) -> tuple[str, str]:
    """Cria uma chave nova. Devolve `(chave_em_claro, hash)`.

    O id vem do banco (a linha nasce antes da chave) e vai embutido em texto
    claro para a conferencia achar o hash sem varrer a tabela -- quem autoriza
    e o hash, nunca o id. Ver credencial.py, decisao 3.
    """
    segredo = secrets.token_hex(credencial.BYTES_DO_SEGREDO)
    chave = f"{PREFIXO}_{chave_id}_{segredo}"
    return chave, credencial.hash_da_chave(chave)


def gerar_mestra() -> tuple[str, str]:
    """Cria uma chave mestra nova. Devolve `(chave_em_claro, hash)`.

    Sem id embutido, ao contrario de `gerar`: existe no maximo UMA mestra
    (`CHECK (id = 1)` na tabela), e nao ha linha a localizar -- a conferencia
    le o unico hash gravado.

    O segredo tem os mesmos 32 bytes sorteados das outras credenciais. A mestra
    inventada a mao pelo operador continua valendo pela variavel de ambiente;
    esta funcao existe para a tela nao pedir ao Joao que invente entropia.
    """
    segredo = secrets.token_hex(credencial.BYTES_DO_SEGREDO)
    chave = f"{PREFIXO_MESTRA}_{segredo}"
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
