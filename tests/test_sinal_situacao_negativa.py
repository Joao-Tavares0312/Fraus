"""F6 -- elogio convivendo com situacao negativa de atendimento.

A feature que as outras cinco nao alcancavam. As cinco existentes sao todas
funcao de `anotar_texto`/emoji, entao precisam de DOIS termos polares (ou
emoji, ou marcador, ou aspas) para achar contraste. A ironia de atendimento
tipica tem so UM lado lexical: o elogio. O outro lado -- "so esperei 3 horas",
"ficar 5h esperando" -- e negativo por conhecimento de mundo, e nao tem
nenhuma palavra polar em lexicon nenhum.

Os dois casos que motivaram esta feature, os dois medidos como falha real:

    "que atendimento maravilhoso, so esperei 3 horas"     -> score 99,95
    "Nossa, eu realmente gostei de ficar 5h esperando"    -> satisfeito 76,4%

O SEGUNDO e o que derrubou o desenho original. A proposta de 04/09 exigia um
termo POSITIVO do SentiLex como lado do elogio -- e `anotar_texto("...gostei
de ficar 5h esperando...")` devolve `[('gostei', 0, False)]`: polaridade
ZERO. O SentiLex-PT02 e lexico de julgamento social e e neutro em verbo de
afeto do proprio falante (limitacao que `lexico.py` ja declara). Ele sabe que
"maravilhoso" e positivo e nao sabe que "gostei" e. A feature teria acertado a
frase de manual do projeto e errado a primeira frase que um usuario real
digitou -- por isso `VERBOS_AFETO_FALANTE` existe como SEGUNDA fonte do lado
positivo, nao como enfeite.
"""

from datetime import datetime, timedelta, timezone

import pytest

from fraus.modelos import Conversa, Mensagem
from fraus.sinais.incongruencia import CHAVES, features_incongruencia
from fraus.sinais.lexico import anotar_texto

AGORA = datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)


def _conversa(*textos: str) -> Conversa:
    return Conversa(
        id="c",
        canal="teste",
        iniciada_em=AGORA,
        mensagens=[
            Mensagem(autor="cliente", texto=t, enviada_em=AGORA + timedelta(seconds=i))
            for i, t in enumerate(textos)
        ],
    )


def _situacao(*textos: str) -> float:
    return features_incongruencia(_conversa(*textos))["incongruencia_situacao_negativa"]


def test_a_chave_entra_no_conjunto_de_chaves_do_modulo():
    assert "incongruencia_situacao_negativa" in CHAVES


def test_gostei_tem_polaridade_zero_no_sentilex():
    """A premissa que quebrou o desenho original -- travada como teste.

    Se um dia o lexicon passar a dar polaridade a "gostei", este teste falha e
    avisa: `VERBOS_AFETO_FALANTE` pode ter virado redundante para este verbo, e
    a decisao de manter ou remover passa a ser consciente em vez de inercia.
    """
    achados = anotar_texto("eu realmente gostei de esperar")
    polaridades = {termo: polaridade for termo, polaridade, _ in achados}
    assert polaridades.get("gostei") == 0


@pytest.mark.parametrize(
    "texto",
    [
        "que atendimento maravilhoso, so esperei 3 horas",
        "Nossa, eu realmente gostei de ficar 5h esperando para ser atendida",
        "otimo, mais uma vez ninguem resolveu",
        "adorei ter que repetir tudo de novo",
        "perfeito, cobraram errado again",
    ],
)
def test_elogio_com_situacao_negativa_dispara(texto):
    assert _situacao(texto) == 1.0


@pytest.mark.parametrize(
    "texto",
    [
        # Reclamacao direta: situacao negativa SEM elogio nenhum. Nao e
        # incongruencia, e a fala mais comum de um cliente insatisfeito -- se
        # isto disparasse, a feature seria um detector de insatisfacao com
        # nome de detector de ironia, exatamente o defeito que tirou a ironia
        # do vetor em 04/09/2026.
        "esperei 3 horas e ninguem resolveu",
        "cobraram errado e ate agora sem resposta",
        # Elogio genuino SEM situacao negativa.
        "resolveu rapido, muito obrigado! adorei o atendimento",
        "atendimento maravilhoso",
        # Fala neutra.
        "bom dia, preciso de ajuda com meu pedido",
        "",
    ],
)
def test_sem_os_dois_lados_nao_dispara(texto):
    assert _situacao(texto) == 0.0


def test_elogio_negado_nao_conta_como_elogio():
    """"nao gostei de esperar" e reclamacao direta, nao ironia.

    Sem escopo de negacao, o verbo de afeto casaria igual e a fala mais
    inequivocamente insatisfeita do corpus viraria a mais ironica.
    """
    assert _situacao("nao gostei de ficar esperando") == 0.0
    assert _situacao("nunca gostei de esperar") == 0.0


def test_situacao_negada_nao_conta_como_situacao():
    """"nao esperei nada" e elogio genuino -- o oposto de situacao negativa."""
    assert _situacao("adorei, nao esperei nada") == 0.0


def test_media_por_conversa_e_nao_maximo():
    """Uma fala ironica em quatro nao vale o mesmo que quatro ironicas.

    Mesmo padrao de agregacao das outras cinco: media sobre as falas do
    cliente. Maximo deixaria uma unica fala dominar a conversa inteira.
    """
    assert _situacao(
        "que atendimento maravilhoso, so esperei 3 horas",
        "bom dia",
        "preciso do meu pedido",
        "obrigado",
    ) == 0.25


def test_so_a_fala_do_cliente_conta():
    conversa = Conversa(
        id="c",
        canal="teste",
        iniciada_em=AGORA,
        mensagens=[
            Mensagem(autor="bot", texto="que atendimento maravilhoso, so esperei 3 horas", enviada_em=AGORA),
            Mensagem(autor="cliente", texto="bom dia", enviada_em=AGORA + timedelta(seconds=1)),
        ],
    )
    assert features_incongruencia(conversa)["incongruencia_situacao_negativa"] == 0.0


def test_conversa_sem_fala_do_cliente_devolve_zero_sem_estourar():
    conversa = Conversa(
        id="c",
        canal="teste",
        iniciada_em=AGORA,
        mensagens=[Mensagem(autor="bot", texto="ola", enviada_em=AGORA)],
    )
    assert features_incongruencia(conversa)["incongruencia_situacao_negativa"] == 0.0
