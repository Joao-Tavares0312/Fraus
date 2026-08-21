from fraus.sinais.estilo import carregar_palavroes, normalizar, tem_censura


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
