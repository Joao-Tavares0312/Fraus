import pytest

from fraus.fusor import NOMES_FEATURES, Fusor, FusorIncompativelError, vetorizar


def _features(**sobrescritas) -> dict[str, float]:
    base = {nome: 0.0 for nome in NOMES_FEATURES}
    base.update(sobrescritas)
    return base


def _fusor_treinado() -> Fusor:
    exemplos, rotulos = [], []
    for _ in range(40):
        exemplos.append(_features(
            texto_prob_satisfeito_media=0.9,
            texto_prob_satisfeito_ultima=0.9,
            emoji_score_medio=0.8,
            latencia_mediana_s=8.0,
        ))
        rotulos.append(2)
        exemplos.append(_features(
            texto_prob_insatisfeito_media=0.9,
            texto_prob_insatisfeito_max=0.95,
            emoji_score_medio=-0.7,
            latencia_mediana_s=300.0,
            escalou=1.0,
        ))
        rotulos.append(0)
    fusor = Fusor()
    fusor.treinar(exemplos, rotulos)
    return fusor


def test_vetorizar_respeita_a_ordem_canonica():
    vetor = vetorizar(_features(emoji_contagem=3.0))
    assert len(vetor) == len(NOMES_FEATURES)
    assert vetor[NOMES_FEATURES.index("emoji_contagem")] == 3.0


def test_feature_faltando_e_erro_e_nao_zero_silencioso():
    incompleto = _features()
    del incompleto["emoji_contagem"]
    with pytest.raises(KeyError):
        vetorizar(incompleto)


def test_vetorizar_recusa_chave_extra():
    """Espelha o lado 'faltando' (invariante 9): sobrando tambem e erro.

    Uma feature que saiu do contrato mas continua sendo produzida por engano
    (caso real: `ironia_prob_media`/`ironia_prob_max` em 04/09/2026) precisa
    aparecer na hora, nao passar batido dentro de um vetor do tamanho certo.
    """
    excedente = _features()
    excedente["ironia_prob_media"] = 0.5
    with pytest.raises(ValueError, match="ironia_prob_media"):
        vetorizar(excedente)


def test_carregar_aceita_artefato_compativel(tmp_path):
    fusor = _fusor_treinado()
    caminho = tmp_path / "fusor.joblib"
    fusor.salvar(caminho)
    assert Fusor.carregar(caminho) is not None


def test_carregar_recusa_artefato_incompativel(tmp_path):
    """Reproduz o incidente real: artefato de 40, contrato de 38.

    `Fusor.carregar` fazia `joblib.load` puro e a API subia normalmente com
    um `StandardScaler` de dimensao errada -- so estourava na primeira
    pontuacao real (`/ingestao`, `/conversas/importar`), como HTTP 500. Isso
    enganou quem testava a mao via `/modelo/simular` (que nao passa pelo
    fusor) duas vezes na mesma semana. A validacao precisa acontecer na
    CARGA, nao na primeira predicao (invariante 7).
    """
    nomes_diferentes = NOMES_FEATURES[:-2]  # dois a menos que o contrato
    exemplos = [{nome: 0.0 for nome in nomes_diferentes} for _ in range(4)]
    rotulos = [0, 1, 2, 1]
    fusor_velho = Fusor()
    fusor_velho._pipeline.fit(
        [[float(f[nome]) for nome in nomes_diferentes] for f in exemplos], rotulos
    )

    caminho = tmp_path / "fusor_velho.joblib"
    import joblib
    joblib.dump(fusor_velho._pipeline, caminho)

    faltando = len(NOMES_FEATURES) - 2
    esperado = rf"{faltando}.*{len(NOMES_FEATURES)}|{len(NOMES_FEATURES)}.*{faltando}"
    with pytest.raises(FusorIncompativelError, match=esperado):
        Fusor.carregar(caminho)


def test_conversa_positiva_pontua_alto():
    fusor = _fusor_treinado()
    score = fusor.pontuar(_features(
        texto_prob_satisfeito_media=0.9,
        texto_prob_satisfeito_ultima=0.9,
        emoji_score_medio=0.8,
        latencia_mediana_s=8.0,
    ))
    assert score > 70


def test_conversa_negativa_pontua_baixo():
    fusor = _fusor_treinado()
    score = fusor.pontuar(_features(
        texto_prob_insatisfeito_media=0.9,
        texto_prob_insatisfeito_max=0.95,
        emoji_score_medio=-0.7,
        latencia_mediana_s=300.0,
        escalou=1.0,
    ))
    assert score < 30


def test_score_fica_sempre_entre_zero_e_cem():
    fusor = _fusor_treinado()
    for valor in (-5.0, 0.0, 9999.0):
        score = fusor.pontuar(_features(latencia_mediana_s=valor))
        assert 0.0 <= score <= 100.0


def test_salvar_e_carregar_preserva_o_score(tmp_path):
    fusor = _fusor_treinado()
    entrada = _features(texto_prob_satisfeito_media=0.9, emoji_score_medio=0.8)
    esperado = fusor.pontuar(entrada)

    caminho = tmp_path / "fusor.joblib"
    fusor.salvar(caminho)
    assert Fusor.carregar(caminho).pontuar(entrada) == pytest.approx(esperado)


def test_importancias_cobrem_todas_as_features():
    assert set(_fusor_treinado().importancias()) == set(NOMES_FEATURES)


def test_contribuicoes_cobrem_todas_as_features():
    fusor = _fusor_treinado()
    contribuicoes = fusor.contribuicoes(_features(emoji_score_medio=0.8))
    assert set(contribuicoes) == set(NOMES_FEATURES)


def test_contribuicoes_conversa_positiva_soma_maior_que_negativa():
    fusor = _fusor_treinado()
    positiva = fusor.contribuicoes(_features(
        texto_prob_satisfeito_media=0.9,
        texto_prob_satisfeito_ultima=0.9,
        emoji_score_medio=0.8,
        latencia_mediana_s=8.0,
    ))
    negativa = fusor.contribuicoes(_features(
        texto_prob_insatisfeito_media=0.9,
        texto_prob_insatisfeito_max=0.95,
        emoji_score_medio=-0.7,
        latencia_mediana_s=300.0,
        escalou=1.0,
    ))
    assert sum(positiva.values()) > sum(negativa.values())


def test_contribuicoes_tem_sinal_interpretavel():
    fusor = _fusor_treinado()
    contribuicoes = fusor.contribuicoes(_features(
        texto_prob_satisfeito_media=0.9,
        texto_prob_satisfeito_ultima=0.9,
        emoji_score_medio=0.8,
        latencia_mediana_s=8.0,
    ))
    assert contribuicoes["texto_prob_satisfeito_media"] > 0


def test_prever_devolve_uma_das_tres_classes():
    fusor = _fusor_treinado()
    assert fusor.prever(_features(texto_prob_satisfeito_media=0.9)) in (0, 1, 2)


def test_contrato_tem_trinta_e_nove_features_com_incongruencia():
    from fraus.sinais.incongruencia import CHAVES

    assert len(NOMES_FEATURES) == 39
    assert len(set(NOMES_FEATURES)) == 39, "nome de feature duplicado"
    for chave in CHAVES:
        assert chave in NOMES_FEATURES


def test_contrato_nao_tem_duplicata():
    assert len(set(NOMES_FEATURES)) == len(NOMES_FEATURES)


def test_contrato_nao_leva_mais_ironia_no_vetor():
    """Trava a decisao de 04/09/2026 -- nao reverter sem reler a medicao.

    Medido sobre o proprio corpus de treino (B2W-Reviews01, 500 resenhas por
    rotulo, semente 20260904): resenha negativa tem media P(ironia) = 0,1012
    (frac(P>0,5) = 0,092); resenha positiva tem media P(ironia) = 0,7146
    (frac(P>0,5) = 0,740). A cabeca de ironia (IDPT 2021, tweet e noticia)
    funciona nesse corpus como detector de sentimento POSITIVO, nao de
    ironia -- o fusor de 40 features aprendeu +0,77 de peso para
    `ironia_prob_media` no eixo satisfeito-menos-insatisfeito (mais ironia
    empurrando para SATISFEITO). Se esta assercao falhar porque alguem
    recolocou `ironia_prob_media`/`ironia_prob_max` em `NOMES_FEATURES`, reveja
    a medicao (`docs/treinamento.md`) antes de ajustar o teste.
    """
    assert "ironia_prob_media" not in NOMES_FEATURES
    assert "ironia_prob_max" not in NOMES_FEATURES


def test_contrato_cobre_todos_os_prefixos_esperados():
    """Onze prefixos, sete familias no vetor: tempo sozinho usa cinco deles.

    A ironia nao aparece aqui -- ela saiu do vetor em 04/09/2026 (ver o
    comentario de `NOMES_FEATURES` em `fraus/fusor.py`), mas continua existindo
    como oitavo sinal do sistema, so que fora do vetor.
    """
    prefixos = {nome.split("_")[0] for nome in NOMES_FEATURES}
    assert prefixos == {
        "texto", "emoji", "latencia", "duracao", "qtd", "escalou",
        "abandonou", "emocao", "lexico", "estilo", "incongruencia",
    }


def test_vetorizar_estoura_em_feature_de_estilo_faltando():
    completas = {nome: 0.0 for nome in NOMES_FEATURES}
    del completas["estilo_frac_caixa_alta"]
    with pytest.raises(KeyError):
        vetorizar(completas)


def test_vetorizar_estoura_em_feature_de_emocao_faltando():
    completas = {nome: 0.0 for nome in NOMES_FEATURES}
    del completas["emocao_raiva_media"]
    with pytest.raises(KeyError):
        vetorizar(completas)


def test_eixo_global_vazio_sem_treino():
    """Fusor nao treinado nao tem eixo -- e dict vazio, nao um zero por feature.

    Zero e um peso valido ("esta feature nao importa"); ausencia de treino e
    outra coisa. O grafo usa essa diferenca para OMITIR as arestas de feature
    em vez de desenhar `len(NOMES_FEATURES)` fios de peso zero.
    """
    assert Fusor().eixo_global() == {}


def test_eixo_global_tem_sinal():
    """Positivo empurra para satisfeito, negativo para insatisfeito.

    `importancias()` nao serve para o grafo porque e valor ABSOLUTO: ela diz
    que `escalou` pesa, nao para que lado.
    """
    eixo = _fusor_treinado().eixo_global()

    assert set(eixo) == set(NOMES_FEATURES)
    # No conjunto de treino, `escalou` so aparece nos exemplos insatisfeitos
    # e `texto_prob_satisfeito_media` so nos satisfeitos.
    assert eixo["escalou"] < 0
    assert eixo["texto_prob_satisfeito_media"] > 0


def test_contribuicoes_seguem_iguais_depois_da_extracao():
    """Trava o refactor: extrair `_diferenca` nao pode mudar a atribuicao."""
    fusor = _fusor_treinado()
    contribuicoes = fusor.contribuicoes(_features(escalou=1.0))

    assert set(contribuicoes) == set(NOMES_FEATURES)
    assert contribuicoes["escalou"] != 0.0


# --- A CURADORIA CHEGA AO SCORE --------------------------------------------

from datetime import datetime, timezone  # noqa: E402

from fraus.fusor import montar_features  # noqa: E402
from fraus.modelos import Conversa, Mensagem  # noqa: E402
from fraus.sinais.curadoria import Curadoria  # noqa: E402
from fraus.sinais.emocao import NOMES_EMOCOES  # noqa: E402


class _TextoDuble:
    """Tres probabilidades por mensagem, na ordem 0/1/2 da invariante 8."""

    def prever_mensagens(self, textos):
        return [[0.2, 0.3, 0.5] for _ in textos]


class _EmocaoDuble:
    def prever_mensagens(self, textos):
        uniforme = 1.0 / len(NOMES_EMOCOES)
        return [[uniforme] * len(NOMES_EMOCOES) for _ in textos]


def _conversa_com(texto: str) -> Conversa:
    base = datetime(2026, 8, 25, 10, 0, 0, tzinfo=timezone.utc)
    return Conversa(
        id="c1",
        canal="csv",
        iniciada_em=base,
        mensagens=[Mensagem(autor="cliente", texto=texto, enviada_em=base)],
    )


def test_curadoria_atravessa_montar_features():
    """O elo que faltava: sem passar aqui, curar palavra nao moveria o score.

    As 39 chaves continuam as mesmas (invariante 9) -- o que muda e o VALOR de
    `lexico_polaridade_media`, nunca o conjunto de features.
    """
    conversa = _conversa_com("o app ta lentissimo")
    curadoria = Curadoria(palavras={"lentissimo": -1})

    sem = montar_features(conversa, _TextoDuble(), _EmocaoDuble())
    com = montar_features(conversa, _TextoDuble(), _EmocaoDuble(), curadoria)

    assert set(sem) == set(com) == set(NOMES_FEATURES)
    assert sem["lexico_polaridade_media"] == 0.0
    assert com["lexico_polaridade_media"] == -1.0
    assert com["lexico_cobertura"] > sem["lexico_cobertura"]


def test_curadoria_de_emoji_atravessa_montar_features():
    conversa = _conversa_com("acabou assim \N{MELTING FACE}")
    curadoria = Curadoria(emojis={"\N{MELTING FACE}": -0.8})

    sem = montar_features(conversa, _TextoDuble(), _EmocaoDuble())
    com = montar_features(conversa, _TextoDuble(), _EmocaoDuble(), curadoria)

    assert sem["emoji_score_medio"] == 0.0
    assert com["emoji_score_medio"] == -0.8


def test_montar_features_entrega_o_contrato_completo():
    conversa = _conversa_com("o atendimento foi otimo")
    features = montar_features(conversa, _TextoDuble(), _EmocaoDuble())
    assert set(features) == set(NOMES_FEATURES)


def test_sem_curadoria_o_vetor_e_o_de_antes():
    conversa = _conversa_com("o atendimento foi otimo")
    assert montar_features(
        conversa, _TextoDuble(), _EmocaoDuble()
    ) == montar_features(conversa, _TextoDuble(), _EmocaoDuble(), None)
