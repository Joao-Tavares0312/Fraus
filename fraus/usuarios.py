"""Senha de usuario da dashboard: gerar hash e conferir.

Aqui NAO vale o SHA-256 puro do credencial.py, e a diferenca e a entropia:
la o segredo sao 32 bytes sorteados, que nenhum dicionario alcanca; senha e
escolhida por gente, e gente escolhe palavra de dicionario. O scrypt cobra
memoria de cada tentativa -- e o que faz forca bruta offline custar caro.

E do stdlib (`hashlib.scrypt`), entao a propriedade veio sem dependencia nova.

O formato guardado declara a si mesmo: `scrypt$<salt_b64>$<hash_b64>`. Se um
dia o custo subir ou o algoritmo mudar, o prefixo diz como conferir cada linha
antiga -- hash sem procedencia obrigaria a migrar todo mundo de uma vez.
"""

import base64
import hashlib
import hmac
import secrets

# 16 bytes de salt: o suficiente para dois usuarios com a mesma senha nunca
# dividirem hash -- hash igual contaria a quem le o banco que as senhas
# coincidem.
BYTES_DE_SALT = 16

# n=2^14, r=8, p=1: a recomendacao corrente para login interativo. Custa
# ~16 MB de memoria por conferencia -- caro para quem chuta em massa, barato
# para um login por vez. Subir n dobraria a memoria e estouraria o maxmem
# padrao do OpenSSL (32 MB).
CUSTO_N = 2**14
CUSTO_R = 8
CUSTO_P = 1
TAMANHO_DO_HASH = 32


def gerar_hash(senha: str) -> str:
    salt = secrets.token_bytes(BYTES_DE_SALT)
    return "$".join(
        (
            "scrypt",
            base64.b64encode(salt).decode("ascii"),
            base64.b64encode(_derivar(senha, salt)).decode("ascii"),
        )
    )


def confere(senha: str, guardado: str | None) -> bool:
    """Compara em tempo constante. Guardado ausente ou corrompido nunca autoriza.

    A derivacao roda MESMO quando a resposta ja esta decidida: pular o scrypt
    quando o usuario nao existe faria o login recusar rapido para e-mail
    inexistente e devagar para senha errada -- e o tempo contaria a quem tenta
    quais e-mails tem conta. O mesmo desenho de `fonte_autorizada`.
    """
    salt, esperado = _abrir(guardado)
    valido = salt is not None
    if salt is None:
        salt, esperado = _SALT_FALSO, _HASH_FALSO
    derivado = _derivar(senha, salt)
    return hmac.compare_digest(derivado, esperado) and valido


def _derivar(senha: str, salt: bytes) -> bytes:
    return hashlib.scrypt(
        senha.encode("utf-8"),
        salt=salt,
        n=CUSTO_N,
        r=CUSTO_R,
        p=CUSTO_P,
        dklen=TAMANHO_DO_HASH,
    )


def _abrir(guardado: str | None) -> tuple[bytes, bytes] | tuple[None, None]:
    """(salt, hash) de um registro valido; (None, None) para o resto."""
    if not guardado:
        return None, None
    partes = guardado.split("$")
    if len(partes) != 3 or partes[0] != "scrypt":
        return None, None
    try:
        return (
            base64.b64decode(partes[1], validate=True),
            base64.b64decode(partes[2], validate=True),
        )
    except (ValueError, TypeError):
        return None, None


# O par contra o qual a recusa deriva quando nao ha registro -- fixo, para o
# custo ser o mesmo do caminho real.
_SALT_FALSO = bytes(BYTES_DE_SALT)
_HASH_FALSO = bytes(TAMANHO_DO_HASH)
