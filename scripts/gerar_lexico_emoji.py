"""Exporta o lexicon de emoji para a dashboard.

A dashboard precisa da MESMA polaridade que `dolos.sinais.emoji` usa, senao a
interface estaria inventando um segundo criterio. Este script deriva o JSON a
partir de `dolos/dados/emoji_sentiment_ranking.csv` com a formula identica a de
`dolos.sinais.emoji._lexicon` -- ele nao e uma segunda fonte de verdade, e uma
projecao da primeira.

Rodar apos qualquer mudanca no CSV:
    uv run python scripts/gerar_lexico_emoji.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from dolos.sinais.emoji import _lexicon  # noqa: E402

DESTINO = RAIZ / "dashboard" / "lib" / "lexicoEmoji.json"


def main() -> None:
    tabela = {caractere: round(valor, 4) for caractere, valor in _lexicon().items()}
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(
        json.dumps(tabela, ensure_ascii=False, indent=0, sort_keys=True),
        encoding="utf-8",
    )
    print(f"[lexico] {len(tabela)} emojis -> {DESTINO}")


if __name__ == "__main__":
    main()
