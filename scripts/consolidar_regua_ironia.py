"""Respostas da pagina de anotacao -> regua congelada em fraus/dados/.

Uso:
    uv run python scripts/consolidar_regua_ironia.py ARQUIVO.json [ARQUIVO.json ...]

Cada ARQUIVO.json e uma lista de registros {anotador, frase_id, resposta,
instante}; as listas sao CONCATENADAS antes de consolidar. Hoje sao duas
origens:

- `fraus/dados/anotacao_regua/anotador-claude-ai.json` -- a primeira rodada,
  feita na pagina do claude.ai (anotador `claude-ai-1`);
- o export de `GET /anotacao/respostas` (`scripts/exportar_anotacao.py`), com
  os anotadores dos links do Fraus.

Exemplo:
    uv run python scripts/consolidar_regua_ironia.py \
        fraus/dados/anotacao_regua/anotador-claude-ai.json respostas-fraus.json
"""

import csv
import json
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from fraus.avaliacao_ironia import (CAMINHO_META_REGUA, CAMINHO_REGUA_PARES,  # noqa: E402
                                    FraseDaRegua, carregar_rascunho, impressao_dos_rotulos,
                                    variantes_de_invariancia)
from fraus.consolidacao_regua import (RESPOSTAS, conferir_ids, decidir_pares, fleiss_kappa,  # noqa: E402
                                      ultimas_respostas)
from fraus.divisao import impressao_dos_textos  # noqa: E402

DADOS = RAIZ / "fraus" / "dados"


def _gravar(caminho, campos, linhas):
    with open(caminho, "w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(linhas)


def _kappa(frases, respostas):
    n = max((len(r) for r in respostas.values()), default=0)
    contagens = [
        [respostas[f.frase_id].count(c) for c in RESPOSTAS]
        for f in frases if len(respostas.get(f.frase_id, [])) == n
    ]
    return fleiss_kappa(contagens) if n > 1 and contagens else None


def carregar_registros(caminhos) -> list[dict]:
    """Concatena as listas de registros de varios arquivos JSON, na ordem dada."""
    registros: list[dict] = []
    for caminho in caminhos:
        registros.extend(json.loads(Path(caminho).read_text(encoding="utf-8")))
    return registros


def main(caminhos_respostas: list[str]) -> None:
    registros = carregar_registros(caminhos_respostas)
    rascunho = carregar_rascunho()
    conferir_ids(registros, rascunho)
    respostas = ultimas_respostas(registros)
    mantidas, descartadas = decidir_pares(rascunho, respostas)
    _gravar(CAMINHO_REGUA_PARES, ["par_id", "estrato", "texto", "rotulo", "concordancia"], mantidas)
    _gravar(DADOS / "regua_ironia_descartes.csv",
            ["par_id", "estrato", "rotulo", "texto", "motivo", "respostas"], descartadas)
    frases = [FraseDaRegua(**m) for m in mantidas]
    _gravar(DADOS / "regua_ironia_invariancia.csv",
            ["frase_origem", "variante", "texto", "rotulo"], variantes_de_invariancia(frases))
    meta = {
        "anotadores": len({r["anotador"] for r in registros}),
        "kappa": _kappa(rascunho, respostas),
        "kappa_por_estrato": {
            estrato: _kappa([f for f in rascunho if f.estrato == estrato], respostas)
            for estrato in ("elogio", "reclamacao", "neutra")
        },
        "pares": len({m["par_id"] for m in mantidas}),
        "descartados": len({d["par_id"] for d in descartadas}),
        "data": date.today().isoformat(),
        "impressao": impressao_dos_textos(m["texto"] for m in mantidas),
        "impressao_rotulos": impressao_dos_rotulos(
            (m["par_id"], m["rotulo"], m["texto"]) for m in mantidas
        ),
        "tipo_avaliacao": "regua_de_pares_rotulada_as_cegas_rascunho_autoral",
    }
    CAMINHO_META_REGUA.write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
