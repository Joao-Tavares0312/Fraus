"""Peso de cada palavra na leitura do modelo, e o vocabulario da conversa.

DUAS COISAS DIFERENTES moram aqui, e confundi-las e o erro que este modulo
existe para evitar:

* **peso** (`pesos_das_palavras`) e quanto o MODELO mudou de opiniao por causa
  daquela palavra. E uma medida do modelo.
* **frequencia** (`vocabulario`) e quantas vezes a palavra apareceu. E uma
  medida do texto, e nao diz nada sobre o que o modelo achou dela.

Palavra muito repetida com peso zero e comum e nao e defeito -- e o modelo
dizendo que a repeticao nao mudou a leitura dele.

POR QUE OCLUSAO E NAO ATENCAO. O peso e medido apagando a palavra e
perguntando de novo: a diferenca entre a resposta com e sem ela E a
contribuicao. E lento (uma passada por palavra) e e o unico metodo desta lista
que responde exatamente a pergunta que a banca vai fazer -- "por que esta
frase recebeu esta nota?". Peso de atencao e frequentemente lido como
explicacao e nao e: atencao alta marca a palavra que o modelo OLHOU, nao a que
mudou a decisao dele, e a literatura ja mostrou os dois divergindo. Gradiente
integrado responderia bem tambem, mas exige backward pass e escolha de
baseline, complexidade que nao se paga aqui.
"""

import re
import unicodedata
from collections import Counter

from fraus.modelos import Conversa
from fraus.sinais.texto import INSATISFEITO, SATISFEITO

# Teto de palavras que recebem peso numa mesma mensagem. Cada palavra custa uma
# passada de BERTimbau: sem teto, uma mensagem colada de 500 palavras viraria
# 500 inferencias e a requisicao penduraria. As palavras alem do teto ficam
# SEM peso (`None`), nunca com peso zero -- zero afirmaria que a palavra nao
# importou, quando a verdade e que ela nao foi medida.
TETO_PALAVRAS_POR_MENSAGEM = 60

# Separador de palavra que preserva a posicao no texto original: a interface
# precisa dos indices para grifar o trecho sem re-tokenizar por conta propria.
PALAVRA = re.compile(r"\w+(?:['’-]\w+)*", re.UNICODE)

# Palavras funcionais do portugues. Elas dominam qualquer contagem de
# frequencia -- "de", "que" e "nao" seriam sempre as tres mais usadas de toda
# conversa, em toda operacao, o que nao informa nada.
#
# Elas so saem do VOCABULARIO. Continuam valendo peso normalmente: "nao" muda
# a leitura de uma frase inteira, e apaga-la da atribuicao esconderia
# exatamente a palavra mais decisiva de uma negacao.
VAZIAS = frozenset("""
a as o os um uma uns umas de do da dos das em no na nos nas por para pra pro
com sem sob sobre entre ate apos e ou mas porem contudo entao que se quando
onde como qual quais quanto quantos eu tu ele ela nos vos eles elas me te lhe
se nos vos lhes meu minha meus minhas teu tua seu sua seus suas nosso nossa
este esta isto esse essa isso aquele aquela aquilo ja ainda mais menos muito
pouco tao tanto bem mal aqui ai ali la e ser sou es somos sao era eram foi
foram sido estar estou esta estamos estao estava estive ter tem tenho temos
tinha tive havia ha haver fazer faz faco fez do la vc voce voces
""".split())


def normalizar(palavra: str) -> str:
    """Minuscula e sem acento, para a contagem nao separar "nao" de "não"."""
    sem_acento = unicodedata.normalize("NFKD", palavra.lower())
    return "".join(c for c in sem_acento if not unicodedata.combining(c))


def _eixo(probabilidades: list[float]) -> float:
    """Satisfeito menos insatisfeito: um eixo unico, com sinal.

    O neutro fica de fora de proposito -- ele nao tem direcao, e somar meio
    neutro aqui misturaria "o modelo achou bom" com "o modelo nao se decidiu".
    """
    return probabilidades[SATISFEITO] - probabilidades[INSATISFEITO]


def pesos_das_palavras(texto: str, classificador) -> list[dict]:
    """Quanto cada palavra empurrou a leitura da mensagem, por oclusao.

    Devolve, para cada palavra: a posicao no texto original (`inicio`/`fim`,
    para a interface grifar sem re-tokenizar), a palavra e o `peso`.

    SINAL DO PESO: positivo quer dizer que a palavra empurrou para SATISFEITO
    -- tira-la derrubaria a leitura. Negativo puxou para insatisfeito. Zero e
    uma medicao de verdade ("apagar esta palavra nao mudou nada"); `None` e
    ausencia de medicao, e os dois nao podem se confundir na tela.

    Todas as variantes vao numa unica chamada ao classificador: sao N+1 textos
    (o inteiro mais um por palavra apagada) num batch so, em vez de N+1
    chamadas.

    LIMITACAO A DECLARAR NA TELA -- apagar uma palavra de dentro de uma
    expressao fixa deixa um fragmento que ninguem escreveria, e o modelo
    responde ao fragmento. Medido em "Bom dia. Minha cobranca veio duplicada":
    "dia" recebe -0,54, um peso alto e enganoso, porque a frase sem ela vira
    "Bom . Minha cobranca veio duplicada" e o "Bom" solto puxa a leitura para
    cima. O peso e verdadeiro sobre O QUE O MODELO FAZ e nao deve ser lido como
    "esta palavra significa insatisfacao". Vale para qualquer metodo de
    oclusao, e e o preco de nao usar gradiente.
    """
    ocorrencias = list(PALAVRA.finditer(texto))
    if not ocorrencias:
        return []

    medidas = ocorrencias[:TETO_PALAVRAS_POR_MENSAGEM]
    sem_medida = ocorrencias[TETO_PALAVRAS_POR_MENSAGEM:]

    # Apagar de verdade, nao substituir por mascara: o objetivo e a frase que
    # sobra sem aquela palavra, do jeito que um humano a leria.
    variantes = [texto]
    for ocorrencia in medidas:
        variantes.append(
            (texto[: ocorrencia.start()] + texto[ocorrencia.end():]).strip()
        )

    previsoes = classificador.prever_mensagens(variantes)
    eixo_inteiro = _eixo(previsoes[0])

    pesos = [
        {
            "palavra": ocorrencia.group(),
            "inicio": ocorrencia.start(),
            "fim": ocorrencia.end(),
            "peso": eixo_inteiro - _eixo(previsao),
        }
        for ocorrencia, previsao in zip(medidas, previsoes[1:])
    ]
    pesos.extend(
        {
            "palavra": ocorrencia.group(),
            "inicio": ocorrencia.start(),
            "fim": ocorrencia.end(),
            "peso": None,  # acima do teto: nao medida, nao "sem efeito"
        }
        for ocorrencia in sem_medida
    )
    return pesos


def contar_palavras(textos: list[str]) -> Counter:
    """Frequencia das palavras de conteudo, normalizadas e sem as funcionais."""
    contagem: Counter = Counter()
    for texto in textos:
        for ocorrencia in PALAVRA.finditer(texto):
            normalizada = normalizar(ocorrencia.group())
            # Numero solto nao e vocabulario, e "3" aparece em toda conversa
            # sobre prazo e protocolo sem dizer nada sobre o assunto dela.
            if normalizada in VAZIAS or normalizada.isdigit() or len(normalizada) < 3:
                continue
            contagem[normalizada] += 1
    return contagem


def vocabulario(
    conversa: Conversa, referencia: Counter | None = None, limite: int = 12
) -> list[dict]:
    """Palavras mais usadas pelo CLIENTE nesta conversa, comparadas ao conjunto.

    `destaque` e quantas vezes a palavra e mais frequente aqui do que na
    referencia -- 3.0 quer dizer "o triplo do normal nesta operacao". E o campo
    que responde "o que ESTA conversa tem de diferente", que a contagem crua
    nao responde: as palavras mais repetidas de qualquer atendimento sao as
    mesmas de todos os outros.

    Sem referencia (ou com a palavra ausente dela), `destaque` sai `None` --
    nao ha com o que comparar, e inventar 1.0 afirmaria "igual a media" sem
    ter medido media nenhuma.

    So a fala do cliente entra. O texto do bot e roteiro escrito por quem
    montou o fluxo: contar as palavras dele mediria o script, nao o cliente.
    """
    textos = [m.texto for m in conversa.mensagens_cliente]
    contagem = contar_palavras(textos)
    total = sum(contagem.values())
    if total == 0:
        return []

    total_referencia = sum(referencia.values()) if referencia else 0

    itens = []
    for palavra, vezes in contagem.most_common(limite):
        destaque = None
        if referencia and total_referencia and referencia.get(palavra):
            frequencia_aqui = vezes / total
            frequencia_geral = referencia[palavra] / total_referencia
            destaque = frequencia_aqui / frequencia_geral
        itens.append({"palavra": palavra, "vezes": vezes, "destaque": destaque})
    return itens
