"""Baixa as respostas da anotacao da regua (`GET /anotacao/respostas`).

Uso:
    FRAUS_CHAVE_ACESSO=... uv run python scripts/exportar_anotacao.py respostas-fraus.json

Grava a lista de registros {anotador, frase_id, resposta, instante} no
formato que `scripts/consolidar_regua_ironia.py` le. API em `FRAUS_API_URL`
(padrao https://fraus-api.vercel.app); a credencial nunca e impressa.
"""

import json
import os
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urljoin

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from scripts.criar_link_anotacao import API_PADRAO, base, chamar, chave_do_ambiente  # noqa: E402

abrir_url = urllib.request.urlopen


def main(argv=None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        sys.exit(__doc__)
    api = os.environ.get("FRAUS_API_URL", API_PADRAO)
    registros = chamar("GET", urljoin(base(api), "anotacao/respostas"), chave_do_ambiente(), abrir=abrir_url)
    Path(argv[0]).write_text(json.dumps(registros, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(registros)} registros de {len({r['anotador'] for r in registros})} anotadores em {argv[0]}")


if __name__ == "__main__":
    main()
