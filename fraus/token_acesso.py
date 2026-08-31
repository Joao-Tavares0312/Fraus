"""O token de sessao da dashboard: JWT HS256, assinado com segredo do ambiente.

O segredo (`FRAUS_JWT_SEGREDO`) mora no ambiente e nunca no banco -- a mesma
regra do segredo de webhook (fraus/assinatura.py), pelo mesmo motivo: segredo
recuperavel num SQLite de arquivo vaza junto com o backup.

HS256 E FIXO POR CONSTRUCAO. `conferir` so aceita esse algoritmo; um token
declarando `alg: none` (o ataque classico) ou qualquer outro e recusado antes
de o payload ser olhado.

O relogio chega por parametro. O `exp` e conferido aqui contra o `agora`
recebido, nao pelo relogio interno da biblioteca -- e o que deixa a validade
testavel sem congelar o relogio do processo.
"""

from datetime import datetime, timedelta, timezone

import jwt

# 12 horas: cobre o dia de trabalho do analista; amanha ele entra de novo.
# Refresh token dobraria a superficie por conveniencia marginal (spec §3).
VALIDADE = timedelta(hours=12)

_ALGORITMO = "HS256"


def emitir(usuario_id: int, papel: str, segredo: str, agora: datetime) -> str:
    """`sub` vai como string porque a RFC 7519 o define assim -- verificador
    estrito (o proprio PyJWT, de 2.10 em diante) recusa numero."""
    return jwt.encode(
        {
            "sub": str(usuario_id),
            "papel": papel,
            "iat": agora,
            "exp": agora + VALIDADE,
        },
        segredo,
        algorithm=_ALGORITMO,
    )


def conferir(token: str, segredo: str, agora: datetime) -> dict | None:
    """A sessao do token, ou None. Nunca levanta: recusa e resposta, nao erro.

    Daqui so sai o que o resto do codigo precisa (`usuario_id`, `papel`) --
    devolver o payload cru convidaria alguem a ler um campo nao conferido.
    """
    try:
        payload = jwt.decode(
            token,
            segredo,
            algorithms=[_ALGORITMO],
            # O exp e conferido logo abaixo contra o `agora` recebido; deixar
            # a biblioteca conferir usaria o relogio do processo e o parametro
            # viraria enfeite.
            options={"verify_exp": False, "require": ["sub", "papel", "exp"]},
        )
        usuario_id = int(payload["sub"])
    except (jwt.InvalidTokenError, ValueError):
        return None
    expira_em = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    if agora >= expira_em:
        return None
    return {"usuario_id": usuario_id, "papel": payload["papel"]}
