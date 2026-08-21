from fraus.sinais.estilo import carregar_palavroes


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
