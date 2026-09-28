"""Valida uma cabeca de ironia antes de promove-la para ``modelos/``.

Esta regua autoral nao substitui corpus humano independente. Ela apenas impede
que a acuracia perfeita no sintetico esconda novamente os atalhos conhecidos.

Uso:
    uv run python scripts/validar_candidato_ironia.py /caminho/do/candidato
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from fraus.avaliacao_ironia import (avaliar_classificador,  # noqa: E402
                                    candidato_apto_para_promocao)
from fraus.sinais.ironia import ClassificadorIronia  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidato", type=Path)
    parser.add_argument("--max-falso-positivo", type=float, default=0.30)
    parser.add_argument("--max-falso-negativo", type=float, default=0.30)
    parser.add_argument("--saida-json", type=Path)
    opcoes = parser.parse_args()

    resultado = avaliar_classificador(ClassificadorIronia(opcoes.candidato))
    relatorio = resultado.como_dict() | {
        "limites_promocao": {
            "taxa_falso_positivo": opcoes.max_falso_positivo,
            "taxa_falso_negativo": opcoes.max_falso_negativo,
        }
    }
    texto = json.dumps(relatorio, ensure_ascii=False, indent=2)
    print(texto)
    if opcoes.saida_json:
        opcoes.saida_json.write_text(texto + "\n", encoding="utf-8")

    apto = candidato_apto_para_promocao(
        resultado,
        maximo_falso_positivo=opcoes.max_falso_positivo,
        maximo_falso_negativo=opcoes.max_falso_negativo,
    )
    if not apto:
        print(
            "REPROVADO: nao substitua modelos/bertimbau-ironia com este artefato.",
            file=sys.stderr,
        )
        return 1
    print("APROVADO NA REGUA AUTORAL (nao equivale a validacao externa).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
