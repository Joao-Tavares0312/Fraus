"""Compara torch e ONNX int8 NO QUE IMPORTA: score, nota e categoria.

Por que este script existe separado da conversao. `encolher_modelos.py` mede
diferenca de PROBABILIDADE, que e a medida certa para decidir se a quantizacao
estragou um classificador -- e a medida ERRADA para decidir se o Fraus mudou de
opiniao. O score e uma projecao das tres probabilidades num eixo 0-100, a nota
e o score arredondado, e a categoria e a nota caindo numa faixa. Cada degrau
desses absorve ou amplifica a diferenca do degrau anterior.

Uma diferenca de 0,10 em probabilidade pode nao mover nota nenhuma, ou pode
mover uma conversa de neutro para promotor. A unica forma de saber e medir a
ponta, com o motor inteiro montado dos dois jeitos, sobre as mesmas conversas.

E o criterio de aceite do encolhimento inteiro:

    o que nao pode mudar    a CATEGORIA de uma conversa
    o que se tolera medir   deslocamento de score, declarado

Uso:  uv run python scripts/comparar_backends.py [--n 60]
"""

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from fraus.fusor import Fusor
from fraus.indicadores import categoria_nps, nota_0_10
from fraus.ingest.simulador import FRASES_POR_ROTULO, gerar_lote
from fraus.motor import Motor
from fraus.sinais.emocao import ClassificadorEmocao
from fraus.sinais.ironia import ClassificadorIronia
from fraus.sinais.onnx import ClassificadorOnnx, classificadores_multitarefa
from fraus.sinais.texto import ClassificadorTexto


def _motor_torch() -> Motor:
    base = RAIZ / "modelos"
    return Motor(
        ClassificadorTexto(base / "bertimbau-satisfacao"),
        Fusor.carregar(base / "fusor.joblib"),
        ClassificadorEmocao(base / "bertimbau-emocao"),
        ClassificadorIronia(base / "bertimbau-ironia"),
    )


def _motor_onnx() -> Motor:
    """O MESMO fusor, so os tres classificadores trocados.

    O fusor nao entra na conversao: ele e um `LogisticRegression` de 4 KB. Um
    artefato de 4 KB nao paga a complexidade de ter duas versoes -- e mante-lo
    identico isola a variavel: o que mudar na comparacao veio dos BERTimbau.
    """
    onnx = RAIZ / "modelos-onnx"
    return Motor(
        ClassificadorOnnx(onnx / "bertimbau-satisfacao"),
        Fusor.carregar(RAIZ / "modelos" / "fusor.joblib"),
        ClassificadorOnnx(onnx / "bertimbau-emocao"),
        ClassificadorOnnx(onnx / "bertimbau-ironia"),
    )


def _motor_multitarefa() -> Motor:
    texto, emocao, ironia = classificadores_multitarefa(
        RAIZ / "modelos-onnx" / "bertimbau-multitarefa-candidato"
    )
    return Motor(
        texto,
        Fusor.carregar(RAIZ / "modelos" / "fusor.joblib"),
        emocao,
        ironia,
    )


def main() -> int:
    argumentos = argparse.ArgumentParser(description=__doc__)
    argumentos.add_argument("--n", type=int, default=60, help="conversas a comparar")
    argumentos.add_argument(
        "--multitarefa",
        action="store_true",
        help="comparar com modelos-onnx/bertimbau-multitarefa-candidato",
    )
    opcoes = argumentos.parse_args()

    # O simulador e DETERMINISTICO, entao esta comparacao e reproduzivel por
    # quem quiser conferir o numero -- ao contrario de uma amostra do banco,
    # que depende do que cada um importou.
    conversas = [c for c, _ in gerar_lote(FRASES_POR_ROTULO, opcoes.n, semente=20260910)]
    print(f"comparando {len(conversas)} conversas...", file=sys.stderr)

    torch_, onnx_ = _motor_torch(), (
        _motor_multitarefa() if opcoes.multitarefa else _motor_onnx()
    )

    diferencas, mudou_nota, mudou_categoria = [], [], []
    for conversa in conversas:
        a = torch_.pontuar_conversa(conversa)
        b = onnx_.pontuar_conversa(conversa)
        if a is None or b is None:
            # Sem fala do cliente os dois devolvem None, e discordar AQUI seria
            # muito pior que discordar de score: seria um backend inventando
            # sinal onde nao ha. Por isso a checagem e de igualdade.
            assert a == b, f"{conversa.id}: um backend pontuou e o outro nao"
            continue
        diferencas.append(abs(a - b))
        if nota_0_10(a) != nota_0_10(b):
            mudou_nota.append((conversa.id, a, b))
        if categoria_nps(a) != categoria_nps(b):
            mudou_categoria.append((conversa.id, a, b, categoria_nps(a), categoria_nps(b)))

    n = len(diferencas)
    print(f"\n{n} conversas com score nos dois backends", file=sys.stderr)
    print(f"  desvio medio de score : {sum(diferencas) / n:6.3f} pontos (0-100)", file=sys.stderr)
    print(f"  desvio MAXIMO         : {max(diferencas):6.3f} pontos", file=sys.stderr)
    print(f"  notas diferentes      : {len(mudou_nota)} de {n}", file=sys.stderr)
    print(f"  CATEGORIAS diferentes : {len(mudou_categoria)} de {n}", file=sys.stderr)

    for identificador, a, b in mudou_nota[:5]:
        print(f"    nota: {identificador} {a:.2f} -> {b:.2f} "
              f"({nota_0_10(a)} -> {nota_0_10(b)})", file=sys.stderr)
    for identificador, a, b, ca, cb in mudou_categoria[:5]:
        print(f"    CATEGORIA: {identificador} {a:.2f} -> {b:.2f} ({ca} -> {cb})",
              file=sys.stderr)

    if mudou_categoria:
        print("\nRECUSADO: o backend quantizado muda a CATEGORIA de pelo menos "
              "uma conversa. Categoria e o veredito que a tela mostra e que o "
              "NPS agrega -- trocar o backend nao pode trocar o veredito.",
              file=sys.stderr)
        return 1
    print("\nACEITO: nenhuma conversa muda de categoria.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
