"""Censura de dado sensivel ANTES de gravar e ANTES de inferir.

O texto original nunca chega ao disco nem ao classificador: `censurar_pii`
roda no ponto de entrada (ver `fraus/api/registro.py` e
`fraus/ingest/csv_driver.py`), sobre o texto de cada mensagem, antes de
`Conversa` existir. Isso resolve os dois riscos de uma vez -- PII em disco e
CPF virando token que o BERTimbau tenta interpretar.

POR QUE checksum onde da para ter: numero de pedido, protocolo e valor sao os
tokens mais comuns de um chat de atendimento, e apagar todos eles empobrece o
texto que alimenta os sinais -- o mesmo raciocinio que `fraus/sinais/estilo.py`
ja documenta para digito puro. CPF e cartao tem digito verificador, o que
reduz a duvida mas NAO a elimina: o digito verificador do CPF (`_cpf_valido`)
e exato -- so 11 digitos entre 10^10 fecham a conta, entao aceitar por engano
uma sequencia arbitraria e raro na pratica. Luhn (`_luhn_valido`), usado para
cartao, e mais fraco: aceita cerca de 1 em cada 10 sequencias de digitos
arbitrarias (o digito de checagem tem 10 valores possiveis e so um fecha a
conta). Um protocolo ou timestamp que por acaso bater no Luhn passa por
cartao. Exemplo real: "protocolo 20260903120000 aberto" (um timestamp
AAAAMMDDHHMMSS de 14 digitos, formato comum de protocolo de atendimento) vira
"protocolo [CARTAO] aberto" porque a sequencia fecha o Luhn por coincidencia.
Isso e falso-positivo aceito, nao bug: mascarar um protocolo custa uma feature
de estilo levemente mais pobre; deixar passar um cartao de verdade custa um
dado sensivel vazado. A assimetria de custo e o motivo de manter o checksum
mesmo sabendo que ele erra por excesso de zelo.

TELEFONE NAO TEM CHECKSUM, e ai a duvida e real: "12345678901" e um protocolo
ou um celular com DDD digitado corrido? Sao indistinguiveis. A decisao do Joao
em 03/09/2026 foi MASCARAR -- privacidade vence sinal, e um protocolo perdido
custa menos que um telefone vazado. E limitacao declarada, nao descuido.

LIMITACAO DECLARADA (falso-negativo): endereco e heuristica de "tipo de
logradouro + numero" e tem falso-negativo alto (endereco sem essas palavras
nao e pego). Nome proprio sozinho NAO e coberto: exigiria NER, que e modelo
a mais e esta fora do escopo. O que esta aqui e o que se identifica por
padrao deterministico.

LIMITACAO DECLARADA (falso-positivo): a primeira versao do padrao de endereco
casava a palavra solta ("rua", "avenida" etc.) e comia ate 60 caracteres
livres ate o proximo digito -- o que capturava prosa inteira sempre que um
numero aparecia depois, tipo hora do dia ou minutos de espera. Exemplo real:
"a rua estava cheia hoje as 20h" virava "a [ENDERECO]h", apagando exatamente
o relato de sentimento que os sete sinais leem. O texto do cliente e o
produto deste sistema -- perder frase de queixa custa mais caro que deixar
passar um endereco. Por isso o nome da via esta limitado a NO MAXIMO 3
palavras (grupo de ate 3 palavras entre o tipo de logradouro e o numero) em
vez de uma janela livre de caracteres: e esse limite que impede a
heuristica de comer prosa. NAO troque de volta para uma janela de
caracteres numa refatoracao futura -- e o falso-positivo
documentado acima que essa escolha existe para evitar. Ainda sobra
falso-positivo residual quando o nome da via tem 4+ palavras seguido de
numero de verdade (ex.: "entrega na rua 15 de novembro 200" so mascara
parte), mas isso e endereco de verdade sendo mascarado parcialmente, nao
prosa de sentimento sendo destruida -- o risco aceitavel, nao o evitado.
"""

import re

MARCADORES = {
    "cpf": "[CPF]",
    "email": "[EMAIL]",
    "telefone": "[TELEFONE]",
    "cartao": "[CARTAO]",
    "endereco": "[ENDERECO]",
}

# O miolo de cada marcador, sem colchetes -- "CPF", "EMAIL", etc. Derivado de
# `MARCADORES`, nunca digitado de novo: uma segunda lista aqui divergiria no
# dia em que alguem acrescentasse um marcador novo e esquecesse desta.
#
# Existe porque o regex de palavra dos sinais (`PALAVRA` em
# `fraus/sinais/estilo.py`, `_TOKEN` em `fraus/sinais/lexico.py`) nao inclui
# `[` nem `]` -- os colchetes caem fora do token, e o miolo maiusculo sobra
# como uma palavra de 3+ letras isupper(). Sem exclusao explicita, isso e
# contado como grito (`estilo_frac_caixa_alta`) e infla o denominador de toda
# fracao de estilo e de `lexico_cobertura`, mesmo o `[CPF]` nao sendo fala do
# cliente -- e uma cicatriz que o proprio sistema deixou no texto ao censurar.
# "[CPF]" escapava disso POR ACIDENTE ate agora, porque "CPF" ja estava em
# `SIGLAS` (o cliente escreve "meu CPF") -- os outros quatro marcadores nao
# tinham essa sorte. Nao remova esta exclusao achando-a redundante com
# `SIGLAS`: o acoplamento entre `sinais/` e `seguranca/` e deliberado, porque
# o silencio (duas listas que deveriam concordar e nao concordam) e pior do
# que o import explicito.
TOKENS_MARCADORES = frozenset(marcador.strip("[]") for marcador in MARCADORES.values())

# Formato do CPF: 11 digitos, com ou sem os separadores usuais. A validacao
# do digito verificador acontece depois, em `_cpf_valido`.
_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
# Telefone BR: +55 opcional, DDD opcional entre parenteses, 8 ou 9 digitos.
#
# `(?<!\d)` e `(?!\d)` NAO sao decoracao, e `\b` no lugar deles nao serve:
# digito e caractere de palavra, entao nao existe `\b` DENTRO de uma corrida
# de digitos, e o padrao casava no meio de um numero maior. Um cartao de 16
# digitos que falha no Luhn (numero de pedido longo, portanto) tinha os 11
# ultimos digitos comidos como se fossem telefone, saindo como
# "pedido 45395[TELEFONE]" -- mascaramento parcial, que e o pior dos dois
# mundos: nao protege o que era PII nem preserva o que nao era.
_TELEFONE = re.compile(r"(?<!\d)(?:\+55\s?)?(?:\(\d{2}\)|\d{2})[\s-]?\d{4,5}-?\d{4}(?!\d)")
# Cartao: 13 a 19 digitos, com ou sem espaco/hifen a cada quatro.
_CARTAO = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")
_ENDERECO = re.compile(
    r"(?:\b(?:rua|r|av|avenida|alameda|travessa|rodovia|praca)\.?\s+)"
    r"(?:[a-zà-ÿ]+\s+){0,3}?"
    r"(?:n[oº°.]*\s*)?\d{1,6}\b",
    re.IGNORECASE,
)


def _so_digitos(texto: str) -> str:
    return "".join(c for c in texto if c.isdigit())


def _cpf_valido(candidato: str) -> bool:
    """Digito verificador do CPF. Rejeita tambem as 10 sequencias repetidas."""
    digitos = _so_digitos(candidato)
    if len(digitos) != 11 or len(set(digitos)) == 1:
        return False
    for tamanho in (9, 10):
        soma = sum(
            int(digitos[i]) * (tamanho + 1 - i) for i in range(tamanho)
        )
        resto = (soma * 10) % 11
        esperado = 0 if resto == 10 else resto
        if esperado != int(digitos[tamanho]):
            return False
    return True


def _luhn_valido(candidato: str) -> bool:
    """Algoritmo de Luhn -- o mesmo que a bandeira usa para recusar digitacao."""
    digitos = [int(c) for c in _so_digitos(candidato)]
    if len(digitos) < 13:
        return False
    soma = 0
    for posicao, digito in enumerate(reversed(digitos)):
        if posicao % 2 == 1:
            digito *= 2
            if digito > 9:
                digito -= 9
        soma += digito
    return soma % 10 == 0


def censurar_pii(texto: str) -> str:
    """Mascara CPF, e-mail, telefone, cartao e endereco. Deterministico.

    A ORDEM importa: e-mail vem antes de telefone e cartao porque um e-mail
    pode conter digitos que o padrao de telefone casaria por dentro; cartao
    vem antes de telefone porque o padrao de cartao e mais longo e mais
    especifico (Luhn), e telefone casaria um pedaco dele.
    """
    if not texto:
        return texto

    texto = _EMAIL.sub(MARCADORES["email"], texto)
    texto = _CPF.sub(
        lambda m: MARCADORES["cpf"] if _cpf_valido(m.group()) else m.group(), texto
    )
    texto = _CARTAO.sub(
        lambda m: MARCADORES["cartao"] if _luhn_valido(m.group()) else m.group(),
        texto,
    )
    texto = _TELEFONE.sub(MARCADORES["telefone"], texto)
    texto = _ENDERECO.sub(MARCADORES["endereco"], texto)
    return texto
