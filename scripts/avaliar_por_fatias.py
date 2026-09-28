"""Laudo por fatia do motor vigente, e a taxa de erro medida da cabeca de ironia.

Instrumento, nao botao -- o mesmo contrato de `medir_faixas.py` e
`conferir_fusor.py`: nao escreve em `modelos/`, nao toca no banco, so imprime.
O que ele imprime alimenta `docs/cartao-do-modelo.md`, e o cartao cita a semente
para qualquer um reproduzir o numero.

Tres partes:

1. ACERTO POR FATIA do fusor, sobre conversas do simulador com rotulo. Mede onde
   o modelo erra DENTRO do dominio sintetico -- nao desempenho em atendimento
   real, que o projeto nao tem como medir (nao ha corpus PT-BR rotulado de
   atendimento com timestamps).
2. CONVERSA SO DE CORTESIA ("ok, obrigado"). Nao ha rotulo verdadeiro para ela
   -- a mesma fala fecha atendimento bom e ruim --, entao o laudo mostra a
   CATEGORIA que o Fraus da, nao uma acuracia inventada.
3. CONTRA-EXEMPLOS DA IRONIA: fala sincera com marcador de discurso e ironia
   sem marcador. Publicar a taxa de erro em vez de esconder a cabeca.

Uso:
    uv run python scripts/avaliar_por_fatias.py              # FRAUS_BACKEND vale
    FRAUS_BACKEND=onnx uv run python scripts/avaliar_por_fatias.py --n 600
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from fraus.api.caminhos import CAMINHO_FUSOR, backend_declarado  # noqa: E402
from fraus.avaliacao_ironia import (IRONIAS_SEM_MARCADOR,  # noqa: E402
                                    SINCERAS_COM_MARCADOR,
                                    avaliar_probabilidades)
from fraus.api.main import montar_classificadores  # noqa: E402
from fraus.fatias import fatias_de, metricas_por_fatia  # noqa: E402
from fraus.fusor import Fusor, montar_features  # noqa: E402
from fraus.indicadores import FAIXAS_NPS, categoria_nps, nota_0_10  # noqa: E402
from fraus.ingest.simulador import FRASES_POR_ROTULO, gerar_lote  # noqa: E402
from fraus.modelos import Conversa, Mensagem  # noqa: E402
from fraus.sinais.ironia import IRONICO  # noqa: E402

# Diferente das sementes de `medir_faixas` (20260820) e de `comparar_backends`
# (20260910): um laudo que reusa o lote de outro nao e medida independente.
SEMENTE = 20260915

CORTESIAS = ["ok, obrigado", "valeu", "ta bom", "ok", "obrigada", "certo, entendi"]


def _conversas_de_cortesia() -> list[Conversa]:
    """Uma fala do cliente, so cortesia, com resposta do bot em 10 s."""
    inicio = datetime(2026, 9, 15, 10, tzinfo=timezone.utc)
    return [
        Conversa(
            id=f"cortesia-{i}",
            canal="simulador",
            iniciada_em=inicio,
            mensagens=[
                Mensagem(autor="bot", texto="posso ajudar em algo mais?", enviada_em=inicio),
                Mensagem(autor="cliente", texto=texto, enviada_em=inicio + timedelta(seconds=10)),
            ],
        )
        for i, texto in enumerate(CORTESIAS)
    ]


def _tabela(metricas: dict) -> str:
    linhas = ["| eixo | fatia | n | acurácia | F1-macro |", "|---|---|---|---|---|"]
    for eixo, valores in metricas.items():
        for valor, m in valores.items():
            linhas.append(
                f"| {eixo} | {valor} | {m['n']} | {m['acuracia']:.3f} | {m['f1_macro']:.3f} |"
            )
    return "\n".join(linhas)


def main() -> int:
    argumentos = argparse.ArgumentParser(description=__doc__)
    argumentos.add_argument("--n", type=int, default=600)
    opcoes = argumentos.parse_args()

    backend = backend_declarado()
    texto, emocao, ironia = montar_classificadores(backend)
    fusor = Fusor.carregar(CAMINHO_FUSOR)
    print(f"backend={backend} n={opcoes.n} semente={SEMENTE}\n")

    registros = []
    for conversa, rotulo in gerar_lote(FRASES_POR_ROTULO, opcoes.n, semente=SEMENTE):
        if not conversa.tem_sinal_cliente:
            continue
        predito = fusor.prever(montar_features(conversa, texto, emocao))
        registros.append((fatias_de(conversa), rotulo, predito))

    geral = sum(r == p for _, r, p in registros) / len(registros)
    print(f"## 1. Acerto por fatia (simulador)\n\ngeral: acurácia {geral:.3f} em {len(registros)} conversas\n")
    print(_tabela(metricas_por_fatia(registros)))

    print("\n## 2. Conversa só de cortesia (sem rótulo verdadeiro)\n")
    print("| fala | score | nota | categoria |\n|---|---|---|---|")
    for conversa in _conversas_de_cortesia():
        fala = conversa.mensagens_cliente[0].texto
        # A MESMA porta do Motor: sem sinal nao passa pelo fusor (invariante 2).
        if not conversa.tem_sinal_cliente:
            print(f"| {fala} | — | — | sem sinal |")
            continue
        score = fusor.pontuar(montar_features(conversa, texto, emocao))
        print(f"| {fala} | {score:.1f} | {nota_0_10(score)} | {categoria_nps(score, FAIXAS_NPS)} |")

    print("\n## 3. Contra-exemplos da ironia\n")
    sinceras = [p[IRONICO] for p in ironia.prever_mensagens(SINCERAS_COM_MARCADOR)]
    ironicas = [p[IRONICO] for p in ironia.prever_mensagens(IRONIAS_SEM_MARCADOR)]
    regua = avaliar_probabilidades(sinceras, ironicas)
    falso_positivo = regua.taxa_falso_positivo
    falso_negativo = regua.taxa_falso_negativo
    print(f"sincera com marcador marcada como irônica: {falso_positivo:.0%} ({len(sinceras)} falas)")
    print(f"irônica sem marcador que passou como sincera: {falso_negativo:.0%} ({len(ironicas)} falas)\n")
    print("| tipo | fala | P(irônico) |\n|---|---|---|")
    for rotulo, falas, probs in (("sincera", SINCERAS_COM_MARCADOR, sinceras),
                                 ("irônica", IRONIAS_SEM_MARCADOR, ironicas)):
        for fala, p in zip(falas, probs):
            print(f"| {rotulo} | {fala} | {p:.3f} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
