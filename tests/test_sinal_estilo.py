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
    # "p*rr" vira o padrao "p.rr" (4 chars); sem a ancora de fim `$` isso
    # casaria "porra" (5 chars) via `.match`, entao este caso exercita a
    # ancoragem de verdade -- "a*" nao provava nada, so faltava termo de
    # 2 chars no lexicon.
    features = features_estilo(_conversa(["p*rr"]))
    assert features["estilo_palavrao_intensidade"] == 0.0


def test_codigo_de_pedido_nao_conta_censura():
    for texto in ["pedido2024", "protocolo1", "joao@gmail"]:
        features = features_estilo(_conversa([texto]))
        assert features["estilo_frac_censurado"] == 0.0, texto


def test_palavrao_censurado_ainda_conta_censura_e_intensidade():
    features = features_estilo(_conversa(["que p*rra e essa"]))
    assert features["estilo_frac_censurado"] > 0.0
    assert features["estilo_palavrao_intensidade"] > 0.0


def test_simbolo_puro_conta_censura_sozinho():
    features = features_estilo(_conversa(["#@$%"]))
    assert features["estilo_frac_censurado"] > 0.0


def test_token_so_de_digito_nunca_e_censura():
    # Numero de pedido, preco, data e protocolo sao os tokens mais comuns de um
    # chat de atendimento. Enquanto os digitos moravam em `SIMBOLOS_CENSURA`,
    # "400" entrava pelo ramo do simbolo puro e o curinga o resolvia como
    # palavrao pesado. O simulador nao emite digito nenhum: a feature ficava
    # limpa no treino e suja em producao.
    for token in ["2024", "400", "1043", "10", "0", "100%", "01", "13", "5", "50%"]:
        assert tem_censura(token) is False, token


def test_frase_educada_com_numeros_zera_o_palavrao():
    features = features_estilo(
        _conversa(["oi, meu pedido 1043 chegou dia 10 e custou R$ 400, obrigado"])
    )
    assert features["estilo_palavrao_intensidade"] == 0.0
    assert features["estilo_frac_censurado"] == 0.0


def test_homoglifo_de_digito_ainda_resolve_o_palavrao():
    # Tirar digito de `SIMBOLOS_CENSURA` nao pode apagar `p0rra` -> `porra`
    # nem `c@r@lh0` -> `caralho`, que e o caso misto de simbolo com digito.
    assert features_estilo(_conversa(["p0rra"]))["estilo_palavrao_intensidade"] > 0.0
    assert features_estilo(_conversa(["c@r@lh0"]))["estilo_palavrao_intensidade"] > 0.0


def test_saquei_nao_e_palavrao():
    # "saquei" e "entendi" -- token de cliente SATISFEITO, nao xingamento.
    assert features_estilo(_conversa(["saquei, valeu!"]))["estilo_palavrao_intensidade"] == 0.0


def test_interjeicao_neutra_nao_e_palavrao():
    for texto in ["caramba, que rapido", "eita, chegou", "credo", "oxente"]:
        features = features_estilo(_conversa([texto]))
        assert features["estilo_palavrao_intensidade"] == 0.0, texto


def test_lexicon_nao_tem_termo_multipalavra_nem_hifen():
    # A tokenizacao e por palavra (`PALAVRA` nao inclui espaco nem hifen):
    # termo com separador e linha morta que nunca casa.
    for termo in carregar_palavroes():
        assert " " not in termo, termo
        assert "-" not in termo, termo


def test_estilo_da_mensagem_le_uma_fala_por_vez():
    from fraus.sinais.estilo import estilo_da_mensagem

    # "ABSURDO" nao serve de exemplo aqui: esta no lexicon de palavrao (leve),
    # o que faria este teste de gritaria/alongamento tropecar sem querer no
    # teste de palavrao. Ver test_estilo_da_mensagem_marca_palavrao_com_intensidade.
    leitura = estilo_da_mensagem("ISSO E TERRIVEL!!! naaaao acredito")
    assert leitura["caixa_alta"] is True
    assert leitura["alongamento"] is True
    assert leitura["pontuacao_enfatica"] == 1
    assert leitura["palavrao"] is None
    assert leitura["censura"] is False


def test_estilo_da_mensagem_sem_marca_nenhuma():
    from fraus.sinais.estilo import estilo_da_mensagem

    leitura = estilo_da_mensagem("bom dia, preciso de ajuda com o pedido")
    assert leitura["caixa_alta"] is False
    assert leitura["alongamento"] is False
    assert leitura["pontuacao_enfatica"] == 0
    assert leitura["palavrao"] is None
    assert leitura["palavrao_dirigido"] is False
    assert leitura["censura"] is False


def test_estilo_da_mensagem_marca_palavrao_com_intensidade():
    from fraus.sinais.estilo import estilo_da_mensagem

    leitura = estilo_da_mensagem("que droga de sistema")
    assert leitura["palavrao"] == 0.33
    assert leitura["palavrao_dirigido"] is False


def test_estilo_da_mensagem_marca_censura():
    from fraus.sinais.estilo import estilo_da_mensagem

    leitura = estilo_da_mensagem("que p*rra e essa")
    assert leitura["censura"] is True


def test_sigla_nao_conta_como_grito_na_leitura_por_mensagem():
    from fraus.sinais.estilo import estilo_da_mensagem

    assert estilo_da_mensagem("preciso do CPF")["caixa_alta"] is False
