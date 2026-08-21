from datetime import datetime, timezone

from fraus.modelos import Conversa, Mensagem
from fraus.sinais.estilo import (
    carregar_palavroes,
    features_estilo,
    normalizar,
    tem_censura,
)

CHAVES = {
    "estilo_frac_caixa_alta",
    "estilo_pontuacao_enfatica",
    "estilo_frac_alongamento",
    "estilo_palavrao_intensidade",
    "estilo_palavrao_dirigido",
    "estilo_frac_censurado",
}


def _conversa(textos: list[str]) -> Conversa:
    base = datetime(2026, 8, 21, 10, 0, 0, tzinfo=timezone.utc)
    return Conversa(
        id="c1",
        canal="csv",
        iniciada_em=base,
        mensagens=[
            Mensagem(autor="cliente", texto=t, enviada_em=base) for t in textos
        ],
    )


def test_lexicon_tem_as_tres_intensidades():
    lexicon = carregar_palavroes()
    intensidades = {intensidade for intensidade, _ in lexicon.values()}
    assert intensidades == {0.33, 0.66, 1.0}


def test_lexicon_distingue_dirigido_de_desabafo():
    lexicon = carregar_palavroes()
    # "droga" e desabafo: ninguem chama o atendente de droga.
    assert lexicon["droga"] == (0.33, False)
    # "idiota" e dirigido a pessoa por definicao.
    assert lexicon["idiota"][1] is True


def test_lexicon_esta_normalizado_em_minusculas_sem_acento():
    for termo in carregar_palavroes():
        assert termo == termo.lower()
        assert all(ord(c) < 128 for c in termo)


def test_normaliza_homoglifos_para_o_termo_do_lexicon():
    assert normalizar("c@r@lh0") == "caralho"
    assert normalizar("p0rra") == "porra"
    assert normalizar("MERDA") == "merda"
    assert normalizar("babaca") == "babaca"


def test_normalizacao_tira_acento():
    assert normalizar("otario") == "otario"
    assert normalizar("otário") == "otario"


def test_censura_detectada_em_palavra_mista():
    assert tem_censura("p*rra") is True
    assert tem_censura("c@ralho") is True
    assert tem_censura("#@$%") is True


def test_palavra_limpa_nao_e_censura():
    assert tem_censura("caralho") is False
    assert tem_censura("obrigado") is False


def test_pontuacao_sozinha_nao_e_censura():
    # "!!!" e enfase, medida por outra feature -- nao e palavrao mascarado.
    assert tem_censura("!!!") is False
    assert tem_censura("???") is False


def test_devolve_exatamente_as_seis_chaves():
    assert set(features_estilo(_conversa(["ola"]))) == CHAVES


def test_conversa_sem_fala_do_cliente_zera_sem_estourar():
    base = datetime(2026, 8, 21, 10, 0, 0, tzinfo=timezone.utc)
    conversa = Conversa(
        id="c1",
        canal="csv",
        iniciada_em=base,
        mensagens=[Mensagem(autor="bot", texto="POSSO AJUDAR?!!", enviada_em=base)],
    )
    features = features_estilo(conversa)
    assert set(features) == CHAVES
    assert all(valor == 0.0 for valor in features.values())


def test_gritaria_eleva_a_caixa_alta():
    gritou = features_estilo(_conversa(["NAO ACREDITO NISSO"]))
    calmo = features_estilo(_conversa(["nao acredito nisso"]))
    assert gritou["estilo_frac_caixa_alta"] > 0.9
    assert calmo["estilo_frac_caixa_alta"] == 0.0


def test_sigla_nao_conta_como_gritaria():
    features = features_estilo(_conversa(["preciso do CPF e da NF do pedido"]))
    assert features["estilo_frac_caixa_alta"] == 0.0


def test_pontuacao_enfatica_conta_repeticao():
    com = features_estilo(_conversa(["cade minha entrega???"]))
    sem = features_estilo(_conversa(["cade minha entrega?"]))
    assert com["estilo_pontuacao_enfatica"] > sem["estilo_pontuacao_enfatica"]
    assert sem["estilo_pontuacao_enfatica"] == 0.0


def test_alongamento_detectado():
    features = features_estilo(_conversa(["naooooo pfvvvv"]))
    assert features["estilo_frac_alongamento"] > 0.0


def test_riso_nao_conta_como_alongamento():
    # kkkk e marcador positivo de chat BR, nao arrastar de vogal irritado.
    assert features_estilo(_conversa(["kkkkkk"]))["estilo_frac_alongamento"] == 0.0


def test_intensidade_do_palavrao_e_graduada():
    leve = features_estilo(_conversa(["que droga de sistema"]))
    pesado = features_estilo(_conversa(["que caralho de sistema"]))
    assert 0.0 < leve["estilo_palavrao_intensidade"] < pesado["estilo_palavrao_intensidade"]


def test_palavrao_dirigido_separado_de_desabafo():
    pessoa = features_estilo(_conversa(["voce e um idiota"]))
    desabafo = features_estilo(_conversa(["que merda de sistema"]))
    assert pessoa["estilo_palavrao_dirigido"] > 0.0
    assert desabafo["estilo_palavrao_dirigido"] == 0.0


def test_palavrao_censurado_conta_nas_duas_features():
    features = features_estilo(_conversa(["que p*rra e essa"]))
    assert features["estilo_frac_censurado"] > 0.0
    assert features["estilo_palavrao_intensidade"] > 0.0


def test_texto_limpo_zera_tudo():
    features = features_estilo(_conversa(["bom dia, poderia verificar meu pedido?"]))
    assert all(valor == 0.0 for valor in features.values())


def test_asterisco_casa_qualquer_letra():
    # "*" mascara a vogal do meio de "caralho", nao a de "porra" -- um chute
    # fixo de letra acertaria um caso e erraria este calado.
    features = features_estilo(_conversa(["que c*ralho e isso"]))
    assert features["estilo_palavrao_intensidade"] > 0.0


def test_censura_nao_casa_termo_de_tamanho_diferente():
    features = features_estilo(_conversa(["a*"]))
    assert features["estilo_palavrao_intensidade"] == 0.0
