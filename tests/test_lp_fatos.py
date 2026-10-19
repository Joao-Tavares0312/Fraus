"""A LP publica numeros do motor; eles nao podem divergir do codigo.

POR QUE este teste existe: os contadores da pagina inicial afirmam quantas
features o fusor le. Se `NOMES_FEATURES` mudar e a LP nao, a pagina publica
passa a mentir sem nenhum erro -- o mesmo tipo de divergencia silenciosa que a
invariante 9 proibe dentro do motor.
"""

import re
from pathlib import Path

from fraus.fusor import NOMES_FEATURES

CORE = Path(__file__).resolve().parents[1] / "dashboard" / "lib" / "lp-nova" / "coreografia.ts"


def _fato(rotulo: str) -> int:
    texto = CORE.read_text(encoding="utf-8")
    achado = re.search(r'valor:\s*(\d+),\s*rotulo:\s*"' + re.escape(rotulo) + '"', texto)
    assert achado, f"fato '{rotulo}' sumiu de {CORE.name}"
    return int(achado.group(1))


def test_features_da_lp_batem_com_o_fusor():
    assert _fato("features no fusor") == len(NOMES_FEATURES)


def test_lp_nao_anuncia_llm_na_inferencia():
    assert _fato("LLMs na inferência") == 0
