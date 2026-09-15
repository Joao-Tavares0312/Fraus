"""Por que tres features tem o sinal "errado", e por que isso nao e um defeito.

A PERGUNTA QUE A BANCA VAI FAZER. `scripts/conferir_fusor.py` marca tres
features como suspeitas desde o fusor de 35, e o aviso sobreviveu a todos os
retreinos ate hoje:

    texto_prob_satisfeito_ultima   -0,4889   (esperado positivo)
    emoji_frac_positivos           -0,1911   (esperado positivo)
    emoji_frac_negativos           +0,5887   (esperado negativo)

Lido isoladamente, o terceiro diz "mais emoji negativo empurra para
satisfeito", que e absurdo. Este laudo mostra que a leitura isolada e que esta
errada, e mede o que de fato acontece.

A HIPOTESE, E ELA E TESTAVEL. Cada uma das tres tem uma IRMA FORTE que carrega
o mesmo sinal com peso maior e com o sinal certo:

    emoji_score_medio              +1,5511   contra as duas de emoji
    texto_prob_satisfeito_media    +2,7780   contra a de texto

Em regressao logistica, features correlacionadas dividem um efeito unico: a
mais forte fica com ele, e a irmã redundante recebe um peso pequeno de
CORRECAO, com sinal frequentemente oposto. O coeficiente dela deixa de
significar "o efeito desta feature" e passa a significar "o ajuste que falta
depois que a irmã ja falou". Nesse regime, sinal de coeficiente individual nao
e interpretavel -- o que e interpretavel e o efeito LIQUIDO da familia.

O QUE ESTE LAUDO MEDE, entao, sao duas coisas:

1. **A correlacao dentro de cada familia**, sobre conversas de verdade. Se as
   irmas nao forem correlacionadas, a hipotese cai e o defeito e outro.
2. **O efeito LIQUIDO da familia**, varrendo o sinal que ela mede. E a unica
   pergunta que importa para o produto: quando o cliente manda emoji mais
   positivo, a nota sobe ou desce?

NAO CARREGA BERTIMBAU. As features de emoji saem de `features_emoji` sobre
conversas montadas aqui -- valores REAIS, nao inventados. As de texto entram
como probabilidade literal, porque e assim que a cabeca de texto as entrega.
Instrumento, nao botao: nao escreve nada, nao toca no banco. Mesmo molde de
`scripts/conferir_fusor.py` e `scripts/medir_dominio_do_tempo.py`.

Como rodar:
    uv run python scripts/investigar_sinais_invertidos.py
"""

from __future__ import annotations

import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fraus.api.caminhos import CAMINHO_FUSOR  # noqa: E402
from fraus.fusor import FEATURES_EM_LOG, NOMES_FEATURES, Fusor  # noqa: E402
from fraus.ingest.simulador import FRASES_POR_ROTULO, gerar_lote  # noqa: E402
from fraus.modelos import Conversa, Mensagem  # noqa: E402
from fraus.sinais.emoji import features_emoji  # noqa: E402

FAMILIA_EMOJI = (
    "emoji_score_medio",
    "emoji_frac_positivos",
    "emoji_frac_negativos",
    "emoji_contagem",
    "emoji_posicao_relativa_media",
)
FAMILIA_TEXTO_SATISFEITO = ("texto_prob_satisfeito_media", "texto_prob_satisfeito_ultima")

# Emojis com polaridade conhecida no Emoji Sentiment Ranking, os mesmos que o
# simulador usa. A varredura vai de "so negativo" a "so positivo" trocando um
# emoji por vez -- assim as tres features de emoji se movem JUNTAS, do jeito
# que se movem numa conversa de verdade. Varrer uma feature sozinha, deixando
# as irmas paradas, mediria um mundo que nao existe.
POSITIVOS = ["😍", "😊", "👏", "👍"]
NEGATIVOS = ["😡", "😠", "😤", "👎"]

INICIO = datetime(2026, 9, 8, 10, 0, tzinfo=timezone.utc)


def _conversa_com(emojis: list[str]) -> Conversa:
    """Uma fala do cliente carregando os emojis, e uma resposta."""
    return Conversa(
        id="sonda",
        canal="whatsapp",
        iniciada_em=INICIO,
        mensagens=[
            Mensagem(autor="cliente", texto="ok " + "".join(emojis), enviada_em=INICIO),
            Mensagem(
                autor="bot",
                texto="entendido",
                enviada_em=INICIO + timedelta(seconds=30),
            ),
        ],
    )


def _correlacao(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs) ** 0.5
    vy = sum((y - my) ** 2 for y in ys) ** 0.5
    return cov / (vx * vy) if vx and vy else 0.0


def _media_do_treino(fusor: Fusor) -> dict[str, float]:
    """Media do scaler, de volta ao espaco do dict de features.

    As features de espera estao em log1p no scaler desde 15/09/2026; o dict
    e em segundos e `vetorizar` comprime. Sem o expm1 a "media" seria
    comprimida duas vezes e deixaria de ter z-score zero.
    """
    escala = fusor._pipeline.named_steps["escala"]
    return {
        nome: math.expm1(float(m)) if nome in FEATURES_EM_LOG else float(m)
        for nome, m in zip(NOMES_FEATURES, escala.mean_)
    }


def main() -> int:
    fusor = Fusor.carregar(CAMINHO_FUSOR)
    eixo = fusor.eixo_global()
    medias = _media_do_treino(fusor)

    # As quatro misturas: 4 negativos, 3-1, 2-2, 1-3, 4 positivos.
    misturas = [
        NEGATIVOS[:4],
        NEGATIVOS[:3] + POSITIVOS[:1],
        NEGATIVOS[:2] + POSITIVOS[:2],
        NEGATIVOS[:1] + POSITIVOS[:3],
        POSITIVOS[:4],
    ]
    amostras = [features_emoji(_conversa_com(m)) for m in misturas]

    print("=" * 78)
    print("1. AS IRMAS SE MOVEM JUNTAS? -- correlacao dentro da familia emoji")
    print("=" * 78)
    print("Cinco conversas reais, de 4 emojis negativos a 4 positivos, com as")
    print("features saindo de `features_emoji` -- nada inventado.")
    print()
    print(f"{'mistura':<12} {'score_medio':>12} {'frac_pos':>10} {'frac_neg':>10}")
    for mistura, f in zip(misturas, amostras):
        rotulo = f"{sum(1 for e in mistura if e in POSITIVOS)}+/{sum(1 for e in mistura if e in NEGATIVOS)}-"
        print(
            f"{rotulo:<12} {f['emoji_score_medio']:>12.3f} "
            f"{f['emoji_frac_positivos']:>10.2f} {f['emoji_frac_negativos']:>10.2f}"
        )
    print()
    score = [f["emoji_score_medio"] for f in amostras]
    pos = [f["emoji_frac_positivos"] for f in amostras]
    neg = [f["emoji_frac_negativos"] for f in amostras]
    print(f"corr(score_medio, frac_positivos) = {_correlacao(score, pos):+.3f}")
    print(f"corr(score_medio, frac_negativos) = {_correlacao(score, neg):+.3f}")
    print(f"corr(frac_positivos, frac_negativos) = {_correlacao(pos, neg):+.3f}")
    print()
    print("ATENCAO A ESTE -1,000: ele e ARTEFATO DA SONDA, nao fato do corpus.")
    print("Esta varredura so usa emoji POLAR, e ai `frac_pos + frac_neg = 1` por")
    print("construcao. Emoji neutro (|score| <= 0,1) nao entra em nenhuma das duas")
    print("e quebra a soma. A medida honesta e sobre o corpus, logo abaixo.")
    print()

    print("=" * 78)
    print("1b. A MESMA CORRELACAO, NO CORPUS DO SIMULADOR")
    print("=" * 78)
    print("300 conversas geradas com semente fixa -- a estrutura de conversa que o")
    print("notebook 02 usa, com a mistura de emoji e o `PROB_EMOJI` de verdade.")
    print()
    lote = gerar_lote(FRASES_POR_ROTULO, quantidade=300, semente=20260908)
    do_corpus = [features_emoji(conversa) for conversa, _ in lote]
    # Conversa sem emoji nenhum devolve as cinco zeradas: incluir isso na
    # correlacao mediria "tem emoji ou nao", que e outra pergunta -- e a
    # `emoji_contagem` ja responde.
    com_emoji = [f for f in do_corpus if f["emoji_contagem"] > 0]
    cs = [f["emoji_score_medio"] for f in com_emoji]
    cp = [f["emoji_frac_positivos"] for f in com_emoji]
    cn = [f["emoji_frac_negativos"] for f in com_emoji]
    print(f"{len(com_emoji)} das {len(do_corpus)} conversas tem ao menos um emoji.")
    print(f"corr(score_medio, frac_positivos) = {_correlacao(cs, cp):+.3f}")
    print(f"corr(score_medio, frac_negativos) = {_correlacao(cs, cn):+.3f}")
    print(f"corr(frac_positivos, frac_negativos) = {_correlacao(cp, cn):+.3f}")
    print()
    print("Correlacao alta em qualquer leitura: as tres medem a MESMA coisa por")
    print("tres caminhos. Nesse regime o coeficiente individual e ajuste, nao")
    print("efeito, e o sinal dele nao e interpretavel sozinho.")
    print()

    print("=" * 78)
    print("2. O EFEITO LIQUIDO DA FAMILIA -- a pergunta que importa")
    print("=" * 78)
    print("Contribuicao SOMADA das cinco features de emoji, com todo o resto na")
    print("media do treino (z-score zero, contribuicao zero).")
    print()
    print(f"{'mistura':<12} {'liquido emoji':>15} {'so score_medio':>16} {'so as 2 suspeitas':>19}")
    liquidos = []
    for mistura, f in zip(misturas, amostras):
        features = dict(medias)
        features.update(f)
        contribuicoes = fusor.contribuicoes(features)
        liquido = sum(contribuicoes[n] for n in FAMILIA_EMOJI)
        so_forte = contribuicoes["emoji_score_medio"]
        so_suspeitas = (
            contribuicoes["emoji_frac_positivos"] + contribuicoes["emoji_frac_negativos"]
        )
        rotulo = f"{sum(1 for e in mistura if e in POSITIVOS)}+/{sum(1 for e in mistura if e in NEGATIVOS)}-"
        liquidos.append(liquido)
        print(f"{rotulo:<12} {liquido:>15.3f} {so_forte:>16.3f} {so_suspeitas:>19.3f}")
    print()
    subiu = liquidos[-1] > liquidos[0]
    print(
        f"De 4 negativos para 4 positivos o liquido vai de {liquidos[0]:+.3f} "
        f"para {liquidos[-1]:+.3f}: {'SOBE' if subiu else 'DESCE'}."
    )
    print("Emoji mais positivo empurra a nota para cima." if subiu else
          "PROBLEMA REAL: emoji mais positivo empurra a nota para BAIXO.")
    print()

    print("=" * 78)
    print("3. O MESMO TESTE NA FAMILIA DE TEXTO")
    print("=" * 78)
    print("`_media` e `_ultima` sao a mesma leitura da mesma cabeca sobre a mesma")
    print("conversa -- numa conversa de poucos turnos elas quase coincidem. Varridas")
    print("juntas, como se movem de verdade:")
    print()
    print(f"{'P(satisfeito)':>14} {'liquido texto':>15} {'so _media':>12} {'so _ultima':>12}")
    liquidos_texto = []
    for prob in (0.05, 0.25, 0.5, 0.75, 0.95):
        features = dict(medias)
        for nome in FAMILIA_TEXTO_SATISFEITO:
            features[nome] = prob
        contribuicoes = fusor.contribuicoes(features)
        liquido = sum(contribuicoes[n] for n in FAMILIA_TEXTO_SATISFEITO)
        liquidos_texto.append(liquido)
        print(
            f"{prob:>14.2f} {liquido:>15.3f} "
            f"{contribuicoes['texto_prob_satisfeito_media']:>12.3f} "
            f"{contribuicoes['texto_prob_satisfeito_ultima']:>12.3f}"
        )
    print()
    subiu_texto = liquidos_texto[-1] > liquidos_texto[0]
    print(
        f"De 0,05 a 0,95 o liquido vai de {liquidos_texto[0]:+.3f} para "
        f"{liquidos_texto[-1]:+.3f}: {'SOBE' if subiu_texto else 'DESCE'}."
    )
    print()

    print("=" * 78)
    print("VEREDITO")
    print("=" * 78)
    if subiu and subiu_texto:
        print("As duas familias respondem na direcao CERTA. Os tres sinais")
        print("'invertidos' sao pesos de correcao de features redundantes, nao")
        print("defeito de aprendizado -- a irma forte de cada par ja carrega o")
        print("efeito, e o coeficiente pequeno de sinal oposto e o resto.")
        print()
        print("O que isso NAO autoriza a dizer: que as features redundantes sejam")
        print("inofensivas. Elas gastam grau de liberdade e tornam o laudo de pesos")
        print("mais dificil de ler -- e o aviso de `conferir_fusor.py` deve")
        print("CONTINUAR, porque a proxima inversao pode nao ter esta explicacao.")
    else:
        print("PROBLEMA REAL: alguma familia responde na direcao errada no LIQUIDO.")
        print("Aqui a colinearidade nao explica -- investigue o corpus.")
    for nome in ("texto_prob_satisfeito_ultima", "emoji_frac_positivos", "emoji_frac_negativos"):
        print(f"   peso individual de {nome}: {eixo[nome]:+.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
