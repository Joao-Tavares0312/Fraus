"""A consolidacao junta respostas de mais de uma origem.

A primeira rodada de anotacao foi na pagina do claude.ai (exportada para
`fraus/dados/anotacao_regua/`); as seguintes vem de `GET /anotacao/respostas`.
O script recebe os dois arquivos e concatena as listas.
"""

import json
from pathlib import Path

from fraus.avaliacao_ironia import carregar_rascunho
from scripts.consolidar_regua_ironia import carregar_registros

RAIZ = Path(__file__).resolve().parents[1]
DO_CLAUDE_AI = RAIZ / "fraus" / "dados" / "anotacao_regua" / "anotador-claude-ai.json"


def registro(anotador, frase_id="f1"):
    return {"anotador": anotador, "frase_id": frase_id, "resposta": "ironico",
            "instante": "2026-10-08T10:00:00+00:00"}


def test_carregar_registros_concatena_varios_arquivos(tmp_path):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text(json.dumps([registro("x")]), encoding="utf-8")
    b.write_text(json.dumps([registro("y"), registro("z")]), encoding="utf-8")
    assert [r["anotador"] for r in carregar_registros([a, b])] == ["x", "y", "z"]


def test_export_do_claude_ai_esta_versionado_sem_id_de_conta():
    registros = json.loads(DO_CLAUDE_AI.read_text(encoding="utf-8"))
    assert len(registros) == 300
    assert {r["anotador"] for r in registros} == {"claude-ai-1"}
    assert all(set(r) == {"anotador", "frase_id", "resposta", "instante"} for r in registros)
    assert {r["frase_id"] for r in registros} == {f.frase_id for f in carregar_rascunho()}
    assert "u_" not in DO_CLAUDE_AI.read_text(encoding="utf-8")
