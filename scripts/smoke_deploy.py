"""Smoke pós-deploy sem imprimir URL ou credencial.

Uso no CI:
    FRAUS_SMOKE_URL=https://... uv run python scripts/smoke_deploy.py

O script termina; não é keep-alive e não mascara cold start.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urljoin, urlparse


def _url_segura(valor: str) -> str:
    analisada = urlparse(valor)
    if analisada.scheme != "https" or not analisada.netloc:
        raise ValueError("FRAUS_SMOKE_URL precisa ser uma URL HTTPS")
    if analisada.username or analisada.password or analisada.query or analisada.fragment:
        raise ValueError("FRAUS_SMOKE_URL nao pode conter credencial, query ou fragmento")
    return valor.rstrip("/") + "/"


def executar(url: str, token: str | None = None, tentativas: int = 8) -> dict:
    base = _url_segura(url)
    cabecalhos = {"User-Agent": "fraus-smoke/1"}
    if token:
        cabecalhos["Authorization"] = f"Bearer {token}"
    ultimo = "sem resposta"
    for tentativa in range(tentativas):
        try:
            requisicao = urllib.request.Request(urljoin(base, "saude"), headers=cabecalhos)
            with urllib.request.urlopen(requisicao, timeout=30) as resposta:
                corpo = json.load(resposta)
            if corpo.get("status") != "ok" or corpo.get("motor") != "real":
                raise RuntimeError("liveness respondeu sem confirmar o motor real")
            estado = corpo.get("estado_motor", "pronto")
            if estado not in {"frio", "carregando", "pronto"}:
                raise RuntimeError(f"estado do motor nao saudavel: {estado}")
            return {"status": "ok", "motor": "real", "estado_motor": estado}
        except (OSError, ValueError, RuntimeError, urllib.error.HTTPError) as erro:
            ultimo = f"{type(erro).__name__}: {erro}"
            if tentativa + 1 < tentativas:
                time.sleep(min(2**tentativa, 10))
    raise RuntimeError(f"smoke falhou apos {tentativas} tentativas: {ultimo}")


def main() -> int:
    url = os.environ.get("FRAUS_SMOKE_URL", "")
    if not url:
        print("FRAUS_SMOKE_URL nao definida", file=sys.stderr)
        return 2
    try:
        resultado = executar(url, os.environ.get("FRAUS_SMOKE_TOKEN"))
    except Exception as erro:
        # A URL e o token nunca entram nesta mensagem.
        print(str(erro), file=sys.stderr)
        return 1
    print(json.dumps(resultado, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
