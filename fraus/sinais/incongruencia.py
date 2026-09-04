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
from fraus.sinais.lexico import ALCANCE_NEGACAO, NEGACOES, anotar_texto

CHAVES = (
    "incongruencia_polaridade",
    "incongruencia_emoji_texto",
    "incongruencia_marcador_contraste",
    "incongruencia_hiperbole",
    "incongruencia_aspas_ironicas",
    "incongruencia_situacao_negativa",
)

# ---------------------------------------------------------------------------
# F6 -- incongruencia IMPLICITA (Riloff 2013; Joshi 2015)
#
# As cinco features acima cobrem incongruencia EXPLICITA: as duas pontas do
# contraste estao no lexicon. A ironia de atendimento tipica nao e assim --
# tem so UM lado lexical (o elogio), e o outro lado e negativo por
# conhecimento de mundo:
#
#     "que atendimento maravilhoso, so esperei 3 horas"
#
# "esperei 3 horas" nao tem nenhuma palavra polar em lexicon nenhum. Medido:
# as cinco features dao 0,0 nessa frase, e ela pontuava 99,95 / nota 10.
#
# POR QUE LISTA CURADA e nao o bootstrapping do Riloff 2013: o algoritmo dele
# aprende frases de situacao negativa de um corpus grande marcado como
# sarcastico -- que nao existe para atendimento em portugues. Rodar sobre o
# B2W-Reviews01 usaria o MESMO corpus que da o rotulo do fusor, e a feature
# resultante seria um detector de sentimento negativo requentado: exatamente o
# modo de falha que tirou `ironia_prob_*` do vetor em 04/09/2026. Lista curada
# e pequena, auditavel item a item, e a procedencia e honesta -- mesma
# natureza declarada de `palavroes_ptbr.csv` e de `MARCADORES_CONTRASTE`.
# Desenho completo em docs/superpowers/specs/2026-09-04-incongruencia-implicita-design.md.
# ---------------------------------------------------------------------------

# O catalogo de queixa de atendimento, por tema. Nao e lista arbitraria: ao
# contrario de sarcasmo em rede social (dominio aberto, qualquer assunto),
# atendimento tem um numero finito de reclamacoes-tipo, e sao sempre as
# mesmas. Cada item e casado como N-GRAMA DE TOKEN, nao como substring: "fila"
# como substring casaria dentro de "perfilado".
SITUACOES_NEGATIVAS = (
    # espera e demora
    "esperar", "esperei", "esperando", "esperamos", "esperado", "esperou",
    "aguardar", "aguardei", "aguardando", "aguardado",
    "demorou", "demora", "demorando", "fila",
    # repeticao e transferencia -- o cliente refazendo trabalho do atendimento
    "repetir", "repeti", "repetindo", "explicar tudo de novo",
    "explico a mesma coisa", "explicar de novo",
    "transferiram", "transferido", "transferida", "me passaram",
    "de novo", "outra vez", "mais uma vez", "terceira vez", "quarta vez",
    # entrega e promessa nao cumprida
    "nao chegou", "não chegou", "nunca chegou", "cancelaram",
    "nao resolveu", "não resolveu", "nao resolveram", "não resolveram",
    "sem resposta", "sem solucao", "sem solução", "ate agora nada",
    "até agora nada", "perdi o prazo",
    # cobranca
    "cobraram errado", "cobranca indevida", "cobrança indevida",
    "descontaram", "cobrado duas vezes", "cobraram duas vezes",
)

# O lado POSITIVO do contraste quando o SentiLex nao ajuda.
#
# ESTA LISTA E O CONSERTO DE UM FURO REAL DO DESENHO. A proposta original
# exigia um termo positivo de `anotar_texto` como lado do elogio. Medido na
# primeira frase que um usuario digitou no simulador:
#
#     anotar_texto("Nossa, eu realmente gostei de ficar 5h esperando")
#         -> [('gostei', 0, False)]        <- polaridade ZERO
#
# O SentiLex-PT02 e lexico de JULGAMENTO SOCIAL e e neutro em verbo de afeto
# do proprio falante -- limitacao que `lexico.py` ja declara no topo. Ele sabe
# que "maravilhoso" e positivo e nao sabe que "gostei" e. Sem esta lista, F6
# acertaria a frase de manual do projeto e erraria a frase real. Os verbos
# aqui sao os que o SentiLex deixa em zero, nao uma copia dele.
VERBOS_AFETO_FALANTE = (
    "gostei", "gosto", "gostamos", "adorei", "adoro", "adoramos",
    "amei", "amo", "curti", "curto", "aprovei",
)

# Conectivos de contraste do portugues. Lista curta de proposito, pelo mesmo
# motivo que `NEGACOES` em `lexico.py` e curta: marcador duvidoso marca
# contraste que nao existe, e ruido correlacionado com fala normal e pior que
# feature ausente. Fonte: Portuguese Lexicon of Discourse Markers (CLUL).
MARCADORES_CONTRASTE = (
    "mas", "porem", "porém", "contudo", "todavia", "entretanto",
    "so que", "só que", "mesmo assim",
)

# Uma regex por marcador, compilada uma vez. `\b...\b` prende o marcador a
# fronteira de palavra (nao acha "mas" dentro de "mastigar"), e o
# `[\s,;]*` final absorve a pausa que o cliente digita depois do conectivo
# ("otimo, mas, pessimo") sem exigir espaco literal dos dois lados como a
# versao anterior exigia -- ela usava `str.find(f" {marcador} ")` e perdia
# qualquer marcador seguido de virgula. `re.escape` preserva o espaco interno
# de "so que"/"mesmo assim" como caractere literal, nao como classe.
_REGEX_MARCADORES = tuple(
    re.compile(r"\b" + re.escape(marcador) + r"\b[\s,;]*")
    for marcador in MARCADORES_CONTRASTE
)

# Intensificadores PRE-fixados: vem ANTES do termo polar ("muito otimo").
INTENSIFICADORES_ANTES = (
    "muito", "super", "extremamente", "totalmente", "completamente",
    "absurdamente",
)
# Intensificadores POS-fixados: vem DEPOIS. "demais" e o mais comum em fala
# de atendimento ("otimo demais", "ruim demais") e estava na lista errada --
# a janela so olhava para tras, entao o caso de manual do docstring nunca
# disparava. Duas posicoes, duas listas: uma lista so mentiria sobre onde
# procurar. Fonte da hiperbole por intensificador: Troiano & Strapparava
# (EMNLP 2018); Burgers et al. (2012).
INTENSIFICADORES_DEPOIS = ("demais", "mesmo", "pra caramba")

# Limiar de emoji para "tem polaridade" -- o mesmo de `emoji.py`, e de
# proposito: duas reguas diferentes para a mesma pergunta ("este emoji e
# positivo?") divergiriam em silencio na fronteira.
LIMIAR_EMOJI = 0.1

_TOKEN = re.compile(r"[0-9a-zà-ÿA-ZÀ-Ý\-]+")
# Aspas retas e curvas: o cliente digita as duas, e o teclado do celular
# troca uma pela outra sem avisar.
_ENTRE_ASPAS = re.compile(r'["“”\']([^"“”\']{1,40})["“”\']')
# Pontuacao forte encerra o escopo da negacao em F6 -- mesmo criterio de
# `_FRONTEIRA` em `lexico.py`. Nao e importada de la porque la ela e usada
# para PARTIR o texto em segmentos com `finditer`, e aqui com `split`; o
# criterio e o mesmo e a duplicacao esta declarada aqui de proposito.
_FRONTEIRA_FRASE = re.compile(r"[.!?;]")


def _polaridades(texto: str, curadoria: Curadoria) -> list[int]:
    """Polaridades dos termos do lexicon achados, ja com negacao aplicada.

    Usada so por `_marcador_contraste` e `_aspas_ironicas`, que precisam
    analisar SUBSTRINGS (antes/depois do marcador, dentro/fora das aspas) --
    para elas nao ha `anotar_texto` do texto inteiro para reaproveitar.
    """
    return _filtra_polaridades(anotar_texto(texto, curadoria))


def _filtra_polaridades(achados: list[tuple[str, int, bool]]) -> list[int]:
    """Extrai as polaridades nao-nulas de um resultado ja calculado de
    `anotar_texto`, sem rodar o lexicon de novo."""
    return [p for _, p, _ in achados if p != 0]


def _incongruencia_polaridade(achados: list[tuple[str, int, bool]]) -> float:
    """F1 -- positivo e negativo convivendo na MESMA fala (Riloff 2013).

    A razao e `min / total` e nao a contagem crua: uma fala com 1 positivo e 1
    negativo e mais incongruente que uma com 1 positivo e 9 negativos, que e
    so uma reclamacao com uma ressalva. O maximo (0,5) e o empate perfeito.

    Recebe `achados` (ja calculados por `features_incongruencia`) em vez do
    texto cru: correr `anotar_texto` de novo aqui seria a MESMA varredura do
    lexicon que F2 e F4 tambem precisam, sobre o mesmo texto -- feito uma vez
    por mensagem em vez de tres, o que importa porque isso roda por mensagem
    em toda analise (ja houve incidente de CPU bloqueando o event loop do
    uvicorn neste projeto).
    """
    polaridades = _filtra_polaridades(achados)
    positivos = sum(1 for p in polaridades if p > 0)
    negativos = sum(1 for p in polaridades if p < 0)
    total = positivos + negativos
    if total == 0:
        return 0.0
    return min(positivos, negativos) / total


def _contraste_emoji_texto(
    texto: str, achados: list[tuple[str, int, bool]], curadoria: Curadoria
) -> float:
    """F2 -- o emoji diz uma coisa e o texto diz o contrario.

    So conta quando as DUAS pontas tem polaridade: emoji neutro ou texto sem
    termo do lexicon nao e contraste, e um alinhamento com um lado ausente.

    Recebe `achados` ja calculados pelo mesmo motivo de `_incongruencia_polaridade`
    -- ver o docstring dela. `texto` ainda e necessario aqui para achar os
    emojis, que `anotar_texto` nao ve.
    """
    polaridades = _filtra_polaridades(achados)
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

    Usa `_REGEX_MARCADORES` (fronteira de palavra + pausa opcional) em vez de
    `str.find(f" {marcador} ")`: a busca por espaco literal dos dois lados
    perdia qualquer marcador seguido de virgula ("otimo, mas, pessimo"), que
    e a forma mais comum de escrever uma pausa no chat. Marcador logo no
    inicio absoluto da frase (sem nada antes) continua sem marcar -- nao ha
    "antes" para contrastar, entao `not antes` cobre esse caso corretamente,
    nao e bug.
    """
    minusculo = texto.lower()
    for regex in _REGEX_MARCADORES:
        achado = regex.search(minusculo)
        if achado is None:
            continue
        antes = _polaridades(texto[:achado.start()], curadoria)
        depois = _polaridades(texto[achado.end():], curadoria)
        if not antes or not depois:
            continue
        if (sum(antes) > 0) != (sum(depois) > 0):
            return True
    return False


def _posicoes_termos_nao_negados(
    tokens: list[str], achados: list[tuple[str, int, bool]]
) -> list[tuple[int, int]]:
    """Localiza, na lista de tokens, cada achado NAO negado de `anotar_texto`.

    `anotar_texto` devolve o termo como string (ex.: "otimo"), sem a posicao
    dele nos tokens -- precisamos da posicao para saber quais vizinhos checar
    pelo intensificador. Os achados saem na mesma ordem esquerda-para-direita
    da varredura de `anotar_texto`, entao andar um ponteiro crescente pelos
    tokens e casar o termo (que pode ser um n-grama de mais de uma palavra)
    reconstroi a posicao sem duplicar a logica de busca do lexicon.

    So entra na lista o achado NAO negado (`negado is False`): termo negado
    ("nao muito otimo") e leitura mitigada/invertida, nao elogio genuino
    intensificado -- contar "muito" ali como hiperbole marcaria "nao muito
    otimo" identico a "muito otimo", que e exatamente o defeito relatado.
    """
    posicoes: list[tuple[int, int]] = []
    ponteiro = 0
    for termo, polaridade, negado in achados:
        termo_tokens = termo.split(" ")
        tamanho = len(termo_tokens)
        indice = ponteiro
        while indice + tamanho <= len(tokens) and tokens[indice:indice + tamanho] != termo_tokens:
            indice += 1
        if indice + tamanho > len(tokens):
            continue
        ponteiro = indice + tamanho
        if polaridade != 0 and not negado:
            posicoes.append((indice, ponteiro))
    return posicoes


def _hiperbole(texto: str, achados: list[tuple[str, int, bool]]) -> float:
    """F4 -- intensificador colado em termo de polaridade GENUINA (nao negada).

    Fracao dos termos polares nao negados da fala que vem intensificados.
    Elogio intensificado e o formato mais comum da ironia de atendimento
    ("otimo demais"), e tambem o da satisfacao genuina -- por isso e feature
    com peso aprendido pelo fusor, nao regra de decisao.

    Checa intensificador PRE-fixado (antes do termo, "muito otimo") e
    POS-fixado (depois, "otimo demais"): o portugues usa as duas posicoes, e
    a versao anterior so olhava para tras, entao o caso de manual do
    docstring do modulo ("otimo demais") nunca disparava.

    Recebe `achados` (ja calculados por `features_incongruencia`) em vez de
    fazer o proprio lookup: a versao anterior usava `polaridade_do_termo`
    (busca crua, sem negacao) enquanto as outras quatro features usam
    `anotar_texto` (com negacao) -- essa divergencia de fonte fazia "nao
    muito otimo" pontuar hiperbole identico a "muito otimo".
    """
    tokens = _TOKEN.findall(texto.lower())
    if not tokens:
        return 0.0
    posicoes = _posicoes_termos_nao_negados(tokens, achados)
    if not posicoes:
        return 0.0
    intensificados = 0
    for inicio, fim in posicoes:
        antes = tokens[max(0, inicio - 2):inicio]
        depois = tokens[fim:fim + 1]
        if any(v in INTENSIFICADORES_ANTES for v in antes) or any(
            v in INTENSIFICADORES_DEPOIS for v in depois
        ):
            intensificados += 1
    return intensificados / len(posicoes)


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


def _tokens_e_negadas(texto: str) -> tuple[list[str], set[int]]:
    """Tokens do texto inteiro e os indices sob escopo de negacao.

    `anotar_texto` ja resolve negacao, mas devolve termos SEM posicao -- e F6
    casa n-gramas proprios (`SITUACOES_NEGATIVAS`, `VERBOS_AFETO_FALANTE`) que
    nao estao no lexicon, entao nao ha achado dela para reaproveitar. As duas
    CONSTANTES (`NEGACOES`, `ALCANCE_NEGACAO`) sao importadas de `lexico.py`,
    nao redigitadas: se a lista de negacoes mudar la, muda aqui junto. O que e
    local e so a varredura por posicao.

    Sem isto, "nao gostei de ficar esperando" -- a fala mais inequivocamente
    insatisfeita que existe -- casaria "gostei" + "esperando" e sairia como a
    mais ironica da conversa.

    Devolve tokens e negadas JUNTOS porque o escopo se calcula por SEGMENTO (a
    pontuacao forte encerra a negacao, como em `lexico.py`: "nao chegou.
    adorei esperar" tem duas oracoes, e a negacao da primeira nao alcanca a
    segunda) enquanto o casamento de n-grama corre sobre a lista inteira.
    Separar em duas funcoes obrigaria a tokenizar duas vezes e a recalcular os
    offsets de segmento para traduzir indice local em indice global.

    A pontuacao NAO sobrevive a `_TOKEN` (ela so aceita letra, digito e
    hifen), entao a fronteira precisa ser aplicada ao TEXTO, antes de
    tokenizar -- procurar `.!?;` na lista de tokens nunca acharia nada.
    """
    tokens: list[str] = []
    negadas: set[int] = set()
    for segmento in _FRONTEIRA_FRASE.split(texto.lower()):
        base = len(tokens)
        do_segmento = _TOKEN.findall(segmento)
        tokens.extend(do_segmento)
        negacao_ate = -1
        for local, token in enumerate(do_segmento):
            if token in NEGACOES:
                negacao_ate = local + ALCANCE_NEGACAO
                continue
            if local <= negacao_ate:
                negadas.add(base + local)
    return tokens, negadas


def _casa_ngrama(
    tokens: list[str], negadas: set[int], candidatos: tuple[str, ...]
) -> bool:
    """Algum candidato aparece como n-grama de token e NAO esta negado.

    N-grama de token, nao substring: "fila" como substring casaria dentro de
    "perfilado", e "de novo" precisa das duas palavras adjacentes.

    Um n-grama conta como negado se QUALQUER token dele estiver sob escopo --
    a negacao alcanca o comeco da expressao, e "nao explico a mesma coisa"
    deve morrer inteiro, nao so no primeiro token.
    """
    for candidato in candidatos:
        partes = candidato.split(" ")
        tamanho = len(partes)
        for inicio in range(len(tokens) - tamanho + 1):
            if tokens[inicio:inicio + tamanho] != partes:
                continue
            if any(i in negadas for i in range(inicio, inicio + tamanho)):
                continue
            return True
    return False


def _situacao_negativa(texto: str, achados: list[tuple[str, int, bool]]) -> float:
    """F6 -- elogio convivendo com situacao negativa de atendimento.

    Exige os DOIS lados na mesma fala. So a situacao negativa e reclamacao
    direta, que e a fala mais comum de um cliente insatisfeito: se disparasse
    ali, a feature seria um detector de insatisfacao com nome de detector de
    ironia -- o mesmo defeito que tirou `ironia_prob_*` do vetor. So o elogio
    e satisfacao genuina.

    O lado positivo tem DUAS fontes, e a segunda nao e redundante: termo
    positivo nao negado do SentiLex ("maravilhoso"), OU verbo de afeto do
    falante ("gostei"), que o SentiLex deixa em polaridade zero por ser lexico
    de julgamento social. Ver o comentario de `VERBOS_AFETO_FALANTE`.

    Binaria de proposito (0,0 ou 1,0). O grau de ironia nao esta na CONTAGEM de
    situacoes negativas -- "esperei e esperei" nao e mais ironico que
    "esperei"; o que grada e a media por conversa, feita por
    `features_incongruencia`.

    LIMITACAO ACEITA: elogio genuino sobre a RESOLUCAO de um problema real
    ("adorei, resolveram rapido mesmo eu tendo esperado antes") dispara igual.
    Nao ha regra que separe isso de ironia sem conhecimento de mundo. Por isso
    F6 e feature com peso APRENDIDO pelo fusor, ponderada contra as outras 38,
    e nao regra de decisao -- mesma postura que `_hiperbole` ja assume.
    """
    tokens, negadas = _tokens_e_negadas(texto)
    if not tokens:
        return 0.0

    if not _casa_ngrama(tokens, negadas, SITUACOES_NEGATIVAS):
        return 0.0

    tem_elogio = any(
        polaridade > 0 and not negado for _, polaridade, negado in achados
    ) or _casa_ngrama(tokens, negadas, VERBOS_AFETO_FALANTE)
    return 1.0 if tem_elogio else 0.0


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
    somas = {chave: 0.0 for chave in CHAVES}
    for texto in textos:
        # `anotar_texto` roda o lexicon inteiro sobre `texto` UMA vez aqui e o
        # resultado (`achados`) e passado para F1, F2 e F4, que senao
        # chamariam `anotar_texto` cada uma por conta propria sobre o MESMO
        # texto -- essa varredura roda por mensagem em toda analise, e este
        # projeto ja teve incidente de CPU bloqueando o event loop do
        # uvicorn. F3 e F5 continuam calculando por conta propria porque
        # analisam SUBSTRINGS (antes/depois do marcador, dentro/fora das
        # aspas) que nao existem neste resultado do texto inteiro -- nao
        # force esse cache para elas.
        achados = anotar_texto(texto, curadoria)
        somas["incongruencia_polaridade"] += _incongruencia_polaridade(achados)
        somas["incongruencia_emoji_texto"] += _contraste_emoji_texto(
            texto, achados, curadoria
        )
        somas["incongruencia_marcador_contraste"] += (
            1.0 if _marcador_contraste(texto, curadoria) else 0.0
        )
        somas["incongruencia_hiperbole"] += _hiperbole(texto, achados)
        somas["incongruencia_aspas_ironicas"] += (
            1.0 if _aspas_ironicas(texto, curadoria) else 0.0
        )
        somas["incongruencia_situacao_negativa"] += _situacao_negativa(texto, achados)
    return {chave: valor / total for chave, valor in somas.items()}
