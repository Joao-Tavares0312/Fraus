"""Leva a Lumen Telecom ficticia a um Fraus pelo contrato publico `POST /ingestao`.

Por que nao a tela Analisar: ela analisa ate 10 atendimentos e 40 falas do
cliente por arquivo (`fraus/api/rotas/analise.py`) e grava cada um com id de
conteudo (`analise:<hash>`) -- os casos do roteiro sumiriam pelo nome. A
ingestao e o caminho de volume: pontua sem oclusao, guarda o id de origem
(`fonte:<n>:sintetica-lumen-tese`) e reenviar o mesmo id SUBSTITUI.

Antes, no Fraus de destino, uma conta `dev` cria em Integracoes uma fonte por
canal (`webchat`, `whatsapp`, `instagram`; o canal vem da fonte, nunca do
pedido) e gera a chave de cada uma. As chaves entram pelo ambiente:

    FRAUS_CHAVE_FONTE_WEBCHAT=frs_... FRAUS_CHAVE_FONTE_WHATSAPP=frs_... \\
    FRAUS_CHAVE_FONTE_INSTAGRAM=frs_... \\
    uv run python scripts/carregar_empresa_ficticia.py --url https://fraus-api.vercel.app

Sem `--url`, a API local do plano B (http://127.0.0.1:8001). Nenhuma chave e
impressa. Score, nota e categoria nao vao no pedido: o servidor deriva.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from fraus.ingest.csv_driver import carregar_csv  # noqa: E402

CSV_PADRAO = RAIZ / "dados_demo" / "lumen-telecom.csv"
TENTATIVAS_429 = 3


def _pedido(conversa) -> dict:
    return {
        "id": conversa.id,
        "mensagens": [
            {"autor": m.autor, "texto": m.texto, "enviada_em": m.enviada_em.isoformat()}
            for m in conversa.mensagens
        ],
        "escalou_para_humano": conversa.escalou_para_humano,
    }


def _postar(url: str, chave: str, corpo: dict) -> int:
    requisicao = urllib.request.Request(
        url, method="POST", data=json.dumps(corpo).encode(),
        headers={"Authorization": f"Bearer {chave}", "Content-Type": "application/json",
                 "User-Agent": "fraus-lumen/1"},
    )
    for tentativa in range(TENTATIVAS_429):
        try:
            with urllib.request.urlopen(requisicao, timeout=120) as resposta:
                return resposta.status
        except urllib.error.HTTPError as erro:
            # O teto e 120 por minuto por fonte: esperar a janela, nao insistir.
            if erro.code == 429 and tentativa + 1 < TENTATIVAS_429:
                time.sleep(60)
                continue
            return erro.code
    raise AssertionError("inalcancavel")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="http://127.0.0.1:8001", help="base da API do Fraus")
    parser.add_argument("--csv", type=Path, default=CSV_PADRAO)
    args = parser.parse_args()

    resultado = carregar_csv(args.csv)
    if resultado.rejeitadas:
        print(f"{len(resultado.rejeitadas)} linha(s) rejeitada(s) no CSV; nada enviado", file=sys.stderr)
        return 1
    canais = sorted({c.canal for c in resultado.conversas})
    chaves = {canal: os.environ.get(f"FRAUS_CHAVE_FONTE_{canal.upper()}") for canal in canais}
    faltam = [f"FRAUS_CHAVE_FONTE_{canal.upper()}" for canal, chave in chaves.items() if not chave]
    if faltam:
        print("faltam as chaves de fonte: " + ", ".join(faltam), file=sys.stderr)
        return 2

    destino = args.url.rstrip("/") + "/ingestao"
    falhas: dict[int, list[str]] = {}
    for numero, conversa in enumerate(resultado.conversas, start=1):
        status = _postar(destino, chaves[conversa.canal], _pedido(conversa))
        if status != 201:
            falhas.setdefault(status, []).append(conversa.id)
        if numero % 25 == 0:
            print(f"{numero}/{len(resultado.conversas)}", flush=True)

    enviados = len(resultado.conversas) - sum(len(ids) for ids in falhas.values())
    print(f"{enviados} de {len(resultado.conversas)} atendimento(s) aceitos")
    for status, ids in sorted(falhas.items()):
        print(f"  {status}: {len(ids)} -- primeiro {ids[0]}", file=sys.stderr)
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
