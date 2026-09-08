"""Quando o tempo contesta o elogio, e por que a nota continua de pe.

O CASO. A frase canonica do projeto -- "que atendimento maravilhoso, so esperei
3 horas" -- pontua 99,93 / nota 10 / promotor. `incongruencia_situacao_negativa`
entrou no vetor em 04/09/2026 para alcanca-la, dispara nela e perde: pesa
-0,193 contra os +2,78 de `texto_prob_satisfeito_media`. Nenhuma feature
agregada de conversa reverte uma probabilidade saturada por mensagem.

O QUE ESTE MODULO FAZ, E O QUE ELE NAO FAZ. Ele marca; nao corrige. O score
continua 99,93, a nota continua 10, a categoria continua promotor e o
atendimento CONTINUA CONTANDO NO NPS. Tirar do agregado seria mais honesto no
caso isolado e mais perigoso no conjunto -- limiar mal calibrado esvazia o
indicador em silencio. Rebaixar para neutro inventaria um veredito que o modelo
nao produziu, que e o numero simulado que o CLAUDE.md proibe.

A REGRA E DECLARADA, NAO APRENDIDA, e isso e decisao e nao preguica: o corpus
de treino nao tem um unico exemplo de elogio-com-espera rotulado insatisfeito
(a latencia sai de distribuicao por rotulo, entao satisfeito-e-lento e rotulado
satisfeito), logo uma feature 40 nasceria com peso POSITIVO -- o mesmo modo de
falha que tirou `ironia_prob_*` do vetor. Ver a spec de 08/09/2026.

Desenho completo em
`docs/superpowers/specs/2026-09-08-abstencao-por-contestacao-design.md`.
"""

from fraus.contestacao import (LIMIAR_LATENCIA_S, LIMIAR_SCORE, MOTIVO,
                               contestacao)

# A frase canonica, com os numeros que ela de fato produz.
SCORE_CANONICO = 99.93
ESPERA_DE_TRES_HORAS = 10800.0


# ---- a regra ------------------------------------------------------------


def test_elogio_saturado_contra_espera_longa_e_contestado():
    """O caso em si. Este e o teste que impede a regressao."""
    assert contestacao(SCORE_CANONICO, ESPERA_DE_TRES_HORAS) is not None


def test_a_contestacao_carrega_o_motivo_e_os_dois_lados():
    """A tela precisa escrever "elogio saturado contra espera de 3h12" sem
    redigitar a regra em TypeScript -- duplicar regra derivada no cliente ja
    causou divergencia de arredondamento neste projeto (invariante 3). Entao a
    API manda os quatro numeros que a frase usa, nao um booleano."""
    marca = contestacao(SCORE_CANONICO, ESPERA_DE_TRES_HORAS)

    assert marca["motivo"] == MOTIVO
    assert marca["score"] == SCORE_CANONICO
    assert marca["latencia_mediana_s"] == ESPERA_DE_TRES_HORAS
    # Os limiares vao junto: sem eles a tela nao consegue dizer POR QUE aquilo
    # e alto sem ter uma copia dos numeros.
    assert marca["limiar_score"] == LIMIAR_SCORE
    assert marca["limiar_s"] == LIMIAR_LATENCIA_S


# ---- os quatro casos que NAO contestam ----------------------------------


def test_sem_score_nao_contesta():
    """Conversa sem fala do cliente tem `score: None`. Ausencia de dado nao e
    insatisfacao (invariante 2) e tambem nao e contestacao -- nao ha leitura
    para contestar."""
    assert contestacao(None, ESPERA_DE_TRES_HORAS) is None


def test_sem_latencia_nao_contesta():
    """Conversa sem nenhuma resposta nao tem latencia mediana. Nao ha
    contradicao MEDIDA, e inventar uma seria o mesmo pecado com outro nome."""
    assert contestacao(SCORE_CANONICO, None) is None


def test_elogio_rapido_nao_e_contestado():
    """Score alto com atendimento rapido e o caso saudavel -- o produto existe
    para reconhece-lo, nao para desconfiar dele."""
    assert contestacao(SCORE_CANONICO, 12.0) is None


def test_reclamacao_com_espera_longa_nao_e_contestada():
    """O sistema ACERTOU aqui: texto negativo, espera longa, score baixo.
    Contestar seria contestar o acerto -- e transformaria a marca num detector
    de latencia alta com nome de detector de ironia, que e exatamente o modo de
    falha que tirou `ironia_prob_*` do vetor."""
    assert contestacao(3.5, ESPERA_DE_TRES_HORAS) is None


# ---- as fronteiras ------------------------------------------------------


def test_exatamente_no_limiar_nao_contesta():
    """Os dois lados sao ESTRITAMENTE maiores. Fronteira aberta ou fechada nao
    muda nenhum caso real, mas escolher em silencio deixa a proxima pessoa
    adivinhando -- e as fronteiras 6/7 e 8/9 do NPS ja custaram uma divergencia
    de arredondamento neste projeto."""
    assert contestacao(LIMIAR_SCORE, ESPERA_DE_TRES_HORAS) is None
    assert contestacao(SCORE_CANONICO, LIMIAR_LATENCIA_S) is None


def test_um_fio_acima_dos_dois_limiares_contesta():
    assert contestacao(LIMIAR_SCORE + 0.01, LIMIAR_LATENCIA_S + 0.01) is not None


def test_um_lado_so_nunca_basta():
    """A marca e o CONTRASTE entre as duas leituras. Qualquer um dos lados
    sozinho e um fato comum de atendimento, nao uma contradicao."""
    assert contestacao(SCORE_CANONICO, LIMIAR_LATENCIA_S - 1) is None
    assert contestacao(LIMIAR_SCORE - 1, ESPERA_DE_TRES_HORAS) is None


# ---- o que a marca NAO pode fazer ---------------------------------------


def test_a_marca_nao_carrega_nota_nem_categoria():
    """Ela MARCA, nao corrige. No dia em que este dicionario ganhar uma
    `categoria` ou uma `nota`, alguem vai lê-la em vez da derivada de verdade,
    e a regua do NPS passa a ter duas fontes -- que e a invariante 4 quebrada
    pela porta dos fundos."""
    marca = contestacao(SCORE_CANONICO, ESPERA_DE_TRES_HORAS)
    assert "categoria" not in marca
    assert "nota" not in marca
