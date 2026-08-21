import random
import statistics

from fraus.ingest.simulador import FRASES_POR_ROTULO, gerar_conversa, gerar_lote
from fraus.sinais.emoji import features_emoji
from fraus.sinais.estilo import features_estilo
from fraus.sinais.tempo import features_tempo

FRASES = {
    0: ["que absurdo, ninguem resolve", "pessimo atendimento"],
    1: ["ok", "entendi"],
    2: ["muito obrigado, resolveu", "excelente atendimento"],
}


def test_conversa_gerada_e_valida_e_tem_fala_do_cliente():
    conversa = gerar_conversa(rotulo=2, frases_cliente=FRASES[2], semente=42)
    assert conversa.tem_sinal_cliente
    assert conversa.mensagens[0].autor == "cliente"


def test_mesma_semente_gera_a_mesma_conversa():
    a = gerar_conversa(rotulo=1, frases_cliente=FRASES[1], semente=7)
    b = gerar_conversa(rotulo=1, frases_cliente=FRASES[1], semente=7)
    assert a.model_dump() == b.model_dump()


def test_sementes_diferentes_geram_conversas_diferentes():
    a = gerar_conversa(rotulo=1, frases_cliente=FRASES[1], semente=1)
    b = gerar_conversa(rotulo=1, frases_cliente=FRASES[1], semente=2)
    assert a.model_dump() != b.model_dump()


def test_insatisfeito_tem_latencia_maior_que_satisfeito():
    satisfeitas = [
        features_tempo(gerar_conversa(2, FRASES[2], semente=s))["latencia_mediana_s"]
        for s in range(40)
    ]
    insatisfeitas = [
        features_tempo(gerar_conversa(0, FRASES[0], semente=s))["latencia_mediana_s"]
        for s in range(40)
    ]
    media_satisfeitas = sum(satisfeitas) / len(satisfeitas)
    media_insatisfeitas = sum(insatisfeitas) / len(insatisfeitas)
    assert media_insatisfeitas > media_satisfeitas * 3


def test_faixas_de_latencia_se_sobrepoem_entre_os_rotulos():
    """Latencia informa, nunca entrega o gabarito.

    Protege a regressao que matou o primeiro fusor: com faixas DISJUNTAS
    (insatisfeito 60-400s, satisfeito 3-15s) a latencia sozinha determinava o
    rotulo, a regressao logistica aprendeu so o relogio e ignorou o texto --
    99,3% de acuracia no sintetico e ~50 para toda conversa real.
    """
    satisfeitas = sorted(
        features_tempo(gerar_conversa(2, FRASES[2], semente=s))["latencia_mediana_s"]
        for s in range(200)
    )
    insatisfeitas = sorted(
        features_tempo(gerar_conversa(0, FRASES[0], semente=s))["latencia_mediana_s"]
        for s in range(200)
    )
    mediana_satisfeitas = satisfeitas[len(satisfeitas) // 2]
    mediana_insatisfeitas = insatisfeitas[len(insatisfeitas) // 2]

    # Sobreposicao nos dois sentidos: atendimento rapido que terminou mal e
    # atendimento lento que terminou bem existem, e o modelo tem que ver os dois.
    lentas_entre_as_satisfeitas = [v for v in satisfeitas if v > mediana_insatisfeitas]
    rapidas_entre_as_insatisfeitas = [v for v in insatisfeitas if v < mediana_satisfeitas]
    assert len(lentas_entre_as_satisfeitas) >= 10, "nenhuma conversa satisfeita e lenta"
    assert len(rapidas_entre_as_insatisfeitas) >= 10, "nenhuma conversa insatisfeita e rapida"


def test_cliente_usa_emoji_e_a_polaridade_acompanha_o_rotulo_sem_entregar():
    """Sem emoji no corpus sintetico o sinal de emoji nasce com peso zero.

    O primeiro fusor treinado tinha `emoji_score_medio` com coeficiente
    0.0000: a feature era constante no treino, entao o pilar de emoji da
    arquitetura nao contribuia nada. Aqui o emoji aparece, acompanha o rotulo
    na MEDIA e ainda assim cruza -- cliente satisfeito as vezes manda 😅.
    """
    def scores(rotulo):
        return [
            features_emoji(gerar_conversa(rotulo, FRASES[rotulo], semente=s))["emoji_score_medio"]
            for s in range(200)
        ]

    satisfeitas, insatisfeitas = scores(2), scores(0)

    assert any(v != 0.0 for v in satisfeitas), "nenhum emoji nas conversas satisfeitas"
    assert any(v != 0.0 for v in insatisfeitas), "nenhum emoji nas conversas insatisfeitas"

    media_satisfeitas = sum(satisfeitas) / len(satisfeitas)
    media_insatisfeitas = sum(insatisfeitas) / len(insatisfeitas)
    assert media_satisfeitas > media_insatisfeitas

    # Cruzamento: emoji tambem nao pode virar gabarito.
    assert any(v < 0 for v in satisfeitas), "emoji negativo nunca aparece no satisfeito"
    assert any(v > 0 for v in insatisfeitas), "emoji positivo nunca aparece no insatisfeito"


def test_lote_respeita_a_quantidade_e_devolve_rotulos():
    lote = gerar_lote(FRASES, quantidade=30, semente=3)
    assert len(lote) == 30
    assert {rotulo for _, rotulo in lote} == {0, 1, 2}
    assert len({conversa.id for conversa, _ in lote}) == 30


def test_gerar_lote_amostra_sem_reposicao(monkeypatch):
    """Protege a regressao: trocar sample por randrange traz de volta a colisao de id."""
    chamada = {}
    sample_original = random.Random.sample

    def sample_espiao(self, populacao, k):
        chamada["k"] = k
        chamada["tamanho_populacao"] = len(populacao)
        return sample_original(self, populacao, k)

    monkeypatch.setattr(random.Random, "sample", sample_espiao)
    gerar_lote(FRASES, quantidade=10, semente=1)

    assert chamada == {"k": 10, "tamanho_populacao": 10**9}


CHAVES_ESTILO = [
    "estilo_frac_caixa_alta",
    "estilo_pontuacao_enfatica",
    "estilo_frac_alongamento",
    "estilo_palavrao_intensidade",
    "estilo_palavrao_dirigido",
    "estilo_frac_censurado",
]


def _por_rotulo(quantidade: int = 180) -> dict[int, list[dict]]:
    agrupado: dict[int, list[dict]] = {0: [], 1: [], 2: []}
    for conversa, rotulo in gerar_lote(FRASES_POR_ROTULO, quantidade, semente=7):
        agrupado[rotulo].append(features_estilo(conversa))
    return agrupado


def test_estilo_varia_dentro_de_cada_rotulo():
    """Feature constante no treino nasce com peso zero -- e o bug do emoji na v1."""
    agrupado = _por_rotulo()
    for rotulo, linhas in agrupado.items():
        for chave in CHAVES_ESTILO:
            valores = [linha[chave] for linha in linhas]
            assert statistics.pstdev(valores) > 0.0, f"{chave} constante no rotulo {rotulo}"


def test_palavrao_aparece_nas_tres_classes():
    """Palavrao so em detrator seria a latencia disjunta com outra roupa."""
    agrupado = _por_rotulo()
    for rotulo, linhas in agrupado.items():
        com_palavrao = [l for l in linhas if l["estilo_palavrao_intensidade"] > 0]
        assert com_palavrao, f"nenhum palavrao no rotulo {rotulo}"


def test_gritaria_aparece_nas_tres_classes():
    agrupado = _por_rotulo()
    for rotulo, linhas in agrupado.items():
        assert any(l["estilo_frac_caixa_alta"] > 0 for l in linhas), rotulo


def test_distribuicoes_de_estilo_se_sobrepoem_entre_rotulos():
    """As caudas se cruzam: existe satisfeito que grita e detrator que e educado."""
    agrupado = _por_rotulo()
    maximo_satisfeito = max(l["estilo_palavrao_intensidade"] for l in agrupado[2])
    mediana_insatisfeito = statistics.median(
        l["estilo_palavrao_intensidade"] for l in agrupado[0]
    )
    assert maximo_satisfeito >= mediana_insatisfeito
