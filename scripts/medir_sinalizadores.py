"""Instrumento do E5: precisao e recall por regra, com IC de Wilson.

Tres fontes, sempre reportadas separadas:
- casos construidos (fraus/dados/casos_sinalizadores.py): verificam a
  implementacao, NAO medem qualidade -- foram escritos para disparar;
- amostra anotada (--anotada): a unica que mede. Sem ela, "nao verificado";
- simulador (--simulador N): so a taxa de disparo, porque nao ha rotulo de regra.

Nao grava nada. Uso: uv run python scripts/medir_sinalizadores.py [--anotada a.jsonl] [--simulador 600]
"""

import argparse
import json
import sys
from pathlib import Path

from fraus.api.rotas.confianca import wilson
from fraus.dados.casos_sinalizadores import CASOS
from fraus.modelos import Conversa
from fraus.sinalizadores import REGRAS, sinalizadores


def _disparou(regra, conversa):
    return regra in [s["regra"] for s in sinalizadores(conversa) or []]


def medir(casos):
    res = {}
    for regra in REGRAS:
        vp = fp = fn = 0
        for r, _tipo, conversa, deve in casos:
            if r != regra:
                continue
            d = _disparou(regra, conversa)
            vp += d and deve
            fp += d and not deve
            fn += (not d) and deve
        res[regra] = {
            "vp": vp, "fp": fp, "fn": fn,
            "precisao": vp / (vp + fp) if vp + fp else None,
            "recall": vp / (vp + fn) if vp + fn else None,
            "ic_precisao": wilson(vp, vp + fp) if vp + fp else None,
            "ic_recall": wilson(vp, vp + fn) if vp + fn else None,
        }
    return res


def carregar_anotada(caminho: Path):
    """JSONL: {"conversa": {...}, "esperadas": [regras], "anotador": "..."}.
    Cada linha vira um caso por regra: dispara se a regra esta em `esperadas`."""
    casos, anotadores = [], set()
    for n, linha in enumerate(caminho.read_text(encoding="utf-8").splitlines(), start=1):
        if not linha.strip():
            continue
        item = json.loads(linha)
        if not item.get("anotador"):
            raise ValueError(f"linha {n}: anotador ausente")
        desconhecidas = [r for r in item["esperadas"] if r not in REGRAS]
        if desconhecidas:
            raise ValueError(f"linha {n}: regra desconhecida em esperadas: {desconhecidas[0]}")
        conversa = Conversa.model_validate(item["conversa"])
        anotadores.add(item["anotador"])
        for regra in REGRAS:
            casos.append((regra, "anotada", conversa, regra in item["esperadas"]))
    if not casos:
        raise ValueError("amostra anotada vazia")
    return casos, anotadores


def _fmt(v):
    return "n/d" if v is None else f"{v:.2f}"


def _fmt_ic(ic):
    return "n/d" if ic is None else f"[{ic[0]:.2f}, {ic[1]:.2f}]"


def _tabela(res, rotulo=""):
    sufixo = f" ({rotulo})" if rotulo else ""
    print(f"{'regra':28} {'vp':>3} {'fp':>3} {'fn':>3}  "
          f"precisão{sufixo} (IC 95%)  recall{sufixo} (IC 95%)")
    for regra, r in res.items():
        print(f"{regra:28} {r['vp']:>3} {r['fp']:>3} {r['fn']:>3}  "
              f"{_fmt(r['precisao'])} {_fmt_ic(r['ic_precisao']):16}  "
              f"{_fmt(r['recall'])} {_fmt_ic(r['ic_recall'])}")


def principal(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--anotada", type=Path)
    p.add_argument("--simulador", type=int, default=0)
    args = p.parse_args(argv)

    print(f"Casos construídos (n = {len(CASOS)}): verifica a implementação, não mede qualidade.")
    _tabela(medir(CASOS), "construídos")
    print()
    if args.anotada is None:
        print("Amostra anotada: não verificado — fonte pendente (João). Rode com --anotada arquivo.jsonl.")
    else:
        casos, anotadores = carregar_anotada(args.anotada)
        n = len(casos) // len(REGRAS)
        print(f"Amostra anotada (n = {n} conversas; anotador(es): {', '.join(sorted(anotadores))}):")
        _tabela(medir(casos))
    if args.simulador:
        from fraus.ingest.simulador import gerar_lote
        frases = {0: ["pessimo atendimento"], 1: ["ok"], 2: ["otimo, resolveu"]}
        lote = [c for c, _ in gerar_lote(frases, args.simulador, semente=20261014)]
        print(f"\nSimulador (n = {len(lote)}, sem rótulo de regra — só taxa de disparo):")
        for regra in REGRAS:
            k = sum(_disparou(regra, c) for c in lote)
            print(f"  {regra:28} {k}/{len(lote)}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
