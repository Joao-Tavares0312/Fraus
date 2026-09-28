"""Decompõe latência HTTP e registra indícios de região sem expor secrets."""

import argparse
import hashlib
import http.client
import json
import os
import socket
import ssl
from statistics import median
from time import perf_counter
from urllib.parse import urlparse

CABECALHOS_DE_REGIAO = ("x-vercel-id", "x-served-by", "cf-ray", "fly-region")


def _alvo(url: str) -> tuple[str, int, str]:
    analisada = urlparse(url)
    if analisada.scheme != "https" or not analisada.hostname:
        raise ValueError("a URL medida precisa usar HTTPS")
    if analisada.username or analisada.password or analisada.query or analisada.fragment:
        raise ValueError("a URL nao pode conter credencial, query ou fragmento")
    caminho = analisada.path or "/"
    return analisada.hostname, analisada.port or 443, caminho


def medir_uma(url: str, token: str | None = None) -> dict:
    host, porta, caminho = _alvo(url)
    inicio_dns = perf_counter()
    socket.getaddrinfo(host, porta, type=socket.SOCK_STREAM)
    dns_ms = (perf_counter() - inicio_dns) * 1000

    conexao = http.client.HTTPSConnection(
        host, porta, timeout=30, context=ssl.create_default_context()
    )
    inicio_conexao = perf_counter()
    conexao.connect()
    conexao_tls_ms = (perf_counter() - inicio_conexao) * 1000
    cabecalhos = {"User-Agent": "fraus-latencia/1"}
    if token:
        cabecalhos["Authorization"] = f"Bearer {token}"
    inicio_requisicao = perf_counter()
    conexao.request("GET", caminho, headers=cabecalhos)
    resposta = conexao.getresponse()
    ttfb_ms = (perf_counter() - inicio_requisicao) * 1000
    resposta.read()
    transferencia_ms = (perf_counter() - inicio_requisicao) * 1000 - ttfb_ms
    regioes = {
        nome: resposta.getheader(nome)
        for nome in CABECALHOS_DE_REGIAO
        if resposta.getheader(nome)
    }
    conexao.close()
    return {
        "status": resposta.status,
        "dns_ms": round(dns_ms, 1),
        "conexao_tls_ms": round(conexao_tls_ms, 1),
        "ttfb_ms": round(ttfb_ms, 1),
        "transferencia_ms": round(max(0.0, transferencia_ms), 1),
        "server_timing": resposta.getheader("server-timing"),
        "regiao": regioes,
    }


def resumir(amostras: list[dict], url: str) -> dict:
    host, _, caminho = _alvo(url)
    campos = ("dns_ms", "conexao_tls_ms", "ttfb_ms", "transferencia_ms")
    return {
        # Identifica o alvo no relatório sem publicar hostname privado.
        "alvo": hashlib.sha256(f"{host}{caminho}".encode()).hexdigest()[:12],
        "amostras": len(amostras),
        "status": sorted({item["status"] for item in amostras}),
        "mediana_ms": {campo: round(median(item[campo] for item in amostras), 1) for campo in campos},
        "server_timing": [item["server_timing"] for item in amostras if item["server_timing"]],
        "regioes": [item["regiao"] for item in amostras if item["regiao"]],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url", nargs="?", default=os.environ.get("FRAUS_MEDIR_URL"))
    parser.add_argument("--amostras", type=int, default=3)
    args = parser.parse_args()
    if not args.url:
        parser.error("informe a URL ou FRAUS_MEDIR_URL")
    if not 1 <= args.amostras <= 20:
        parser.error("--amostras precisa estar entre 1 e 20")
    token = os.environ.get("FRAUS_MEDIR_TOKEN")
    amostras = [medir_uma(args.url, token) for _ in range(args.amostras)]
    print(json.dumps(resumir(amostras, args.url), ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
