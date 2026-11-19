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


# O que a dashboard publicada le e que uma API velha nao tem: em 30/09/2026 a
# dashboard nova recebeu 404 da API antiga, e a liveness passava assim mesmo.
CHAVES_DE_INDICADORES = (
    "nps", "sem_sinal", "total_conversas", "feedback_declarado_total", "concordancia_com_feedback",
)


def _ler(base: str, rota: str, cabecalhos: dict):
    requisicao = urllib.request.Request(urljoin(base, rota), headers=cabecalhos)
    try:
        with urllib.request.urlopen(requisicao, timeout=30) as resposta:
            return json.load(resposta)
    except urllib.error.HTTPError as erro:
        raise RuntimeError(f"contrato: {rota} respondeu {erro.code}") from None


def conferir_contrato(base: str, cabecalhos: dict) -> dict:
    """Uma vez, depois da liveness: as rotas que a dashboard le respondem.

    Sem repeticao: propagacao ja foi esperada pela liveness, e 401/404/503
    aqui e contrato quebrado, nao lentidao. A mensagem nomeia rota, status ou
    chave -- nunca URL nem token.
    """
    indicadores = _ler(base, "indicadores", cabecalhos)
    for chave in CHAVES_DE_INDICADORES:
        if not isinstance(indicadores, dict) or chave not in indicadores:
            raise RuntimeError(f"contrato: indicadores sem a chave {chave}")
    # 503 aqui e o artefato conformal ausente ou de outra regua.
    _ler(base, "indicadores/confianca", cabecalhos)
    return {"contrato": "conferido"}


def executar(url: str, token: str | None = None, tentativas: int = 8) -> dict:
    base = _url_segura(url)
    cabecalhos = {"User-Agent": "fraus-smoke/1"}
    if token:
        cabecalhos["Authorization"] = f"Bearer {token}"
    resultado = _liveness(base, cabecalhos, tentativas)
    if token:
        resultado.update(conferir_contrato(base, cabecalhos))
    else:
        print("contrato nao conferido: FRAUS_SMOKE_TOKEN ausente", file=sys.stderr)
    return resultado


def _liveness(base: str, cabecalhos: dict, tentativas: int) -> dict:
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
            # A funcao leve (auth, CRUD, leituras) e outra funcao da Vercel:
            # /saude acordou so a do motor.
            requisicao = urllib.request.Request(urljoin(base, "auth/estado"), headers=cabecalhos)
            with urllib.request.urlopen(requisicao, timeout=30) as resposta:
                try:
                    json.load(resposta)
                except ValueError:
                    raise RuntimeError("funcao leve nao respondeu /auth/estado") from None
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
