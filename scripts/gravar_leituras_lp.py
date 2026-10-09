"""Grava as leituras da LP nova (`/leitura`) com o motor REAL de producao.

A LP mostra o Fraus lendo cinco conversas sinteticas (`dados_lp/*.csv`). Um
visitante anonimo nao pode chamar a API -- a analise exige credencial desde a
PR #78 --, entao a leitura e feita UMA vez, aqui, e versionada com a
procedencia: quando, contra qual API e com qual modelo. A tela escreve essa
etiqueta; leitura sem lastro seria numero inventado.

Usa `POST /analisar`, a rota que nao grava nada no banco.

    FRAUS_LP_API=https://... FRAUS_LP_TOKEN=... uv run python scripts/gravar_leituras_lp.py

O token vem do ambiente e nunca e escrito em arquivo. Sem modelo carregado a
API responde erro e o script falha alto (invariante 7): nao ha dublê.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASTA_CSV = RAIZ / "dados_lp"
DESTINO = RAIZ / "dashboard" / "lib" / "lp-nova" / "leituras.json"

IDS = ("obrigado", "ironia", "espera", "promotor", "sem-sinal")
SEM_CLIENTE = "sem-sinal"

# So o que a pagina mostra. `vocabulario` fica de fora: a referencia dele sao
# contagens do banco de producao, e isso nao pertence a uma pagina publica.
CHAVES = ("score", "nota", "categoria", "motivo_sem_sinal", "mensagens", "contribuicoes", "conversa")


class LeituraRecusada(RuntimeError):
    """O motor devolveu algo que a LP nao pode exibir como leitura real."""


def montar_conjunto(respostas: dict, modelo: str, agora: str, api: str, shas: dict) -> dict:
    leituras = []
    for id_ in IDS:
        if id_ not in respostas:
            raise LeituraRecusada(f"falta a leitura {id_}")
        analises = respostas[id_].get("analises") or []
        if len(analises) != 1:
            raise LeituraRecusada(f"{id_}: esperada 1 analise, vieram {len(analises)}")
        analise = analises[0]
        faltando = [c for c in (*CHAVES, "score") if c not in analise]
        if faltando:
            raise LeituraRecusada(f"{id_}: a resposta nao trouxe {faltando}; API antiga ou contrato mudou")
        sem_nota = analise["score"] is None
        # A conversa sem fala do cliente PRECISA sair sem nota (invariante 2);
        # as outras PRECISAM sair com nota. Qualquer troca e motor errado.
        if id_ == SEM_CLIENTE and not sem_nota:
            raise LeituraRecusada(f"{id_}: conversa sem cliente voltou com score {analise['score']}")
        # Score nulo tambem sai de transcricao sem horario; sem cliente e so com o motivo.
        if id_ == SEM_CLIENTE and not analise["motivo_sem_sinal"]:
            raise LeituraRecusada(f"{id_}: score nulo sem motivo_sem_sinal; nao e a ausencia de cliente")
        if id_ != SEM_CLIENTE and sem_nota:
            raise LeituraRecusada(f"{id_}: conversa com cliente voltou sem score")
        leituras.append({"id": id_, **{c: analise[c] for c in CHAVES}, "sha256": shas[id_]})
    return {
        "procedencia": {"gravado_em": agora, "api": api, "modelo": modelo},
        "leituras": leituras,
    }


def exigir_https(api: str) -> str:
    """O Bearer de producao nao trafega em claro."""
    if not api.startswith("https://"):
        raise LeituraRecusada(f"FRAUS_LP_API precisa ser https:// (veio {api!r}): o token iria em claro")
    return api.rstrip("/")


class SemRedirect(urllib.request.HTTPRedirectHandler):
    """O urllib copia o Authorization ao seguir redirect, ate para outro host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise LeituraRecusada(f"a API respondeu {code} para {newurl}; redirect nao e seguido com o token")


_ABRIR = urllib.request.build_opener(SemRedirect())


def _pedir(api: str, token: str, caminho: str, corpo: dict | None = None) -> dict:
    dados = json.dumps(corpo).encode("utf-8") if corpo is not None else None
    pedido = urllib.request.Request(
        f"{api.rstrip('/')}{caminho}",
        data=dados,
        method="POST" if dados is not None else "GET",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with _ABRIR.open(pedido, timeout=180) as resposta:
        return json.loads(resposta.read())


def identidade_do_modelo(ficha: dict) -> str:
    """Impressao digital dos pesos do fusor que a API serviu.

    `GET /modelo` nao tem campo de versao, e inventar um ("v2") seria rotulo
    sem lastro. Os pesos SAO o modelo que pontuou: o hash deles muda quando
    o fusor muda, e mais nada muda o hash.
    """
    pesos = ficha.get("importancias")
    if not pesos:
        raise LeituraRecusada("GET /modelo veio sem importancias; sem pesos nao ha identidade")
    canonico = json.dumps(pesos, sort_keys=True, separators=(",", ":"))
    return "fusor:" + hashlib.sha256(canonico.encode("utf-8")).hexdigest()[:12]


def main() -> int:
    api = os.environ.get("FRAUS_LP_API")
    token = os.environ.get("FRAUS_LP_TOKEN")
    if not api or not token:
        print("defina FRAUS_LP_API e FRAUS_LP_TOKEN", file=sys.stderr)
        return 2
    api = exigir_https(api)
    respostas, shas = {}, {}
    for id_ in IDS:
        bruto = (PASTA_CSV / f"{id_}.csv").read_bytes()
        shas[id_] = hashlib.sha256(bruto).hexdigest()
        respostas[id_] = _pedir(api, token, "/analisar", {"csv": bruto.decode("utf-8"), "nome": f"{id_}.csv"})
        print(f"lida {id_}")
    modelo = identidade_do_modelo(_pedir(api, token, "/modelo"))
    agora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conjunto = montar_conjunto(respostas, modelo=modelo, agora=agora, api=api, shas=shas)
    # A pagina mostra quando o motor discorda do roteiro; aqui so avisa, sem
    # recusar -- recusar seria escolher a leitura a dedo.
    roteiro = {"obrigado": "detrator", "ironia": "detrator", "espera": "detrator", "promotor": "promotor", "sem-sinal": None}
    for leitura in conjunto["leituras"]:
        if leitura["categoria"] != roteiro[leitura["id"]]:
            print(f"aviso: {leitura['id']} lida como {leitura['categoria']}, roteiro {roteiro[leitura['id']]}")
    DESTINO.write_text(json.dumps(conjunto, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"gravado {DESTINO.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
