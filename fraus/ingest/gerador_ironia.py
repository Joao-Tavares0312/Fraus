"""Gerador de corpus sintetico de ironia em atendimento.

POR QUE ESTE MODULO EXISTE. Nao ha corpus de ironia PT-BR aberto, com texto e
em tamanho treinavel. Levantamento de 14/08/2026, em docs/treinamento.md: o
IDPT 2021 nao tem download livre; `arbml/multilingual_irony` traz so IDs de
tweet, sem texto; o unico candidato aberto (Goncalves et al., BraSNAM 2015 --
"Bazinga!") coletou tweets pelas hashtags #sarcasm e #irony, ou seja, e corpus
em INGLES. Traduzir reintroduziria o vazamento de procedencia que ja custou o
primeiro fusor.

Some-se a isso que NENHUM corpus de ironia existe no dominio de atendimento,
em lingua nenhuma. Mesmo o IDPT liberado seria transferencia de dominio nao
verificada -- tweets e comentario de noticia, nao suporte.

E o mesmo impasse do sinal de tempo, e a mesma saida: gerar. Ver
`fraus.ingest.simulador`, que existe porque nenhum corpus de review tem
timestamps.

LIMITACAO METODOLOGICA, a declarar no relatorio: a ironia aqui e SINTETICA e
segue padroes declarados neste arquivo. Ironia real e mais variada, mais
sutil e depende de contexto que uma frase isolada nao carrega. As metricas do
notebook 04 sao OTIMISTAS por construcao -- elas medem o quanto o modelo
aprendeu estes padroes, nao o quanto ele le ironia humana. O conjunto de teste
independente e o unico numero honesto para o relatorio (ver `docs`).

O QUE FOI FEITO PARA NAO VAZAR O GABARITO
-----------------------------------------
A armadilha obvia seria: ironico = elogio + fato ruim; nao-ironico = tudo o
mais. Um modelo treinado nisso aprenderia "tem fato ruim -> ironia" ou "tem
palavra elogiosa -> ironia" e acertaria quase tudo sem ler a INCONGRUENCIA,
que e o proprio fenomeno.

Tres cruzamentos deliberados impedem isso:

1. os MESMOS fatos ruins aparecem nas reclamacoes diretas (nao-ironicas). Fato
   ruim sozinho nao separa classe;
2. as MESMAS palavras elogiosas aparecem nos elogios sinceros e ate em
   reclamacoes ("obrigado, mas nao resolveu"). Lexico positivo sozinho nao
   separa classe;
3. numero e unidade de tempo ("3 horas", "quinta vez") aparecem nas duas
   classes, inclusive nos elogios sinceros ("resolveram em 2 minutos").

O que resta como sinal e so a relacao entre as duas partes -- que e o que se
quer ensinar.
"""

import random

from fraus.sinais.ironia import IRONICO, NAO_IRONICO

# Predicados elogiosos. Aparecem nas TRES situacoes: ironia, elogio sincero e
# reclamacao com agradecimento -- por isso nao servem de atalho.
ELOGIOS = [
    "adorei", "amei", "que maravilha", "excelente", "otimo", "perfeito",
    "que servico impecavel", "nota dez", "parabens", "sensacional",
    "que atendimento incrivel", "show de bola", "muito bom",
]

# Fatos com carga NEGATIVA. Usados tanto na ironia (colados a um elogio)
# quanto na reclamacao direta (colados a uma queixa).
FATOS_RUINS = [
    "esperar 3 horas na linha",
    "ser transferido cinco vezes",
    "repetir meu CPF para quatro atendentes",
    "ficar duas semanas sem resposta",
    "receber o produto errado de novo",
    "o app cair no meio do pagamento",
    "ninguem resolver nada",
    "abrir o quarto chamado sobre a mesma coisa",
    "a cobranca duplicada continuar la",
    "ouvir a mesma musica de espera por 40 minutos",
    "o prazo estourar pela terceira vez",
    "ter que ligar de novo amanha",
]

# Fatos com carga POSITIVA. So aparecem no elogio sincero, mas carregam numero
# e unidade de tempo tal como os ruins -- para que "tem numero" nao vire pista.
FATOS_BONS = [
    "resolverem em 2 minutos",
    "o reembolso cair no mesmo dia",
    "atenderem no primeiro toque",
    "trocarem o produto em 24 horas",
    "explicarem tudo com paciencia",
    "resolverem sem eu precisar repetir nada",
    "o tecnico chegar na hora marcada",
    "cancelarem a cobranca duplicada na hora",
]

QUEIXAS = [
    "que absurdo", "inaceitavel", "que descaso", "estou indignado",
    "que raiva", "nao da mais", "que decepcao", "cansei",
]

# Falas operacionais, sem carga. Existem para o modelo nao aprender que toda
# frase sem elogio e reclamacao.
NEUTRAS = [
    "qual o prazo de entrega do pedido 4471",
    "consigo alterar o endereco de cobranca",
    "boa tarde, gostaria da segunda via do boleto",
    "voces atendem no sabado",
    "qual o numero do protocolo",
    "preciso do CNPJ da empresa para a nota",
    "como faco para cancelar a assinatura",
    "o pedido ja saiu para entrega",
    "aceita pagamento por pix",
    "onde vejo meu historico de chamados",
]

# Conectores da estrutura ironica: elogio + fato ruim.
LIGACOES_IRONICAS = [
    "{elogio}, {fato}",
    "{elogio}! {fato} foi otimo",
    "{elogio} mesmo, {fato}",
    "{elogio}, so precisei {fato}",
    "so faltou {fato} para ficar perfeito, {elogio}",
    "{elogio} pela oportunidade de {fato}",
    "nada como {fato} para comecar bem o dia, {elogio}",
]

# Ironia por ATENUACAO, sem palavra elogiosa nenhuma: o exagero as avessas.
# Sem esta familia, "tem elogio" viraria condicao necessaria de ironia.
#
# Esta lista precisa ser GRANDE o bastante para nao saturar: ela concorre com
# ELOGIOS x LIGACOES_IRONICAS, que sozinho passa de mil combinacoes. Com
# poucos moldes, a familia se esgota, a deduplicacao a corta e "ironia tem
# elogio" volta a ser quase-verdade no corpus -- que e o atalho que ela existe
# para impedir. Ha teste travando essa proporcao.
ATENUACOES = [
    "imagina, {fato} nao incomoda nada",
    "tranquilo, {fato} e exatamente o que eu queria hoje",
    "que sorte a minha, {fato}",
    "adivinha: {fato}. surpresa zero",
    "claro, {fato}. era so o que faltava",
    "relaxa, {fato} faz parte da experiencia",
    "nem precisava, mas obrigado por {fato}",
    "eu ja esperava {fato}, entao ta tudo certo",
    "sem pressa, {fato} nao muda nada mesmo",
    "olha so, {fato}. quem diria",
    "{fato} de novo? nossa, que novidade",
    "fantastico: {fato}",
    "e claro que ia acabar em {fato}",
    "de novo {fato}. ja virou tradicao",
    "top demais {fato}, recomendo a experiencia",
    "so o de sempre: {fato}",
    "previsivel, {fato}",
    "quase perfeito, faltou so {fato}",
]

LIGACOES_ELOGIO = [
    "{elogio}, {fato}",
    "{elogio}! obrigado por {fato}",
    "{elogio} mesmo, {fato} me salvou",
    "{fato} foi otimo, {elogio}",
]

# A reclamacao direta reutiliza FATOS_RUINS -- e o cruzamento que impede o
# modelo de ler "fato ruim" como gabarito de ironia. Duas delas comecam com
# agradecimento, para que lexico positivo tambem apareca fora da ironia.
LIGACOES_QUEIXA = [
    "{queixa}, {fato}",
    "{fato} de novo. {queixa}",
    "{queixa}! tive que {fato}",
    "obrigado pela atencao, mas {fato} e {queixa}",
    "agradeco o retorno, so que {fato}. {queixa}",
]

# Emojis com CRUZAMENTO, pelo mesmo motivo do simulador: se o emoji sorridente
# so aparecesse na ironia, ele viraria o novo gabarito.
EMOJIS = ["🙂", "😊", "👏", "👍", "😡", "😒", "😅", "🙏", ""]
PROB_EMOJI = 0.35


def _talvez_emoji(aleatorio: random.Random, texto: str) -> str:
    if aleatorio.random() >= PROB_EMOJI:
        return texto
    emoji = aleatorio.choice(EMOJIS)
    return f"{texto} {emoji}".strip()


def _talvez_maiuscula(aleatorio: random.Random, texto: str) -> str:
    """Variacao de caixa e pontuacao final.

    Sem isto, a frase ironica sairia sempre em minuscula e sem ponto final
    enquanto a neutra viria em outra forma -- e o modelo leria a FORMATACAO.
    """
    sorteio = aleatorio.random()
    if sorteio < 0.25:
        texto = texto[0].upper() + texto[1:] if texto else texto
    if sorteio > 0.80:
        texto = texto + aleatorio.choice([".", "!", "..."])
    return texto


def gerar_exemplos(quantidade: int, semente: int = 42) -> list[tuple[str, int]]:
    """`quantidade` pares (texto, rotulo), equilibrados e sem repeticao.

    Metade ironica, metade nao-ironica. A metade nao-ironica se divide entre
    elogio sincero, reclamacao direta e fala operacional -- as tres precisam
    existir para que "nao e elogio" nao vire atalho para "nao e ironia".
    """
    aleatorio = random.Random(semente)
    vistos: set[str] = set()
    exemplos: list[tuple[str, int]] = []

    def acrescentar(texto: str, rotulo: int) -> None:
        texto = _talvez_maiuscula(aleatorio, _talvez_emoji(aleatorio, texto))
        chave = texto.lower().strip()
        if chave in vistos:
            return
        vistos.add(chave)
        exemplos.append((texto, rotulo))

    # O espaco de combinacoes e FINITO. Pedir mais do que ele comporta nao
    # pode travar nem repetir: o laco desiste depois de `PACIENCIA` sorteios
    # seguidos sem nenhum texto novo, e devolve o que conseguiu.
    #
    # A parada e por ESGOTAMENTO, nao por um teto proporcional a `quantidade`:
    # teto proporcional faz um pedido absurdo custar tempo absurdo antes de
    # desistir, mesmo com o espaco ja exaurido nos primeiros milhares.
    PACIENCIA = 2_000
    sem_novidade = 0
    ironicos = 0

    while len(exemplos) < quantidade and sem_novidade < PACIENCIA:
        antes = len(exemplos)
        alvo_ironico = ironicos < quantidade / 2

        if alvo_ironico:
            fato = aleatorio.choice(FATOS_RUINS)
            if aleatorio.random() < 0.75:
                molde = aleatorio.choice(LIGACOES_IRONICAS)
                acrescentar(
                    molde.format(elogio=aleatorio.choice(ELOGIOS), fato=fato), IRONICO
                )
            else:
                acrescentar(aleatorio.choice(ATENUACOES).format(fato=fato), IRONICO)
            if len(exemplos) > antes:
                ironicos += 1
                sem_novidade = 0
            else:
                sem_novidade += 1
            continue

        familia = aleatorio.random()
        if familia < 0.34:
            acrescentar(
                aleatorio.choice(LIGACOES_ELOGIO).format(
                    elogio=aleatorio.choice(ELOGIOS), fato=aleatorio.choice(FATOS_BONS)
                ),
                NAO_IRONICO,
            )
        elif familia < 0.72:
            acrescentar(
                aleatorio.choice(LIGACOES_QUEIXA).format(
                    queixa=aleatorio.choice(QUEIXAS), fato=aleatorio.choice(FATOS_RUINS)
                ),
                NAO_IRONICO,
            )
        else:
            acrescentar(aleatorio.choice(NEUTRAS), NAO_IRONICO)

        sem_novidade = 0 if len(exemplos) > antes else sem_novidade + 1

    return exemplos
