"""Ate onde o relogio pode mandar na nota, e a partir de quando ele manda sozinho.

O QUE ISTO MEDE, E POR QUE PRECISOU EXISTIR. Em 08/09/2026, uma conversa com
3 horas de espera cuja UNICA fala do cliente o BERTimbau le como 86% satisfeita
saiu com score 4,4e-24 -- nota 0, detrator. A atribuicao mostrou
`latencia_primeira_resposta_s` em -85,4 contra +4,6 de
`texto_prob_satisfeito_media`: o tempo pesando 20x o texto.

E A INVARIANTE 10 EM RUNTIME, e por isso as guardas existentes nao pegam. As
features de latencia sao ILIMITADAS e o corpus de treino nunca passou de
minutos, entao o `StandardScaler` recebe um valor a dezenas de desvios da media
e a contribuicao (coeficiente x z-score) explode -- mesmo com o coeficiente POR
UNIDADE continuando pequeno, no "rodape" que `docs/treinamento.md` descreve. O
teste `test_nenhuma_feature_e_previsor_unilateral` olha a distribuicao NO
CORPUS; latencia de tres horas nao esta la para ser olhada.

O laudo responde tres perguntas, nesta ordem:

1. **Onde acaba o corpus.** Media e desvio que o scaler aprendeu para cada
   feature de tempo -- e a distribuicao de treino como o modelo a viu, sem
   depender de reabrir o simulador.
2. **Onde o relogio empata com o texto.** Varrendo a latencia com o texto
   saturado, o ponto em que |contribuicao do tempo| passa |contribuicao do
   texto|. Antes desse ponto o tempo modula; depois, ele decide.
3. **Quantos desvios isso representa.** O empate em unidade de sigma do treino
   -- o numero que diz se o ponto de virada esta dentro ou fora do que o modelo
   viu.

NAO DECIDE NADA. As tres saidas (clipar num teto, passar a escala log, ou
aceitar e declarar como limitacao) sao decisao do dono do projeto, e as duas
primeiras exigem retreino. Segue o modelo de `scripts/conferir_fusor.py` e de
`scripts/medir_faixas.py`: instrumento, nao botao -- nao escreve nada, nao toca
no banco, e nao ha caminho da API ate aqui.

Nao carrega BERTimbau nenhum: o lado do texto entra como probabilidade
literal, entao o laudo roda em segundos e sem os modelos em `modelos/` (so o
`fusor.joblib`).

Como rodar:
    uv run python scripts/medir_dominio_do_tempo.py
    uv run python scripts/medir_dominio_do_tempo.py --prob-satisfeito 0.99
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fraus.api.caminhos import CAMINHO_FUSOR  # noqa: E402
from fraus.fusor import FEATURES_EM_LOG, NOMES_FEATURES, Fusor  # noqa: E402

# As quatro features que crescem com a espera. `qtd_turnos_cliente`,
# `escalou` e `abandonou` sao da mesma familia e NAO entram: elas nao crescem
# com o relogio (sao contagem e binarias), entao nao participam do modo de
# falha que este laudo mede.
FEATURES_DE_TEMPO = (
    "latencia_mediana_s",
    "latencia_p90_s",
    "latencia_primeira_resposta_s",
    "duracao_total_s",
)

FEATURE_DO_TEXTO = "texto_prob_satisfeito_media"

# A frase canonica do projeto le 0,858 de satisfeito na cabeca de texto --
# medido, nao arbitrado. E o caso que motivou este laudo.
PROB_CANONICA = 0.858

# A varredura vai de "resposta imediata" ate as tres horas da frase canonica.
LATENCIAS_S = (5, 10, 30, 60, 120, 180, 300, 600, 900, 1800, 3600, 7200, 10800)


def _media_e_desvio(fusor: Fusor) -> dict[str, tuple[float, float]]:
    """O que o `StandardScaler` aprendeu, por feature.

    E a distribuicao de treino como o MODELO a viu. Ler daqui em vez de
    reabrir o simulador e deliberado: o simulador de hoje pode ja nao ser o
    que gerou este artefato, e a pergunta do laudo e sobre o artefato.
    """
    escala = fusor._pipeline.named_steps["escala"]
    return {
        nome: (float(m), float(s))
        for nome, m, s in zip(NOMES_FEATURES, escala.mean_, escala.scale_)
    }


def _conversa_sintetica(latencia_s: float, prob_satisfeito: float,
                        estatisticas: dict[str, tuple[float, float]]) -> dict[str, float]:
    """Vetor de uma conversa com UMA fala do cliente e UMA resposta.

    Toda feature que nao esta sendo variada entra na MEDIA DO TREINO, e isso e
    o coracao do metodo: valor na media tem z-score zero, logo contribuicao
    exatamente zero. O que sobra no laudo e so o tempo contra o texto, sem
    ruido de nenhuma outra familia -- que e a comparacao que a pergunta pede.
    """
    # A media do scaler das features de espera esta em log1p (15/09/2026); o
    # dict de features e sempre em SEGUNDOS, e `vetorizar` comprime. Voltar
    # com expm1 mantem o z-score zero que o metodo exige.
    features = {
        nome: math.expm1(media) if nome in FEATURES_EM_LOG else media
        for nome, (media, _) in estatisticas.items()
    }
    features[FEATURE_DO_TEXTO] = prob_satisfeito
    for nome in FEATURES_DE_TEMPO:
        features[nome] = float(latencia_s)
    # A conversa dura a espera mais os poucos segundos das duas falas.
    features["duracao_total_s"] = float(latencia_s) + 30.0
    return features


def _somar(contribuicoes: dict[str, float], nomes) -> float:
    return sum(contribuicoes[nome] for nome in nomes)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--prob-satisfeito",
        type=float,
        default=PROB_CANONICA,
        help=f"probabilidade de satisfeito do texto (padrao {PROB_CANONICA}, a da frase canonica)",
    )
    args = ap.parse_args()

    fusor = Fusor.carregar(CAMINHO_FUSOR)
    estatisticas = _media_e_desvio(fusor)

    print("=" * 78)
    print("1. ONDE ACABA O CORPUS -- o que o scaler aprendeu das features de tempo")
    print("=" * 78)
    # Em log1p desde 15/09/2026: a media vira media GEOMETRICA em segundos, e
    # "+3 desvios" e multiplicativo -- expm1 de (media + 3 desvios) no log.
    print(f"{'feature':<32} {'centro (s)':>12} {'desvio (log)':>12} {'centro+3d (s)':>14}")
    for nome in FEATURES_DE_TEMPO:
        media, desvio = estatisticas[nome]
        print(f"{nome:<32} {math.expm1(media):>12.1f} {desvio:>12.2f} "
              f"{math.expm1(media + 3 * desvio):>14.1f}")
    print()
    print("`centro+3d` e uma referencia grosseira de onde o corpus rareia. Acima")
    print("disso e extrapolacao; em log1p o z-score ainda cresce sem teto, mas")
    print("devagar: dobrar a espera soma ~0,7 no log, nao multiplica o z por dois.")
    print()

    print("=" * 78)
    print(f"2. TEMPO CONTRA TEXTO -- texto fixo em P(satisfeito) = {args.prob_satisfeito}")
    print("=" * 78)
    print(f"{'latencia':>10} {'contrib tempo':>15} {'contrib texto':>15} {'razao':>10} {'quem manda':>12}")

    virada = None
    linhas = []
    for latencia in LATENCIAS_S:
        features = _conversa_sintetica(latencia, args.prob_satisfeito, estatisticas)
        contribuicoes = fusor.contribuicoes(features)
        tempo = _somar(contribuicoes, FEATURES_DE_TEMPO)
        texto = contribuicoes[FEATURE_DO_TEXTO]
        razao = abs(tempo) / abs(texto) if texto else float("inf")
        manda = "tempo" if abs(tempo) > abs(texto) else "texto"
        if virada is None and manda == "tempo":
            virada = latencia
        linhas.append((latencia, tempo, texto, razao, manda))
        print(f"{latencia:>9}s {tempo:>15.2f} {texto:>15.2f} {razao:>9.1f}x {manda:>12}")
    print()

    print("=" * 78)
    print("3. ONDE ISSO CAI NA DISTRIBUICAO DE TREINO")
    print("=" * 78)
    if virada is None:
        print("O texto manda em toda a faixa varrida. Nada a declarar.")
    else:
        # A contribuicao do tempo deixou de ser AFIM na latencia em 15/09/2026
        # (log1p), entao o cruzamento sai por BISSECAO entre o ultimo ponto da
        # grade em que o texto mandava e o primeiro em que o tempo manda. Ela e
        # monotona: log1p cresce sempre, e os pesos de espera sao negativos.
        def tempo_em(latencia: float) -> float:
            f = _conversa_sintetica(latencia, args.prob_satisfeito, estatisticas)
            return _somar(fusor.contribuicoes(f), FEATURES_DE_TEMPO)

        texto = linhas[0][2]
        baixo = max(l for l, *_ in linhas if l < virada)
        alto = float(virada)
        for _ in range(60):
            meio = (baixo + alto) / 2
            if abs(tempo_em(meio)) > abs(texto):
                alto = meio
            else:
                baixo = meio
        exata = alto

        media, desvio = estatisticas["latencia_mediana_s"]
        sigmas = (math.log1p(exata) - media) / desvio if desvio else float("inf")
        print(f"O relogio empata com o texto em {exata:.0f}s ({exata / 60:.1f} min)")
        print(f"e manda a partir dali. Na grade acima isso cai entre "
              f"{[l for l, *_ in linhas if l < exata][-1]}s e {virada}s -- confere.")
        print()
        print(f"{exata:.0f}s e {sigmas:.1f} desvios acima da media de `latencia_mediana_s`")
        print(f"no treino (centro {math.expm1(media):.1f}s, desvio {desvio:.2f} em log1p). Ou seja: o ponto em que o")
        print("relogio toma a nota esta " + ("FORA do" if sigmas > 3 else "DENTRO do")
              + " que o corpus mostrou ao modelo (corte de 3 desvios).")
        print()
        print(f"A 3 horas o tempo da {abs(tempo_em(10800.0)):.1f} de contribuicao, "
              f"contra {abs(texto):.1f} do texto inteiro.")
        print()
        pior = linhas[-1]
        print(f"No pior caso varrido ({pior[0]}s), o tempo pesa {pior[3]:.0f}x o texto.")
    print()
    print("Decidido em 15/09/2026: a espera entra em log1p, sem teto (ver")
    print("docs/treinamento.md). O teto p99 foi recusado: fazia 3 h pesarem o")
    print("mesmo que 10 min. O laudo continua valendo para qualquer retreino.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
