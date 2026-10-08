"""Cria links de anotador da regua de ironia (`POST /anotacao/anotadores`).

Uso:
    FRAUS_CHAVE_ACESSO=... uv run python scripts/criar_link_anotacao.py [--quantos N]

Imprime uma linha por anotador: `<id do anotador>  <link>`. O link e
`{FRAUS_DASHBOARD_URL}/anotar/<token>` (padrao https://fraus.vercel.app) e o
token so existe nesta saida -- o banco guarda o hash. Quem perder o link
recebe um novo; o antigo pode ser revogado no banco.

A API e `FRAUS_API_URL` (padrao https://fraus-api.vercel.app). A credencial
vem de `FRAUS_CHAVE_ACESSO` e nunca e impressa. Nenhum nome de pessoa vai
para a API: anote fora dela quem recebeu qual id.
"""

import argparse
import json
import os
import sys
import urllib.request
from urllib.parse import urljoin

API_PADRAO = "https://fraus-api.vercel.app"
DASHBOARD_PADRAO = "https://fraus.vercel.app"

abrir_url = urllib.request.urlopen


def chamar(metodo: str, url: str, chave: str, *, abrir=None):
    """JSON de uma chamada autenticada. Erro HTTP sobe como esta."""
    pedido = urllib.request.Request(url, method=metodo, headers={"Authorization": f"Bearer {chave}"})
    with (abrir or abrir_url)(pedido, timeout=60) as resposta:
        return json.loads(resposta.read().decode("utf-8"))


def base(url: str) -> str:
    return url if url.endswith("/") else url + "/"


def criar_links(api: str, chave: str, dashboard: str, quantos: int, *, abrir=None) -> list[tuple[str, str]]:
    links = []
    for _ in range(quantos):
        criado = chamar("POST", urljoin(base(api), "anotacao/anotadores"), chave, abrir=abrir)
        links.append((criado["anotador"], f"{dashboard.rstrip('/')}/anotar/{criado['token']}"))
    return links


def chave_do_ambiente() -> str:
    chave = os.environ.get("FRAUS_CHAVE_ACESSO")
    if not chave:
        sys.exit("defina FRAUS_CHAVE_ACESSO (mestra ou chave de acesso `fra_`)")
    return chave


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quantos", type=int, default=1)
    args = parser.parse_args(argv)
    if args.quantos < 1:
        parser.error("--quantos precisa ser pelo menos 1")
    links = criar_links(
        os.environ.get("FRAUS_API_URL", API_PADRAO), chave_do_ambiente(),
        os.environ.get("FRAUS_DASHBOARD_URL", DASHBOARD_PADRAO), args.quantos,
        abrir=abrir_url,
    )
    for anotador, link in links:
        print(f"{anotador}  {link}")


if __name__ == "__main__":
    main()
