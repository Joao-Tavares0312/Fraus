"""Sinal de estilo: a FORMA da escrita, nao o conteudo dela.

Caixa alta, pontuacao repetida, alongamento de caractere, palavrao e censura
carregam intensidade que nenhum dos outros sinais captura. E deterministico de
proposito: o BERTimbau nao aprende enfase porque o B2W-Reviews01 -- resenha
moderada de e-commerce -- praticamente nao contem gritaria nem xingamento.
Modelo nao aprende fenomeno que o corpus nao tem, e mais epocas sobre o mesmo
texto so reproduzem o mesmo artefato. Ver a spec de 21/08/2026.

Le apenas as falas do cliente, coerente com os demais sinais: enfase do bot nao
e enfase do cliente.
"""

import csv
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from fraus.modelos import Conversa
from fraus.seguranca.pii import TOKENS_MARCADORES

CAMINHO_PALAVROES = Path(__file__).parent.parent / "dados" / "palavroes_ptbr.csv"

INTENSIDADE_POR_NOME = {"leve": 0.33, "medio": 0.66, "pesado": 1.0}


@lru_cache(maxsize=1)
def carregar_palavroes() -> dict[str, tuple[float, bool]]:
    """Termo normalizado -> (intensidade, dirigido a pessoa).

    A gradacao existe porque "que droga" e "vai tomar no cu" nao sao o mesmo
    evento, e o alvo existe porque xingar o PRODUTO e reclamacao enquanto
    xingar o ATENDENTE e ruptura da conversa.
    """
    tabela: dict[str, tuple[float, bool]] = {}
    with CAMINHO_PALAVROES.open(encoding="utf-8", newline="") as arquivo:
        for linha in csv.DictReader(arquivo):
            termo = linha["termo"].strip().lower()
            if not termo:
                continue
            tabela[termo] = (
                INTENSIDADE_POR_NOME[linha["intensidade"].strip()],
                linha["alvo"].strip() == "pessoa",
            )
    return tabela


# Simbolos usados para mascarar palavrao. `!` e `?` NAO entram: eles sao
# enfase, medida por `estilo_pontuacao_enfatica`, e incluir aqui faria "!!!"
# contar como xingamento censurado.
#
# DIGITO NAO ENTRA, e isso nao e descuido: enquanto `0 1 3 4` moravam aqui,
# qualquer token feito so de digito ("400", "1043", "10") satisfazia o ramo do
# simbolo puro, era contado como xingamento mascarado inequivoco e ainda tinha
# cada caractere curingado ate resolver um termo curto do lexicon -- "400" saia
# como intensidade PESADA. Numero de pedido, preco, data e protocolo sao os
# tokens mais comuns de um chat de atendimento, e o simulador nao emite digito
# nenhum: a feature ficava limpa no treino e suja em producao, com o peso
# aprendido sobre um significado e aplicado a outro. O lugar do digito e so
# `HOMOGLIFOS`, onde ele serve para `p0rra` -> `porra`. Nao "conserte" a
# assimetria acrescentando `5` aqui: isso alarga o bug para "5" e "50%".
SIMBOLOS_CENSURA = set("*@#$%&")

# Homoglifos: o que o cliente digita -> a letra que ele quis dizer. Sem isso o
# lexicon erra TODA ocorrencia censurada, que e justamente a mais interessante.
HOMOGLIFOS = str.maketrans({
    "@": "a", "4": "a",
    "0": "o",
    # "!" NAO entra aqui: `PALAVRA` nao o inclui, entao ele nunca chega a uma
    # palavra -- e mapeamento inalcancavel e some numa refatoracao futura.
    "1": "i",
    "3": "e",
    "$": "s", "5": "s",
    # "*", "#", "%" e "&" NAO mapeiam para uma letra fixa: um asterisco pode
    # mascarar qualquer letra (p*rra -> porra, c*ralho -> caralho), e chutar
    # uma vogal fixa acertaria um caso e erraria o outro em silencio. Quem
    # casa palavra censurada contra o lexicon e `casar_censurado`, tratando
    # cada simbolo como curinga de uma letra qualquer -- nao esta funcao.
    "*": "", "#": "", "%": "", "&": "",
})
# Nota: so `* @ # $ % &` estao em `SIMBOLOS_CENSURA`; os digitos `0 1 3 4 5`
# vivem exclusivamente aqui. Palavra sem simbolo de mascara (`p0rra`) nao passa
# por `tem_censura` e e resolvida por este `translate`; palavra com simbolo
# (`c@r@lh0`) vai para `casar_censurado`, que aplica o mesmo mapeamento aos
# caracteres que NAO sao mascara antes de curingar o resto.

# Separador de palavra que PRESERVA simbolo de censura: `\w` sozinho quebraria
# "p*rra" em "p" e "rra" e a censura sumiria antes de ser contada.
PALAVRA = re.compile(r"[\w" + re.escape("*@#$%&") + r"]+", re.UNICODE)


def _sem_acento(palavra: str) -> str:
    """Minusculas, sem acento -- so isso, sem mexer em simbolo de mascara.

    Base compartilhada por `normalizar` (que ainda reverte homoglifo) e por
    `casar_censurado` (que precisa dos simbolos de mascara intactos).
    """
    return "".join(
        c
        for c in unicodedata.normalize("NFD", palavra.lower())
        if unicodedata.category(c) != "Mn"
    )


def normalizar(palavra: str) -> str:
    """Minusculas, sem acento, homoglifos revertidos.

    Roda DEPOIS de `tem_censura`, nunca antes: ela apaga exatamente a marca que
    a outra funcao precisa ver.
    """
    return _sem_acento(palavra).translate(HOMOGLIFOS)


def tem_censura(palavra: str) -> bool:
    """A palavra mistura letra e simbolo de mascara, ou e so simbolo.

    Autocensura e raiva COM autocontrole -- estado diferente de raiva crua, e
    por isso tem feature propria em vez de virar so mais um palavrao.
    """
    if not palavra:
        return False
    simbolos = sum(1 for c in palavra if c in SIMBOLOS_CENSURA)
    if simbolos == 0:
        return False
    letras = sum(1 for c in palavra if c.isalpha())
    # So mascara (`#@$%`) e censura pura; letra + mascara (`p*rra`) tambem.
    # Numero sozinho ("2024", "400") nao e: nenhum digito e mascara, entao um
    # token puramente numerico nem chega aqui (fica no `simbolos == 0`), e um
    # token que misture digito e mascara sem letra ("4*0") cai fora do `all`.
    return letras > 0 or all(c in SIMBOLOS_CENSURA for c in palavra)


def casar_censurado(
    palavra: str, lexicon: dict[str, tuple[float, bool]]
) -> tuple[float, bool] | None:
    """Casa palavra mascarada contra o lexicon tratando cada simbolo como UMA letra qualquer.

    `p*rra` casa `porra`, `c*ralho` casa `caralho`. Mapear o simbolo para uma
    vogal fixa acertaria o primeiro e erraria o segundo -- e erraria calado,
    que e pior.

    O caractere que NAO e mascara passa pelo mapeamento de homoglifo antes de
    virar literal: sem isso `c@r@lh0` geraria o padrao `c.r.lh0`, que nao casa
    `caralho` porque o `0` continuaria digito.
    """
    padrao = "".join(
        "." if c in SIMBOLOS_CENSURA else re.escape(c.translate(HOMOGLIFOS))
        for c in _sem_acento(palavra)
    )
    regex = re.compile(f"^{padrao}$")
    melhor: tuple[float, bool] | None = None
    for termo, entrada in lexicon.items():
        if not regex.match(termo):
            continue
        # Mais de um termo do lexicon pode casar o mesmo padrao com curinga
        # (ex.: "p..a" casa "poha" e "puta"). Desempatar pela ORDEM do CSV
        # deixaria a intensidade dependente de onde a linha foi inserida --
        # um bug silencioso a espera de uma edicao futura no arquivo. Em vez
        # disso, o desempate e deterministico: fica o casamento de MAIOR
        # intensidade, que e a leitura mais conservadora do sinal.
        if melhor is None or entrada[0] > melhor[0]:
            melhor = entrada
    return melhor


# Siglas que sao caixa alta sem serem gritaria. Sem esta lista, "preciso do CPF"
# marcaria enfase que nao existe.
SIGLAS = {
    "CPF", "CNPJ", "NF", "NFE", "SAC", "PIX", "CEP", "RG", "ID", "OK",
    "SP", "RJ", "MG", "PR", "RS", "BA", "PE", "CE", "DF", "GO",
    "SMS", "PDF", "URL", "APP", "TV", "PC", "USB", "CD", "DVD",
}

# Piso de comprimento para uma palavra maiuscula contar como grito. Palavra de
# 1-2 letras em caixa alta e quase sempre sigla ou digitacao apressada.
#
# Revisado em 03/09/2026 contra Burgers, van Mulken & Schellens (2012),
# Ptacek, Habernal & Hong (COLING 2014) e Bouazizi & Ohtsuki: nenhum dos tres
# fixa um piso numerico de comprimento para "palavra maiuscula". Burgers trata
# capitalizacao como categoria qualitativa de marcador tipografico, sem
# threshold. Ptacek usa contagem continua normalizada ("numero de palavras
# maiusculas" / total de palavras) -- nao um corte binario por tamanho.
# Bouazizi & Ohtsuki descrevem features de pontuacao e padrao sem detalhar um
# piso de letras para maiuscula. Mantido o valor de tres por falta de fonte
# que indique outro numero -- e limitacao declarada, nao calibracao.
MINIMO_CAIXA_ALTA = 3

# Quantas repeticoes seguidas do mesmo caractere marcam alongamento. Duas nao
# bastam: "carro", "passar" e "nossa" sao grafia normal do portugues.
#
# Revisado em 03/09/2026 contra a mesma bibliografia: Ptacek et al. (2014) nao
# lista alongamento de caractere entre as features de "Word-case" ou
# "Punctuation-based" da Tabela 1 -- o fenomeno simplesmente nao aparece no
# artigo. Burgers (2012) e Bouazizi & Ohtsuki tambem nao quantificam um numero
# de repeticoes. Nenhuma das tres fontes contradiz ou sustenta o valor de
# tres; ele fica como esta por nao haver base bibliografica para mudar, nao
# porque a bibliografia o confirme.
MINIMO_ALONGAMENTO = 3

# Riso alongado e o marcador POSITIVO mais comum de chat brasileiro. Contar
# "kkkk" junto de "naooooo" inverteria o sentido da feature em boa parte das
# conversas, entao ele tem excecao explicita.
LETRAS_DE_RISO = set("kh")

# Revisado em 03/09/2026: Ptacek et al. (2014) tratam exclamacao e interrogacao
# como contagens continuas (normalizadas pelo maximo observado), nao como um
# corte de "2 ou mais sinais seguidos". Burgers (2012) cita pontuacao como
# categoria de marcador tipografico sem numero. Bouazizi & Ohtsuki tratam "!"
# e "?" como indicadores de hiperbole, tambem sem threshold de repeticao
# consecutiva. Nenhuma fonte examinada especifica o corte de duas ou mais
# ocorrencias seguidas -- mantido por ausencia de base para trocar, nao por
# confirmacao bibliografica do numero exato.
PONTUACAO_ENFATICA = re.compile(r"[!?]{2,}")


def _e_grito(palavra: str) -> bool:
    """Palavra em caixa alta que nao e sigla nem palavra curta."""
    return (
        len(palavra) >= MINIMO_CAIXA_ALTA
        and palavra.isupper()
        and any(c.isalpha() for c in palavra)
        and palavra not in SIGLAS
    )


def _tem_alongamento(palavra: str) -> bool:
    """Tres ou mais repeticoes do mesmo caractere, exceto riso."""
    minuscula = palavra.lower()
    repeticoes = 1
    for anterior, atual in zip(minuscula, minuscula[1:]):
        if atual != anterior:
            repeticoes = 1
            continue
        repeticoes += 1
        if repeticoes >= MINIMO_ALONGAMENTO and atual not in LETRAS_DE_RISO:
            return True
    return False


def estilo_da_mensagem(texto: str) -> dict:
    """A leitura de estilo de UMA fala, para a tela mostrar onde ela aconteceu.

    `features_estilo` agrega a conversa inteira -- e o que o fusor consome, e
    e a media que pesa na nota. Esta funcao responde outra pergunta: em QUAL
    mensagem a marca apareceu. Uma conversa com 5% de caixa alta pode ser uma
    fala gritada entre dezenove calmas ou vinte falas levemente enfaticas, e a
    media nao distingue as duas.

    As duas leituras compartilham as MESMAS funcoes auxiliares de proposito:
    duas implementacoes da pergunta "isto e um grito?" divergiriam na
    fronteira, e a tela passaria a marcar o que a feature nao marcou.
    """
    # Marcador de censura de PII ("[CPF]", "[EMAIL]" etc.) perde os colchetes
    # neste tokenizador e sobra maiusculo -- excluido aqui para nao contar
    # como grito nem como fala do cliente (ver `TOKENS_MARCADORES`).
    palavras = [p for p in PALAVRA.findall(texto) if p not in TOKENS_MARCADORES]
    lexicon = carregar_palavroes()

    intensidade_maxima = None
    dirigido = False
    censurada = False

    for palavra in palavras:
        if tem_censura(palavra):
            entrada = casar_censurado(palavra, lexicon)
            if any(c.isalpha() for c in palavra):
                if entrada is not None:
                    censurada = True
            else:
                censurada = True
        else:
            entrada = lexicon.get(normalizar(palavra))
        if entrada is not None:
            valor, alvo_pessoa = entrada
            if intensidade_maxima is None or valor > intensidade_maxima:
                intensidade_maxima = valor
            dirigido = dirigido or alvo_pessoa

    return {
        "caixa_alta": any(_e_grito(p) for p in palavras),
        "alongamento": any(_tem_alongamento(p) for p in palavras),
        "pontuacao_enfatica": len(PONTUACAO_ENFATICA.findall(texto)),
        # O MAXIMO e nao a media: numa fala so, a media diluiria o xingamento
        # pesado entre os leves da mesma frase, e o que a tela precisa
        # mostrar e o pior que apareceu ali.
        "palavrao": intensidade_maxima,
        "palavrao_dirigido": dirigido,
        "censura": censurada,
    }


def features_estilo(conversa: Conversa) -> dict[str, float]:
    """Agrega a FORMA da escrita das mensagens DO CLIENTE.

    Conversa sem fala do cliente devolve as seis features zeradas -- e ausencia
    de medida, e quem distingue "nao mediu" de "mediu e deu zero" e o
    `score: None` la em cima, nunca esta funcao (invariante 2).
    """
    textos = [m.texto for m in conversa.mensagens_cliente]
    vazio = {
        "estilo_frac_caixa_alta": 0.0,
        "estilo_pontuacao_enfatica": 0.0,
        "estilo_frac_alongamento": 0.0,
        "estilo_palavrao_intensidade": 0.0,
        "estilo_palavrao_dirigido": 0.0,
        "estilo_frac_censurado": 0.0,
    }
    if not textos:
        return vazio

    lexicon = carregar_palavroes()
    palavras: list[str] = []
    for texto in textos:
        # Mesma exclusao de `estilo_da_mensagem`: marcador de censura de PII
        # nao entra nem no numerador nem no denominador -- ele nao e palavra
        # do cliente, e conta-lo aqui inflaria toda fracao de estilo com uma
        # cicatriz que o proprio sistema deixou no texto ao censurar.
        palavras.extend(p for p in PALAVRA.findall(texto) if p not in TOKENS_MARCADORES)

    if not palavras:
        return vazio

    total = len(palavras)
    gritos = 0
    alongadas = 0
    censuradas = 0
    intensidades: list[float] = []
    dirigidos = 0

    for palavra in palavras:
        if _e_grito(palavra):
            gritos += 1
        if _tem_alongamento(palavra):
            alongadas += 1
        # O casamento (quando ha simbolo de censura) e feito na palavra CRUA,
        # com a mascara intacta -- nao na normalizada. Isso NAO inverte a
        # ordem censura-antes-de-normalizacao: `casar_censurado` so olha a
        # palavra original, entao a evidencia da mascara nunca e apagada
        # antes de ser usada, so decidimos o que fazer com o resultado dele
        # antes de chamar `normalizar`.
        if tem_censura(palavra):
            match = casar_censurado(palavra, lexicon)
            if any(c.isalpha() for c in palavra):
                # Palavra com letra + simbolo (`pedido2024`, `joao@gmail`) so
                # conta como autocensura se o curinga resolver um palavrao
                # DE VERDADE no lexicon -- senao a feature mediria "cliente
                # citou um codigo", nao autocensura, e ruido correlacionado
                # com atendimento normal e pior que feature ausente.
                if match is not None:
                    censuradas += 1
                entrada = match
            else:
                # Token so de simbolo (`#@$%`) nao tem o que resolver: e
                # xingamento mascarado inequivoco e conta sempre.
                censuradas += 1
                entrada = match
        else:
            entrada = lexicon.get(normalizar(palavra))
        if entrada is not None:
            intensidade, dirigido = entrada
            intensidades.append(intensidade)
            if dirigido:
                dirigidos += 1

    enfaticas = sum(len(PONTUACAO_ENFATICA.findall(t)) for t in textos)

    return {
        "estilo_frac_caixa_alta": gritos / total,
        "estilo_pontuacao_enfatica": enfaticas / len(textos),
        "estilo_frac_alongamento": alongadas / total,
        "estilo_palavrao_intensidade": (
            sum(intensidades) / len(intensidades) if intensidades else 0.0
        ),
        "estilo_palavrao_dirigido": (
            dirigidos / len(intensidades) if intensidades else 0.0
        ),
        "estilo_frac_censurado": censuradas / total,
    }
