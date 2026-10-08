"""Gera scripts/anotacao_ironia/frases.json a partir do rascunho da regua."""

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from fraus.anotacao_regua import frases_para_anotacao  # noqa: E402
from fraus.avaliacao_ironia import carregar_rascunho  # noqa: E402

destino = RAIZ / "scripts" / "anotacao_ironia" / "frases.json"
destino.write_text(
    json.dumps(frases_para_anotacao(carregar_rascunho()), ensure_ascii=False, indent=1) + "\n",
    encoding="utf-8",
)
print(f"{destino}: escrito")
