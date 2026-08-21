import random
import statistics

import pytest

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


@pytest.fixture(scope="module")
def agrupado_por_rotulo() -> dict[int, list[dict]]:
    """Lote de 180 conversas (60 por rotulo), semente fixa -- deterministico.

    `scope="module"` porque os quatro testes de estilo abaixo consultam
    exatamente o mesmo lote; regenera-lo em cada teste era trabalho repetido
    com resultado identico por construcao.
    """
    agrupado: dict[int, list[dict]] = {0: [], 1: [], 2: []}
    for conversa, rotulo in gerar_lote(FRASES_POR_ROTULO, 180, semente=7):
        agrupado[rotulo].append(features_estilo(conversa))
    return agrupado


def test_estilo_varia_dentro_de_cada_rotulo(agrupado_por_rotulo):
    """Feature constante no treino nasce com peso zero -- e o bug do emoji na v1.

    Este teste e quebradico por construcao: `estilo_frac_censurado` no rotulo 1,
    por exemplo, so varia por causa de UMA entrada de `ESTILO_POR_ROTULO`.
    Reordenar ou editar as listas pode fazer alguma combinacao rotulo/feature
    voltar a ficar constante para a semente 7. Se isso acontecer, a CURA e
    acrescentar entrada a `ESTILO_POR_ROTULO` ate a feature variar de novo --
    NUNCA afrouxar esta asercao, porque afrouxar reintroduz em silencio o
    mesmo bug de peso zero que ela existe para pegar.
    """
    for rotulo, linhas in agrupado_por_rotulo.items():
        for chave in CHAVES_ESTILO:
            valores = [linha[chave] for linha in linhas]
            assert statistics.pstdev(valores) > 0.0, f"{chave} constante no rotulo {rotulo}"


def test_palavrao_aparece_nas_tres_classes(agrupado_por_rotulo):
    """Palavrao so em detrator seria a latencia disjunta com outra roupa."""
    for rotulo, linhas in agrupado_por_rotulo.items():
        com_palavrao = [linha for linha in linhas if linha["estilo_palavrao_intensidade"] > 0]
        assert com_palavrao, f"nenhum palavrao no rotulo {rotulo}"


def test_gritaria_aparece_nas_tres_classes(agrupado_por_rotulo):
    for rotulo, linhas in agrupado_por_rotulo.items():
        assert any(linha["estilo_frac_caixa_alta"] > 0 for linha in linhas), rotulo


def test_distribuicoes_de_estilo_se_sobrepoem_entre_rotulos(agrupado_por_rotulo):
    """As caudas se cruzam: existe satisfeito que grita e detrator que e educado.

    Segue a forma de `test_faixas_de_latencia_se_sobrepoem_entre_os_rotulos`:
    sobreposicao BILATERAL (satisfeito alto E insatisfeito baixo), com
    contagem minima de cada lado -- nao "existe pelo menos um", que passaria
    ate com as classes completamente separadas (bastava um unico satisfeito
    com `caralho`, intensidade 1.0, contra a mediana de qualquer coisa <= 1.0).

    A diferenca em relacao ao teste de latencia: latencia e continua e a
    mediana de cada classe cai no meio da distribuicao. As duas features de
    estilo aqui sao ZERO-INFLADAS -- a maioria das conversas nao grita nem
    xinga, entao a MEDIANA de QUALQUER rotulo e 0.0, e "abaixo da mediana"
    ficaria vazio por construcao (o piso da feature ja e 0). Por isso o corte
    usado e o QUARTIL SUPERIOR (Q3, 75o percentil) de cada classe, nao a
    mediana: joga a barra no "quarto mais intenso" de cada distribuicao, que
    e onde a sobreposicao de verdade importa.
    """
    for chave in ("estilo_palavrao_intensidade", "estilo_frac_caixa_alta"):
        satisfeitos = sorted(linha[chave] for linha in agrupado_por_rotulo[2])
        insatisfeitos = sorted(linha[chave] for linha in agrupado_por_rotulo[0])
        q3_satisfeitos = statistics.quantiles(satisfeitos, n=4)[2]
        q3_insatisfeitos = statistics.quantiles(insatisfeitos, n=4)[2]

        intensos_entre_satisfeitos = [v for v in satisfeitos if v > q3_insatisfeitos]
        comedidos_entre_insatisfeitos = [v for v in insatisfeitos if v < q3_satisfeitos]

        # Limiares calibrados no lote de 180 (semente 7): a contagem real
        # observada e 9/43 para palavrao e 10/38 para caixa alta -- as margens
        # abaixo sao conservadoras, nao o valor exato medido.
        assert len(intensos_entre_satisfeitos) >= 5, (
            f"{chave}: poucos satisfeitos no quartil superior do insatisfeito"
        )
        assert len(comedidos_entre_insatisfeitos) >= 15, (
            f"{chave}: poucos insatisfeitos abaixo do quartil superior do satisfeito"
        )
