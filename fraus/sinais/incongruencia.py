"""Sinal de incongruencia: o CONFLITO interno do texto, nao a polaridade dele.

Ironia e uma relacao entre o que o texto DIZ e o que ele SIGNIFICA, e a marca
computavel dessa relacao e a incongruencia -- polaridade que se contradiz
dentro da mesma fala, exagero implausivel, aspas que negam a palavra que
cercam. A literatura e consistente nisso: Riloff et al. (EMNLP 2013) definem
sarcasmo como contraste entre sentimento positivo e situacao negativa, e
Joshi et al. (ACL 2015) medem +8% F1 sobre features lexicas e pragmaticas so
com incongruencia explicita. Ver a bibliografia da spec de 03/09/2026.

POR QUE UM MODULO SEPARADO de `ironia.py`: aquele modulo E o classificador
BERTimbau -- carrega peso, roda `torch`, falha alto se o artefato nao existe.
Este nao carrega modelo nenhum: e lexico e regex, reusando `lexico.py` e
`emoji.py`. Juntar os dois faria a heuristica deterministica ficar refem do
artefato treinado, e um dos dois nao poderia rodar sem o outro sem motivo.

POR QUE COMPLEMENTA em vez de substituir: o classificador de ironia foi
treinado no IDPT 2021 (tweet e noticia), e a transferencia para atendimento
nao e verificada -- a propria dashboard ja avisa que ele erra 6 em 10 falas
sinceras. Estas cinco features tem procedencia independente dele: quando as
duas leituras concordam, a evidencia soma; quando discordam, a discordancia e
informacao, e quem pondera as duas e o fusor, com peso aprendido.

TODAS as cinco leem SO a fala do cliente, coerente com os demais sinais.
"""

import re

from fraus.modelos import Conversa
from fraus.sinais.curadoria import CURADORIA_VAZIA, Curadoria
from fraus.sinais.emoji import emojis_com_posicao, score_do_emoji
from fraus.sinais.lexico import anotar_texto, polaridade_do_termo

CHAVES = (
    "incongruencia_polaridade",
    "incongruencia_emoji_texto",
    "incongruencia_marcador_contraste",
    "incongruencia_hiperbole",
    "incongruencia_aspas_ironicas",
)

# Conectivos de contraste do portugues. Lista curta de proposito, pelo mesmo
# motivo que `NEGACOES` em `lexico.py` e curta: marcador duvidoso marca
# contraste que nao existe, e ruido correlacionado com fala normal e pior que
# feature ausente. Fonte: Portuguese Lexicon of Discourse Markers (CLUL).
MARCADORES_CONTRASTE = (
    "mas", "porem", "porém", "contudo", "todavia", "entretanto",
    "so que", "só que", "mesmo assim",
)

# Intensificadores que, junto de polaridade extrema, formam hiperbole
# (Troiano & Strapparava, EMNLP 2018; Burgers et al., 2012). "atendimento
# EXTREMAMENTE otimo, so esperei 3 horas" e o caso de manual.
INTENSIFICADORES = (
    "muito", "super", "extremamente", "totalmente", "completamente",
    "absurdamente", "demais",
)

# Limiar de emoji para "tem polaridade" -- o mesmo de `emoji.py`, e de
# proposito: duas reguas diferentes para a mesma pergunta ("este emoji e
# positivo?") divergiriam em silencio na fronteira.
LIMIAR_EMOJI = 0.1

_TOKEN = re.compile(r"[0-9a-zà-ÿA-ZÀ-Ý\-]+")
# Aspas retas e curvas: o cliente digita as duas, e o teclado do celular
# troca uma pela outra sem avisar.
_ENTRE_ASPAS = re.compile(r'["“”\']([^"“”\']{1,40})["“”\']')


def _polaridades(texto: str, curadoria: Curadoria) -> list[int]:
    """Polaridades dos termos do lexicon achados, ja com negacao aplicada."""
    return [p for _, p, _ in anotar_texto(texto, curadoria) if p != 0]


def _incongruencia_polaridade(texto: str, curadoria: Curadoria) -> float:
    """F1 -- positivo e negativo convivendo na MESMA fala (Riloff 2013).

    A razao e `min / total` e nao a contagem crua: uma fala com 1 positivo e 1
    negativo e mais incongruente que uma com 1 positivo e 9 negativos, que e
    so uma reclamacao com uma ressalva. O maximo (0,5) e o empate perfeito.
    """
    polaridades = _polaridades(texto, curadoria)
    positivos = sum(1 for p in polaridades if p > 0)
    negativos = sum(1 for p in polaridades if p < 0)
    total = positivos + negativos
    if total == 0:
        return 0.0
    return min(positivos, negativos) / total


def _contraste_emoji_texto(texto: str, curadoria: Curadoria) -> float:
    """F2 -- o emoji diz uma coisa e o texto diz o contrario.

    So conta quando as DUAS pontas tem polaridade: emoji neutro ou texto sem
    termo do lexicon nao e contraste, e um alinhamento com um lado ausente.
    """
    polaridades = _polaridades(texto, curadoria)
    if not polaridades:
        return 0.0
    scores = [score_do_emoji(c, curadoria) for c, _ in emojis_com_posicao(texto)]
    com_polaridade = [s for s in scores if abs(s) > LIMIAR_EMOJI]
    if not com_polaridade:
        return 0.0

    media_texto = sum(polaridades) / len(polaridades)
    media_emoji = sum(com_polaridade) / len(com_polaridade)
    # Sinais opostos: o produto e negativo. A magnitude e quanto as duas
    # pontas se afastam, limitada a 1 para nao deixar uma fala extrema
    # dominar a media da conversa.
    if media_texto * media_emoji >= 0:
        return 0.0
    return min(1.0, abs(media_texto - media_emoji) / 2)


def _marcador_contraste(texto: str, curadoria: Curadoria) -> bool:
    """F3 -- conectivo de contraste separando polaridades opostas.

    O conectivo SOZINHO nao basta: "mas" e uma das palavras mais comuns do
    portugues e aparece em fala perfeitamente sincera. O que marca e o
    conectivo com polaridade oposta de cada lado dele.
    """
    minusculo = texto.lower()
    for marcador in MARCADORES_CONTRASTE:
        posicao = minusculo.find(f" {marcador} ")
        if posicao == -1:
            continue
        antes = _polaridades(texto[:posicao], curadoria)
        depois = _polaridades(texto[posicao + len(marcador) + 2:], curadoria)
        if not antes or not depois:
            continue
        if (sum(antes) > 0) != (sum(depois) > 0):
            return True
    return False


def _hiperbole(texto: str, curadoria: Curadoria) -> float:
    """F4 -- intensificador colado em termo de polaridade.

    Fracao dos termos polares da fala que vem intensificados. Elogio
    intensificado e o formato mais comum da ironia de atendimento ("otimo
    demais"), e tambem o da satisfacao genuina -- por isso e feature com peso
    aprendido pelo fusor, nao regra de decisao.
    """
    tokens = _TOKEN.findall(texto.lower())
    if not tokens:
        return 0.0
    polares = 0
    intensificados = 0
    for indice, token in enumerate(tokens):
        if polaridade_do_termo(token, curadoria) == 0:
            continue
        polares += 1
        vizinhos = tokens[max(0, indice - 2):indice]
        if any(v in INTENSIFICADORES for v in vizinhos):
            intensificados += 1
    if polares == 0:
        return 0.0
    return intensificados / polares


def _aspas_ironicas(texto: str, curadoria: Curadoria) -> bool:
    """F5 -- palavra entre aspas com polaridade oposta ao resto da fala.

    As "scare quotes" (Burgers et al., 2012): o cliente marca tipograficamente
    a palavra de que ele discorda. `"otimo" atendimento, tudo pessimo` e o
    caso. Aspas sem conflito de polaridade sao citacao, nao deboche.
    """
    for achado in _ENTRE_ASPAS.finditer(texto):
        dentro = _polaridades(achado.group(1), curadoria)
        if not dentro:
            continue
        fora = _polaridades(
            texto[:achado.start()] + " " + texto[achado.end():], curadoria
        )
        if not fora:
            continue
        if (sum(dentro) > 0) != (sum(fora) > 0):
            return True
    return False


def features_incongruencia(
    conversa: Conversa, curadoria: Curadoria | None = None
) -> dict[str, float]:
    """As cinco features de incongruencia, media sobre as falas do cliente.

    Conversa sem fala do cliente devolve as cinco zeradas -- e ausencia de
    medida, e quem distingue "nao mediu" de "mediu e deu zero" e o
    `score: None` la em cima, nunca esta funcao (invariante 2).
    """
    curadoria = curadoria or CURADORIA_VAZIA
    textos = [m.texto for m in conversa.mensagens_cliente]
    if not textos:
        return {chave: 0.0 for chave in CHAVES}

    total = len(textos)
    return {
        "incongruencia_polaridade": sum(
            _incongruencia_polaridade(t, curadoria) for t in textos
        ) / total,
        "incongruencia_emoji_texto": sum(
            _contraste_emoji_texto(t, curadoria) for t in textos
        ) / total,
        "incongruencia_marcador_contraste": sum(
            1 for t in textos if _marcador_contraste(t, curadoria)
        ) / total,
        "incongruencia_hiperbole": sum(_hiperbole(t, curadoria) for t in textos) / total,
        "incongruencia_aspas_ironicas": sum(
            1 for t in textos if _aspas_ironicas(t, curadoria)
        ) / total,
    }
