"""O contrato dos sinalizadores tem duas metades; esta e a guarda barata.

Mesmo padrao de tests/test_contestacao_atravessa_a_fronteira.py: le .ts/.tsx
como TEXTO. Nao e typecheck -- impede o silencio.
"""

import pathlib
import re

from fraus.sinalizadores import REGRAS

RAIZ = pathlib.Path(__file__).parent.parent
API_TS = (RAIZ / "dashboard" / "lib" / "api.ts").read_text(encoding="utf-8")
TSX = (RAIZ / "dashboard" / "components" / "Sinalizadores.tsx").read_text(encoding="utf-8")


def test_o_tipo_declara_as_chaves_do_servidor():
    bloco = re.search(r"export type Sinalizador = \{(.*?)\n\};", API_TS, re.S)
    assert bloco is not None
    assert set(re.findall(r"^\s*(\w+):", bloco.group(1), re.M)) == {"regra", "evidencia", "detalhe"}


def test_as_regras_do_tipo_sao_as_do_servidor():
    bloco = re.search(r"export type RegraSinalizador =(.*?);", API_TS, re.S)
    assert bloco is not None
    assert tuple(re.findall(r'"(\w+)"', bloco.group(1))) == REGRAS


def test_o_rotulo_cobre_toda_regra():
    for regra in REGRAS:
        assert re.search(rf"\b{regra}:", TSX), regra


def test_a_tela_nao_redigita_limiar():
    for limiar in ("0,85", "0.85", "0,7", "0.7"):
        assert limiar not in TSX
