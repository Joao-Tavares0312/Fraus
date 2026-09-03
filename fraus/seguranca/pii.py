"""Censura de dado sensivel ANTES de gravar e ANTES de inferir.

O texto original nunca chega ao disco nem ao classificador: `censurar_pii`
roda no ponto de entrada (ver `fraus/api/registro.py` e
`fraus/ingest/csv_driver.py`), sobre o texto de cada mensagem, antes de
`Conversa` existir. Isso resolve os dois riscos de uma vez -- PII em disco e
CPF virando token que o BERTimbau tenta interpretar.

POR QUE checksum onde da para ter: numero de pedido, protocolo e valor sao os
tokens mais comuns de um chat de atendimento, e apagar todos eles empobrece o
texto que alimenta os sinais -- o mesmo raciocinio que `fraus/sinais/estilo.py`
ja documenta para digito puro. CPF e cartao tem digito verificador, entao para
esses dois a duvida nao existe: ou o numero fecha a conta ou nao e um deles.

TELEFONE NAO TEM CHECKSUM, e ai a duvida e real: "12345678901" e um protocolo
ou um celular com DDD digitado corrido? Sao indistinguiveis. A decisao do Joao
em 03/09/2026 foi MASCARAR -- privacidade vence sinal, e um protocolo perdido
custa menos que um telefone vazado. E limitacao declarada, nao descuido.

LIMITACAO DECLARADA: endereco e heuristica de "tipo de logradouro + numero" e
tem falso-negativo alto (endereco sem essas palavras nao e pego). Nome
proprio sozinho NAO e coberto: exigiria NER, que e modelo a mais e esta fora
do escopo. O que esta aqui e o que se identifica por padrao deterministico.
"""

import re

MARCADORES = {
    "cpf": "[CPF]",
    "email": "[EMAIL]",
    "telefone": "[TELEFONE]",
    "cartao": "[CARTAO]",
    "endereco": "[ENDERECO]",
}

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
    r"\b(?:rua|av|avenida|alameda|travessa|rodovia|praca)\b[^,.;\n]{0,60}?\d+",
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
