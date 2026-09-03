from datetime import datetime, timezone

from fraus.modelos import Conversa, Mensagem
from fraus.sinais.incongruencia import features_incongruencia

CHAVES = {
    "incongruencia_polaridade",
    "incongruencia_emoji_texto",
    "incongruencia_marcador_contraste",
    "incongruencia_hiperbole",
    "incongruencia_aspas_ironicas",
}


def _conversa(textos: list[str], autor: str = "cliente") -> Conversa:
    base = datetime(2026, 9, 3, 10, 0, 0, tzinfo=timezone.utc)
    return Conversa(
        id="c1",
        canal="csv",
        iniciada_em=base,
        mensagens=[
            Mensagem(autor=autor, texto=t, enviada_em=base) for t in textos
        ],
    )


def test_devolve_exatamente_as_cinco_chaves():
    assert set(features_incongruencia(_conversa(["oi"]))) == CHAVES


def test_conversa_sem_fala_do_cliente_zera_tudo():
    """Ausencia de medida, nao medida zero -- quem distingue e o score None."""
    features = features_incongruencia(_conversa(["posso ajudar?"], autor="bot"))
    assert set(features) == CHAVES
    assert all(valor == 0.0 for valor in features.values())


def test_polaridade_mista_na_mesma_mensagem_marca_incongruencia():
    misto = features_incongruencia(_conversa(["otimo atendimento, pessimo servico"]))
    so_negativo = features_incongruencia(_conversa(["pessimo servico horrivel"]))
    assert misto["incongruencia_polaridade"] > so_negativo["incongruencia_polaridade"]


def test_texto_so_positivo_nao_marca_incongruencia_de_polaridade():
    features = features_incongruencia(_conversa(["otimo atendimento, excelente"]))
    assert features["incongruencia_polaridade"] == 0.0


def test_emoji_positivo_com_texto_negativo_marca_contraste():
    contraste = features_incongruencia(_conversa(["que servico pessimo 😊"]))
    alinhado = features_incongruencia(_conversa(["que servico pessimo 😡"]))
    assert contraste["incongruencia_emoji_texto"] > alinhado["incongruencia_emoji_texto"]


def test_marcador_de_contraste_entre_polaridades_opostas():
    com_marcador = features_incongruencia(
        _conversa(["o atendimento foi otimo, mas o servico foi pessimo"])
    )
    sem_marcador = features_incongruencia(_conversa(["o servico foi pessimo"]))
    assert com_marcador["incongruencia_marcador_contraste"] == 1.0
    assert sem_marcador["incongruencia_marcador_contraste"] == 0.0


def test_hiperbole_exige_intensificador_junto_de_polaridade():
    com = features_incongruencia(_conversa(["atendimento extremamente otimo"]))
    sem = features_incongruencia(_conversa(["atendimento otimo"]))
    assert com["incongruencia_hiperbole"] > sem["incongruencia_hiperbole"]
    assert sem["incongruencia_hiperbole"] == 0.0


def test_aspas_ironicas_com_polaridade_oposta_ao_resto():
    ironico = features_incongruencia(
        _conversa(['que "otimo" atendimento, servico pessimo e horrivel'])
    )
    assert ironico["incongruencia_aspas_ironicas"] == 1.0


def test_aspas_sem_conflito_de_polaridade_nao_marcam():
    features = features_incongruencia(_conversa(['ele disse "bom dia" e ajudou']))
    assert features["incongruencia_aspas_ironicas"] == 0.0


def test_hiperbole_respeita_negacao_do_termo_intensificado():
    """'nao muito otimo' nao e elogio intensificado -- e leitura negada/mitigada.

    Achado do revisor: _hiperbole usava polaridade_do_termo (lookup cru, sem
    negacao) enquanto as outras quatro features usam anotar_texto. Isso fazia
    'nao muito otimo' pontuar identico a 'muito otimo'.
    """
    com_negacao = features_incongruencia(_conversa(["nao muito otimo"]))
    sem_negacao = features_incongruencia(_conversa(["muito otimo"]))
    assert com_negacao["incongruencia_hiperbole"] < sem_negacao["incongruencia_hiperbole"]
    assert sem_negacao["incongruencia_hiperbole"] == 1.0


def test_hiperbole_reconhece_intensificador_pos_fixado():
    """'otimo demais' e o caso de manual citado no docstring do modulo -- so que
    a janela original olhava so para tras e nunca disparava para ele."""
    pos_fixado = features_incongruencia(_conversa(["atendimento otimo demais"]))
    pre_fixado = features_incongruencia(_conversa(["atendimento extremamente otimo"]))
    sem_intensificador = features_incongruencia(_conversa(["atendimento otimo"]))
    assert pos_fixado["incongruencia_hiperbole"] > sem_intensificador["incongruencia_hiperbole"]
    assert pre_fixado["incongruencia_hiperbole"] > sem_intensificador["incongruencia_hiperbole"]


def test_marcador_de_contraste_com_virgula_apos_o_marcador():
    """'mas,' com pausa digitada nao pode escapar da deteccao de contraste."""
    features = features_incongruencia(
        _conversa(["o atendimento foi otimo, mas, o servico foi pessimo"])
    )
    assert features["incongruencia_marcador_contraste"] == 1.0
