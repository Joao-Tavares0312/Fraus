"""Quando o tempo contesta o elogio: a marca que acompanha o numero.

A frase canonica do projeto -- "que atendimento maravilhoso, so esperei 3
horas" -- e o caso de manual da ironia de atendimento, e o sistema a le como
elogio sincero: a cabeca de texto da 0,858 de satisfeito para ela.
`incongruencia_situacao_negativa` entrou no vetor em 04/09/2026 para alcanca-la:
dispara e PERDE, porque pesa -0,193 contra os +2,78 de
`texto_prob_satisfeito_media`. Nenhuma feature agregada de conversa reverte uma
probabilidade saturada por mensagem.

QUANTO A CONVERSA DE FATO PONTUA DEPENDE DO RELOGIO, e isto foi MEDIDO em
08/09/2026 contra a API real, com a mesma fala e so a latencia variando:

    latencia    score    nota  categoria   contestada
        10 s    99,92      10  promotor    --
       179 s    99,70      10  promotor    --
       181 s    99,69      10  promotor    SIM
       300 s    99,21      10  promotor    SIM
       600 s    93,25       9  promotor    --
      1800 s    17,19       2  detrator    --
     10800 s     0,00       0  detrator    --

O "99,93" que circula na documentacao deste projeto e o caso RAPIDO -- que e
real e comum: o cliente abre um atendimento novo e ironiza sobre uma espera que
aconteceu FORA daquele log. Com as 3 horas dentro do proprio log, o relogio ja
derruba o score sozinho.

E POR ISSO QUE A JANELA DA MARCA E ESTREITA DE PROPOSITO, e a estreiteza e a
feature: abaixo de 180 s nao ha contradicao para marcar, acima de ~10 min o
modelo ja acerta sem ajuda. A contestacao cobre so a faixa de ~3 a ~9 minutos,
onde o texto satura e o tempo ainda nao venceu. Se um dia ela parecer inutil
por marcar pouco, e este paragrafo que precisa ser lido antes de alarga-la.

REGRA DECLARADA, NAO PESO APRENDIDO -- e isso e decisao, nao atalho. A rota
obvia seria uma feature 40 cruzando tempo x texto, que e o que a literatura
indica (Riloff et al., EMNLP 2013: sarcasmo como contraste entre sentimento
positivo e situacao negativa). O corpus impede: o fusor treina com texto do
B2W-Reviews01 costurado na ESTRUTURA de conversa do simulador, onde a latencia
sai de distribuicao log-normal POR ROTULO. A interacao "texto saturado x
latencia alta" so e nao-nula nas caudas que se cruzam -- os ~11% de conversas
satisfeitas que sairam lentas -- e todas elas estao rotuladas SATISFEITO, por
construcao. O corpus nao contem um unico exemplo de "elogio + espera longa =
insatisfacao"; contem o contrario. A feature nasceria com peso POSITIVO,
empurrando para satisfeito exatamente onde deveria derrubar: o mesmo modo de
falha que tirou `ironia_prob_media`/`ironia_prob_max` do vetor em 04/09/2026,
com roupa nova. E `test_nenhuma_feature_e_previsor_unilateral` nao pegaria --
ela nao seria unilateral, so estaria com o sinal trocado.

ELA MARCA, NAO CORRIGE. Score, nota e categoria seguem intactos e o atendimento
CONTINUA CONTANDO no NPS, no CSAT e na contencao. Duas alternativas foram
recusadas e o motivo importa: tirar do agregado seria mais honesto no caso
isolado e mais perigoso no conjunto (limiar mal calibrado esvazia o indicador
em silencio, e "quantos atendimentos sumiram?" e a primeira pergunta que se
faz); rebaixar para neutro inventaria um veredito que o modelo nao produziu.

FUNCAO PURA, SEM BANCO E SEM MODELO. Modulo proprio e nao `indicadores.py`
(aquele e a regua do NPS) nem `resumo.py` (cuja `resumir` nao recebe o score).

Base formal: The Art of Abstention (ACL 2021) -- a regra de Chow, decidir
acima de um limiar de confianca -- com a diferenca deliberada de que aqui a
abstencao NAO apaga o numero. Desenho completo em
`docs/superpowers/specs/2026-09-08-abstencao-por-contestacao-design.md`.
"""

# O lado do TEMPO tem procedencia publicada: 57% de abandono acima de 3
# minutos (From Seconds to Sentiments, IJHCI 2025), a mesma referencia que
# `fraus/sinais/tempo.py` ja cita no topo. O numero nao e gosto nosso.
LIMIAR_LATENCIA_S = 180.0

# O lado do TEXTO e o unico numero deste modulo SEM procedencia -- esta
# declarado assim de proposito, aqui e na spec. 95 e onde um score deixa de
# ser "alto" e vira "saturado": acima dele o fusor esta dizendo que nao tem
# duvida, e e a ausencia de duvida que a espera longa contradiz.
#
# E o SCORE GRAVADO, e nao `texto_prob_satisfeito_media`, porque a leitura
# obriga: o banco guarda score, categoria e o payload (`fraus/db.py`), e as 39
# features nao sao persistidas -- recalcula-las por linha significaria rodar o
# BERTimbau em toda listagem, e este projeto ja teve incidente de CPU
# bloqueando o event loop do uvicorn. A troca ainda sai ganhando em tres
# pontos: nenhuma chamada de modelo na leitura, nenhuma coluna nova, e vale
# retroativamente para o que ja esta no banco. E contestar o VEREDITO EXIBIDO
# e mais defensavel que contestar um intermediario que a tela nunca mostra.
LIMIAR_SCORE = 95.0

# Nomeado, e nao uma frase pronta: a frase de tela mora no front, que a monta
# com os numeros daqui. Um motivo nomeado permite um segundo tipo de
# contestacao depois sem quebrar quem le o campo.
MOTIVO = "elogio_contra_espera"


def contestacao(
    score: float | None, latencia_mediana_s: float | None
) -> dict | None:
    """A marca, ou `None` quando nao ha o que contestar.

    Os dois limiares sao ESTRITAMENTE maiores. Fronteira aberta ou fechada nao
    muda nenhum caso real, mas escolher em silencio deixa a proxima pessoa
    adivinhando -- e as fronteiras 6/7 e 8/9 do NPS ja custaram uma divergencia
    de arredondamento neste projeto.

    QUATRO AUSENCIAS, E NENHUMA DELAS CONTESTA:

    - `score is None` -- conversa sem fala do cliente. Ausencia de dado nao e
      insatisfacao (invariante 2) e tambem nao e contestacao: nao ha leitura
      para contestar.
    - `latencia_mediana_s is None` -- conversa sem nenhuma resposta. Nao ha
      contradicao MEDIDA, e inventar uma seria o mesmo pecado com outro nome.
    - score alto e latencia normal -- elogio rapido e o caso saudavel; o
      produto existe para reconhece-lo, nao para desconfiar dele.
    - score baixo e latencia alta -- reclamacao com espera longa, ou seja o
      sistema acertou. Contestar aqui faria a marca virar um detector de
      latencia alta com nome de detector de ironia.

    O dicionario devolvido leva os DOIS lados e os DOIS limiares porque a tela
    escreve a frase a partir deles, sem redigitar a regra em TypeScript
    (invariante 3). Nao leva `nota` nem `categoria`, e nao pode passar a levar:
    seria uma segunda fonte para a regua do NPS.
    """
    if score is None or latencia_mediana_s is None:
        return None
    if score <= LIMIAR_SCORE or latencia_mediana_s <= LIMIAR_LATENCIA_S:
        return None
    return {
        "motivo": MOTIVO,
        "score": score,
        "limiar_score": LIMIAR_SCORE,
        "latencia_mediana_s": latencia_mediana_s,
        "limiar_s": LIMIAR_LATENCIA_S,
    }
