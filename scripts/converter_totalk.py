"""Converte um export da Totalk para o CSV que o Fraus importa.

    uv run python scripts/converter_totalk.py ENTRADA.csv [-o saida.csv]

Por padrao grava em `dados_brutos/`, que e a unica pasta de onde a API aceita
importar -- assim o arquivo ja nasce no lugar onde a tela de Integracoes vai
encontra-lo.

O relatorio impresso NAO e enfeite: ele mostra o que a conversao INFERIU (quem
e atendente humano, quantas mensagens da empresa vieram sem assinatura) e o que
foi ignorado. Taxa de contencao e escalonamento dependem dessas inferencias, e
conversao que nao mostra o que adivinhou entrega numero sem lastro.
"""

from __future__ import annotations

import argparse
import sys
from datetime import timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from fraus.ingest.totalk import (FUSO_PADRAO, converter,  # noqa: E402
                                 para_csv_canonico)


def main() -> int:
    analisador = argparse.ArgumentParser(description=__doc__)
    analisador.add_argument("entrada", type=Path, help="CSV exportado da Totalk")
    analisador.add_argument(
        "-o", "--saida", type=Path, default=None,
        help="destino (padrao: dados_brutos/<nome>-fraus.csv)",
    )
    analisador.add_argument(
        "--fuso", type=int, default=-3,
        help="deslocamento em horas do fuso do export (padrao: -3, America/Sao_Paulo)",
    )
    analisador.add_argument(
        "--agente", action="append", default=[],
        help="nome de atendente HUMANO; pode repetir. Sem isto, a conversao infere.",
    )
    argumentos = analisador.parse_args()

    if not argumentos.entrada.is_file():
        print(f"arquivo nao encontrado: {argumentos.entrada}", file=sys.stderr)
        return 1

    fuso = timezone(timedelta(hours=argumentos.fuso)) if argumentos.fuso != -3 else FUSO_PADRAO

    with argumentos.entrada.open(encoding="utf-8-sig", newline="") as arquivo:
        try:
            resultado = converter(arquivo, fuso=fuso, agentes_humanos=argumentos.agente)
        except KeyError as erro:
            print(f"coluna ausente no export: {erro.args[0]}", file=sys.stderr)
            return 1

    if not resultado.conversas:
        print("nenhuma conversa valida no arquivo", file=sys.stderr)
        return 1

    saida = argumentos.saida or (
        RAIZ / "dados_brutos" / f"{argumentos.entrada.stem}-fraus.csv"
    )
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(para_csv_canonico(resultado.conversas), encoding="utf-8")

    total_mensagens = sum(len(c.mensagens) for c in resultado.conversas)
    escaladas = sum(1 for c in resultado.conversas if c.escalou_para_humano)
    print(f"{len(resultado.conversas)} conversa(s), {total_mensagens} mensagem(ns) -> {saida}")
    print(f"  escalaram para humano: {escaladas}")

    if resultado.agentes_detectados:
        print(f"  atendentes INFERIDOS: {', '.join(resultado.agentes_detectados)}")
        print("    (se algum destes for automacao, rode de novo com --agente para os reais)")
    if resultado.mensagens_sem_prefixo:
        print(
            f"  {resultado.mensagens_sem_prefixo} mensagem(ns) da empresa sem assinatura, "
            "contadas como bot"
        )
    if resultado.ignoradas:
        print(f"  {len(resultado.ignoradas)} linha(s) ignorada(s):")
        for linha in resultado.ignoradas[:10]:
            print(f"    linha {linha.numero_linha}: {linha.motivo}")

    print()
    print("O texto das mensagens vai INTEIRO para o banco. Nome, telefone e e-mail")
    print("do contato NAO -- o modelo canonico nao tem campo para eles. Ainda assim,")
    print("cliente costuma dizer nome e documento no meio da conversa: trate o banco")
    print("resultante como dado pessoal.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
