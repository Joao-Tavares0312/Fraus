"""Indicadores agregados.

NPS aqui e INFERIDO do texto, nao declarado pelo cliente. A dashboard rotula
como estimativa -- apresentar como NPS declarado seria falso.

Faixas canonicas: 0-6 detrator, 7-8 neutro, 9-10 promotor.
Categoria SEMPRE derivada no servidor.
"""

from collections import Counter
from math import sqrt
from statistics import median
from typing import Literal

from fraus.modelos import Conversa
from fraus.sinais.tempo import latencias_da_conversa

Categoria = Literal["detrator", "neutro", "promotor"]
NOTA_MINIMA_SATISFEITO = 7

# Fonte UNICA das faixas de NPS: qualquer lugar que precise das faixas (a API,
# a dashboard) le daqui -- nunca digita os numeros 0, 6, 7, 8, 9, 10 de novo.
FAIXAS_NPS: dict[Categoria, tuple[int, int]] = {
    "detrator": (0, 6),
    "neutro": (7, 8),
    "promotor": (9, 10),
}

NOTA_MINIMA = 0
NOTA_MAXIMA = 10

# Abaixo deste n o ponto estimado do NPS nao e mostrado -- so o intervalo e a
# contagem. O estudo de simulacao de 2026 (MDPI Stats 9(2):45) comparou Wald,
# bootstrap-t e Wald ajustado e concluiu que os dois primeiros devem ser
# EVITADOS em amostra pequena, com todos convergindo para a cobertura nominal
# conforme n cresce. 30 e o corte convencional de "amostra grande" para a
# aproximacao normal; e regra de EXIBICAO, nao de calculo, e por isso mora
# aqui e nao numa constante do front.
N_MINIMO_NPS = 30

# z de 1,96 -> 95% de confianca sob a aproximacao normal.
Z_95 = 1.96


def nota_0_10(score_0_100: float) -> int:
    return int(round(max(0.0, min(100.0, score_0_100)) / 10))


def categoria_nps(
    score_0_100: float, faixas: dict[Categoria, tuple[int, int]] | None = None
) -> Categoria:
    """Categoria da nota segundo `faixas` -- por PARAMETRO, nunca global mutavel.

    Quando a configuracao muda as faixas, quem le passa as faixas vigentes; o
    default e o padrao de fabrica. Assim a faixa continua morando num lugar so
    e nao existe estado global que mude sob os pes de quem ja calculou.
    """
    if faixas is None:
        faixas = FAIXAS_NPS
    nota = nota_0_10(score_0_100)
    for categoria, (minima, maxima) in faixas.items():
        if minima <= nota <= maxima:
            return categoria
    raise ValueError(f"nota {nota} fora de qualquer faixa de NPS")


def validar_faixas_nps(faixas: dict[str, tuple[int, int]]) -> None:
    """Recusa faixa que nao cubra 0..10 de forma contigua, nomeando o problema.

    Faixa de NPS com buraco ou sobreposicao nao e preferencia de gosto: seria
    nota sem categoria (ou com duas), e o erro apareceria muito depois, na
    leitura de um atendimento qualquer. Levanta ValueError -- a borda HTTP
    traduz para 400 com a mesma frase.
    """
    faltando = [c for c in ("detrator", "neutro", "promotor") if c not in faixas]
    if faltando:
        raise ValueError(f"faixa de NPS ausente: {', '.join(faltando)}")
    sobrando = [c for c in faixas if c not in ("detrator", "neutro", "promotor")]
    if sobrando:
        raise ValueError(f"categoria de NPS desconhecida: {', '.join(sorted(sobrando))}")

    for categoria, (minima, maxima) in faixas.items():
        if minima > maxima:
            raise ValueError(
                f"faixa vazia em {categoria}: minima {minima} maior que maxima {maxima}"
            )

    ordenadas = sorted(faixas.items(), key=lambda item: item[1][0])
    primeira, (inicio, _) = ordenadas[0][0], ordenadas[0][1]
    if inicio != NOTA_MINIMA:
        raise ValueError(
            f"as faixas comecam em {inicio} na categoria {primeira}, "
            f"mas precisam comecar em {NOTA_MINIMA}"
        )
    ultima, (_, fim) = ordenadas[-1][0], ordenadas[-1][1]
    if fim != NOTA_MAXIMA:
        raise ValueError(
            f"as faixas terminam em {fim} na categoria {ultima}, "
            f"mas precisam terminar em {NOTA_MAXIMA}"
        )

    for (nome_anterior, (_, fim_anterior)), (nome, (inicio_atual, _)) in zip(
        ordenadas, ordenadas[1:]
    ):
        if inicio_atual <= fim_anterior:
            raise ValueError(
                f"a faixa {nome} sobrepoe {nome_anterior}: "
                f"{nome_anterior} vai ate {fim_anterior} e {nome} comeca em {inicio_atual}"
            )
        if inicio_atual > fim_anterior + 1:
            raise ValueError(
                f"buraco entre {nome_anterior} e {nome}: "
                f"nenhuma faixa cobre a nota {fim_anterior + 1}"
            )


def calcular_nps(
    scores: list[float], faixas: dict[Categoria, tuple[int, int]] | None = None
) -> float | None:
    """Percentual de promotores menos percentual de detratores, em [-100, 100].

    Sem score algum devolve None -- ausencia de dado nao e insatisfacao, e
    "NPS +0" seria apresentar como medido um numero que ninguem mediu.
    """
    if not scores:
        return None
    categorias = [categoria_nps(s, faixas) for s in scores]
    total = len(categorias)
    promotores = categorias.count("promotor") / total
    detratores = categorias.count("detrator") / total
    return round(100.0 * (promotores - detratores), 2)


def nps_com_intervalo(
    scores: list[float], faixas: dict[Categoria, tuple[int, int]] | None = None
) -> dict | None:
    """NPS inferido com intervalo de confianca de 95% (AW(3,T)).

    Hoje "NPS -12" aparece igual com 8 conversas e com 8.000, e a primeira
    pergunta de quem avalia e "quantas conversas sustentam esse numero?".
    Mostrar ponto estimado sem incerteza e inconsistente com um sistema que
    ja recusa transformar ausencia em zero.

    O ponto observado continua sendo percentual de promotores menos
    percentual de detratores, sem suavizacao, igual a `calcular_nps`.
    Para o INTERVALO usamos Wald ajustado triangular AW(3,T): acrescentar
    0,75 as contagens de cada extremo e 1,5 aos neutros. Sao pseudocontagens
    estatisticas, nunca atendimentos reais nem mudanca no score do fusor.

        n_ajustado = n + 3
        p_prom     = (promotores + 0,75) / n_ajustado
        p_det      = (detratores + 0,75) / n_ajustado
        media      = p_prom - p_det
        variancia  = (p_prom + p_det) - media**2
        erro       = sqrt(variancia / (n_ajustado - 1))
        ic         = media +- 1,96 * erro        (tudo x100 na escala do NPS)

    Referencia e implementacao dos autores (variancia com n_ajustado - 1):
    https://doi.org/10.3390/stats9020045
    https://github.com/philturk/Net_Promoter_Score_Confidence_Intervals
    O ajuste evita largura zero em categoria unanime. Esconder o ponto em
    amostra pequena e uma regra de exibicao SEPARADA do metodo estatistico:
    abaixo de `N_MINIMO_NPS` ele nao e devolvido. O `n` permanece observado.

    None quando nao ha score nenhum -- nao existe intervalo de coisa nenhuma.

    HONESTIDADE OBRIGATORIA, e ela precisa aparecer na tela junto do numero:
    este intervalo captura so a incerteza AMOSTRAL. Ele NAO captura a
    incerteza do MODELO, que exigiria calibracao. Um IC apresentado como se
    cobrisse o erro do modelo e pior que nao ter IC nenhum.
    """
    if not scores:
        return None

    categorias = Counter(categoria_nps(s, faixas) for s in scores)
    n = len(scores)
    n_ajustado = n + 3
    p_prom = (categorias["promotor"] + 0.75) / n_ajustado
    p_det = (categorias["detrator"] + 0.75) / n_ajustado

    media = p_prom - p_det
    variancia = (p_prom + p_det) - media**2
    erro = sqrt(variancia / (n_ajustado - 1))
    margem = Z_95 * erro

    # Recortado na escala: o NPS vive em [-100, 100] por definicao, e ponta
    # fora dela seria um numero impossivel impresso com cara de medida.
    inferior = max(-100.0, 100.0 * (media - margem))
    superior = min(100.0, 100.0 * (media + margem))

    return {
        "nps": calcular_nps(scores, faixas) if n >= N_MINIMO_NPS else None,
        "ic_inferior": round(inferior, 2),
        "ic_superior": round(superior, 2),
        "n": n,
    }


def calcular_csat(scores: list[float]) -> float | None:
    """Percentual de atendimentos com nota >= 7. Sem score algum devolve None."""
    if not scores:
        return None
    satisfeitos = sum(1 for s in scores if nota_0_10(s) >= NOTA_MINIMA_SATISFEITO)
    return round(100.0 * satisfeitos / len(scores), 2)


def mediana(valores: list[float]) -> float | None:
    """Mediana, ou None na lista vazia -- nunca 0.0.

    Zero seria "respondeu instantaneamente", que e o oposto de "nao da para
    saber". A serie temporal precisa poder dizer que nao mediu.
    """
    if not valores:
        return None
    return median(valores)


def serie_diaria(
    registros: list[tuple[Conversa, float | None]],
    faixas: dict[Categoria, tuple[int, int]] | None = None,
) -> list[dict]:
    """NPS inferido e latencia mediana por dia, ordenados do mais antigo.

    O dia sai de `iniciada_em` da conversa. A latencia do dia e a mediana das
    MEDIANAS de cada atendimento, nao a mediana de todas as esperas juntas: um
    unico atendimento com trinta idas e vindas dominaria o dia inteiro se as
    esperas fossem jogadas num balde so.

    `nps` e `latencia_mediana_s` sao None no dia sem dado, e os dois motivos
    sao diferentes -- por isso `atendimentos` e `com_score` vem separados.
    Um dia pode ter atendimento e nenhum score (conversa sem fala do cliente),
    e apresentar isso como NPS 0 seria inventar medicao.
    """
    por_dia: dict[str, dict] = {}

    for conversa, score in registros:
        dia = conversa.iniciada_em.date().isoformat()
        balde = por_dia.setdefault(
            dia, {"scores": [], "latencias": [], "atendimentos": 0}
        )
        balde["atendimentos"] += 1
        if score is not None:
            balde["scores"].append(score)
        latencia = mediana(latencias_da_conversa(conversa))
        if latencia is not None:
            balde["latencias"].append(latencia)

    return [
        {
            "dia": dia,
            "nps": calcular_nps(balde["scores"], faixas),
            "latencia_mediana_s": mediana(balde["latencias"]),
            "atendimentos": balde["atendimentos"],
            "com_score": len(balde["scores"]),
        }
        for dia, balde in sorted(por_dia.items())
    ]


def containment_rate(conversas: list[Conversa]) -> float | None:
    """Percentual de conversas resolvidas sem intervencao humana.

    None no conjunto VAZIO -- nunca 0.0, que se leria como "nenhum atendimento
    foi contido", o pior numero da escala, onde nao houve atendimento nenhum.

    A distincao que importa e que esta funcao NAO depende de score: conversa
    sem fala do cliente nao tem NPS nem CSAT e mesmo assim conta como contida
    (ha teste exigindo 100% nesse caso). O que a ausencia de score nao mede,
    ela continua medindo. So o conjunto vazio nao tem resposta.

    Ate 10/09/2026 devolvia 0.0, e o front nao acreditava: `page.tsx` escrevia
    `total_conversas ? containment_rate : null`. A guarda no cliente era a
    prova de que alguem ja tinha sentido o problema -- e ela so protegia a
    dashboard. Export, webhook e qualquer terceiro lendo /indicadores recebiam
    o zero. Uma ponta so decide agora.
    """
    if not conversas:
        return None
    contidas = sum(1 for c in conversas if not c.escalou_para_humano)
    return round(100.0 * contidas / len(conversas), 2)


def contidos_com_score(registros: list[tuple[Conversa, float | None]]) -> int:
    """Quantos atendimentos NAO escalaram e tem score -- o denominador honesto.

    A tela precisa dele para dizer "3 de 12" em vez de so um percentual: sem o
    denominador, 33% sobre tres atendimentos parece a mesma coisa que 33%
    sobre trezentos.
    """
    return sum(
        1 for conversa, score in registros
        if not conversa.escalou_para_humano and score is not None
    )


def falso_containment(
    registros: list[tuple[Conversa, float | None]],
    faixas: dict[Categoria, tuple[int, int]] | None = None,
) -> float | None:
    """Percentual de atendimentos contidos que sairam DETRATORES.

    Conteve e o cliente saiu insatisfeito e sucesso falso: a metrica de
    contencao sobe enquanto a experiencia piora. So o atendimento COM score
    entra na conta -- conversa sem fala do cliente nao e nem sucesso nem
    fracasso, e o denominador precisa dizer sobre quantos se esta falando.

    O limiar de insatisfacao e a categoria `detrator` das faixas VIGENTES,
    recebidas por parametro (invariante 4) -- nunca um 6 digitado aqui.

    None quando nenhum atendimento contido tem score -- nunca 0.0, que se
    leria como "nenhum contido saiu insatisfeito", afirmacao que ninguem
    mediu.
    """
    contidos = [
        score for conversa, score in registros
        if not conversa.escalou_para_humano and score is not None
    ]
    if not contidos:
        return None
    detratores = sum(1 for score in contidos if categoria_nps(score, faixas) == "detrator")
    return round(100.0 * detratores / len(contidos), 2)


def tempo_mediano_resposta(registros: list[tuple[Conversa, float | None]]) -> float | None:
    """Mediana de TODAS as esperas cliente -> resposta do conjunto.

    `None` quando nao ha nenhum par -- nunca zero: zero numa medida de tempo
    de resposta se le como "respondeu na hora", e conjunto sem par nao mediu
    espera nenhuma.
    """
    esperas = [
        espera
        for conversa, _ in registros
        for espera in latencias_da_conversa(conversa)
    ]
    return mediana(esperas)


def lexico_por_classe(
    registros: list[tuple[Conversa, float | None]],
    faixas: dict[Categoria, tuple[int, int]] | None = None,
    limite: int = 6,
) -> list[dict]:
    """Palavras e emojis caracteristicos de cada categoria do conjunto.

    Ordenado por DISTINCAO, nao por frequencia: `distincao` e a diferenca
    entre a fracao do termo nesta classe e a fracao dele nas outras, em
    [-1, 1]. O termo que aparece em toda parte nao explica classe nenhuma.

    Mesma regra da derivacao que a dashboard fazia no cliente (e mantem como
    plano B): so a fala do CLIENTE conta -- o texto do bot e roteiro --, e
    conversa sem score fica fora, porque sem categoria nao ha classe onde
    contar. Emoji e recortado por cluster de grafema, pela mesma extracao do
    sinal de emoji, para a contagem nao divergir do motor.
    """
    from fraus.sinais.emoji import emojis_com_posicao
    from fraus.sinais.palavras import contar_palavras

    if faixas is None:
        faixas = FAIXAS_NPS

    categorias = tuple(faixas)
    palavras_por = {categoria: Counter() for categoria in categorias}
    emojis_por = {categoria: Counter() for categoria in categorias}
    atendimentos = {categoria: 0 for categoria in categorias}

    for conversa, score in registros:
        if score is None:
            continue
        categoria = categoria_nps(score, faixas)
        atendimentos[categoria] += 1
        textos = [m.texto for m in conversa.mensagens_cliente]
        palavras_por[categoria].update(contar_palavras(textos))
        for texto in textos:
            for emoji, _posicao in emojis_com_posicao(texto):
                emojis_por[categoria][emoji] += 1

    return [
        {
            "categoria": categoria,
            "atendimentos": atendimentos[categoria],
            "palavras": _ranquear_por_distincao(palavras_por, categoria, limite),
            "emojis": _ranquear_por_distincao(emojis_por, categoria, limite),
        }
        for categoria in categorias
    ]


def _ranquear_por_distincao(
    por_classe: dict[Categoria, Counter], categoria: Categoria, limite: int
) -> list[dict]:
    da_classe = por_classe[categoria]
    total = sum(da_classe.values())
    if total == 0:
        return []

    outras: Counter = Counter()
    for outra, tabela in por_classe.items():
        if outra != categoria:
            outras.update(tabela)
    total_outras = sum(outras.values())

    itens = [
        {
            "termo": termo,
            "ocorrencias": ocorrencias,
            "distincao": ocorrencias / total
            - (outras.get(termo, 0) / total_outras if total_outras else 0.0),
        }
        for termo, ocorrencias in da_classe.items()
    ]
    itens.sort(key=lambda item: (-item["distincao"], -item["ocorrencias"]))
    return itens[:limite]
