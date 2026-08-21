"""Mede como as tres classes do modelo caem nas tres categorias do NPS.

Existe porque a afirmacao que este script produz e uma AFIRMACAO NUMERICA do
relatorio -- "num lote equilibrado por construcao, o NPS sai em X" -- e ate
hoje ela vinha de uma medicao avulsa que ninguem conseguia rodar de novo.
Numero de banca que nao se reproduz nao e medida, e lembranca.

O que ele faz:

1. gera o lote do simulador, equilibrado por construcao (mesmo numero de
   conversas por rotulo) e com semente fixa -- rodar duas vezes da o mesmo
   resultado, no mesmo hardware ou noutro;
2. pontua com o motor REAL, os pesos de `modelos/`. Nao ha dublê aqui: o
   dublê pontua por contagem de palavra, e medir a regua do fusor com um
   numero que nao saiu do fusor seria pior do que nao medir;
3. imprime a distribuicao por categoria, o NPS e a mediana de score de cada
   classe -- as tres coisas juntas, porque so a ultima distingue "o modelo
   nao separa as classes" (defeito de treino) de "o modelo separa e a regua
   dobra o resultado" (defeito de composicao, que e o caso).

`--peso-neutro` mede uma regua DIFERENTE da vigente sem editar codigo. E o que
permite publicar o antes e o depois lado a lado. Ele e um instrumento, nao um
botao: nao escreve nada, nao toca no banco, e nao ha caminho da API ate aqui.
O peso de verdade e `fraus.fusor.PESO_NEUTRO_NO_SCORE`, constante -- ver o
design em docs/superpowers/specs/2026-08-20-nps-neutro-alinhado-design.md.

Como rodar:
    uv run python scripts/medir_faixas.py
    uv run python scripts/medir_faixas.py --peso-neutro 0.5    # a regua antiga
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from statistics import median

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from fraus.api.main import (CAMINHO_FUSOR, CAMINHO_MODELO_EMOCAO,  # noqa: E402
                            CAMINHO_MODELO_IRONIA, CAMINHO_MODELO_TEXTO)
from fraus.fusor import (NEUTRO, PESO_NEUTRO_NO_SCORE, SATISFEITO,  # noqa: E402
                         Fusor, montar_features, vetorizar)
from fraus.indicadores import (calcular_nps, categoria_nps,  # noqa: E402
                               nota_0_10)
from fraus.ingest.simulador import FRASES_POR_ROTULO, gerar_lote  # noqa: E402
from fraus.sinais.emocao import ClassificadorEmocao  # noqa: E402
from fraus.sinais.ironia import ClassificadorIronia  # noqa: E402
from fraus.sinais.texto import ClassificadorTexto  # noqa: E402

# 30 por classe, como a medicao original que este script substitui. O tamanho
# nao e arbitrario nem precisa ser grande: o que se mede aqui e uma composicao
# ARITMETICA entre score e faixa, nao a acuracia do modelo -- para acuracia,
# o lugar e o notebook 02, com holdout de verdade.
POR_CLASSE = 30
SEMENTE = 20260820

NOME_DA_CLASSE = {0: "insatisfeito", 1: "neutro", 2: "satisfeito"}
CATEGORIAS = ("detrator", "neutro", "promotor")


def pontuar_com_peso(fusor: Fusor, features: dict[str, float], peso_neutro: float) -> float:
    """`Fusor.pontuar`, mas com o peso do neutro por parametro.

    Duplica a formula de proposito, e a duplicacao e o ponto: a producao usa a
    constante e este script usa o parametro. Se ele CHAMASSE `pontuar`, nao
    haveria como medir a regua antiga sem editar o codigo da regua vigente --
    que e exatamente o que torna uma medicao "antes e depois" impossivel de
    confiar.

    Acessa o pipeline por dentro porque nao ha outra porta: `pontuar` ja aplica
    o peso. E o preco de manter o peso constante em producao, e ele e pago aqui,
    num script de medicao, e nao la.
    """
    probabilidades = fusor._pipeline.predict_proba([vetorizar(features)])[0]
    classes = list(fusor._pipeline.named_steps["modelo"].classes_)
    por_classe = dict(zip(classes, probabilidades))
    score = 100.0 * (por_classe.get(SATISFEITO, 0.0) + peso_neutro * por_classe.get(NEUTRO, 0.0))
    return max(0.0, min(100.0, score))


def medir(peso_neutro: float) -> dict:
    # Os tres classificadores sao obrigatorios desde o contrato de 35 features:
    # cada um propaga ModeloAusenteError, com mensagem propria, se faltar --
    # nunca pontuamos aqui com vetor incompleto (invariante 7).
    classificador = ClassificadorTexto(CAMINHO_MODELO_TEXTO)
    emocao = ClassificadorEmocao(CAMINHO_MODELO_EMOCAO)
    ironia = ClassificadorIronia(CAMINHO_MODELO_IRONIA)
    fusor = Fusor.carregar(CAMINHO_FUSOR)

    lote = gerar_lote(
        FRASES_POR_ROTULO, quantidade=POR_CLASSE * len(FRASES_POR_ROTULO), semente=SEMENTE
    )

    scores: list[float] = []
    scores_por_rotulo: dict[int, list[float]] = {rotulo: [] for rotulo in NOME_DA_CLASSE}
    # Matriz rotulo verdadeiro -> categoria atribuida. E ela que mostra ONDE a
    # classe neutra esta caindo, coisa que a contagem por categoria sozinha nao
    # diz: 4% de neutros pode ser o modelo errando ou a regua dobrando, e sao
    # consertos diferentes.
    matriz = {rotulo: dict.fromkeys(CATEGORIAS, 0) for rotulo in NOME_DA_CLASSE}

    for conversa, rotulo in lote:
        score = pontuar_com_peso(
            fusor, montar_features(conversa, classificador, emocao, ironia), peso_neutro
        )
        scores.append(score)
        scores_por_rotulo[rotulo].append(score)
        matriz[rotulo][categoria_nps(score)] += 1

    return {
        "peso_neutro": peso_neutro,
        "conversas": len(scores),
        "nps": calcular_nps(scores),
        "matriz": matriz,
        "medianas": {
            rotulo: median(valores) if valores else None
            for rotulo, valores in scores_por_rotulo.items()
        },
    }


def imprimir(resultado: dict) -> None:
    matriz = resultado["matriz"]
    total = resultado["conversas"]
    por_categoria = {
        categoria: sum(matriz[rotulo][categoria] for rotulo in matriz)
        for categoria in CATEGORIAS
    }

    print(f"\npeso do neutro no score: {resultado['peso_neutro']}")
    print(f"{total} conversas do simulador, {POR_CLASSE} por classe, semente {SEMENTE}\n")

    print("classe do modelo -> categoria de NPS")
    print(f"{'':>14} {'detrator':>10} {'neutro':>10} {'promotor':>10} {'mediana':>10}")
    for rotulo, nome in NOME_DA_CLASSE.items():
        linha = matriz[rotulo]
        mediana = resultado["medianas"][rotulo]
        print(
            f"{nome:>14} {linha['detrator']:>10} {linha['neutro']:>10} "
            f"{linha['promotor']:>10} {mediana:>10.2f}"
        )

    print(f"\n{'total':>14}", end="")
    for categoria in CATEGORIAS:
        pct = 100.0 * por_categoria[categoria] / total
        print(f" {por_categoria[categoria]:>4} ({pct:>4.1f}%)", end="")
    print(f"\n\nNPS inferido: {resultado['nps']:+.2f}")

    # O lote e equilibrado POR CONSTRUCAO: um terco de cada classe. Se a regua
    # nao dobrasse o resultado, promotores e detratores se cancelariam e o NPS
    # ficaria perto de zero. A distancia ate zero e o vies, e nomea-la e o
    # motivo deste script existir.
    print(f"esperado num lote equilibrado: ~0,00 -- vies de {resultado['nps']:+.2f}")

    neutro_puro = 100.0 * resultado["peso_neutro"]
    print(
        f"\nclasse neutra pura pontuaria {neutro_puro:.0f} "
        f"-> nota {nota_0_10(neutro_puro)} -> {categoria_nps(neutro_puro)}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--peso-neutro",
        type=float,
        default=PESO_NEUTRO_NO_SCORE,
        help=(
            "peso de P(neutro) no score, so para MEDIR outra regua. "
            f"Padrao: o vigente em producao ({PESO_NEUTRO_NO_SCORE})."
        ),
    )
    argumentos = parser.parse_args()
    if not 0.0 <= argumentos.peso_neutro <= 1.0:
        parser.error("o peso do neutro precisa estar entre 0 e 1")
    imprimir(medir(argumentos.peso_neutro))


if __name__ == "__main__":
    main()
