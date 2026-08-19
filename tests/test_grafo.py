from datetime import datetime, timedelta, timezone

from fraus.grafo import TODAS_AS_CAMADAS, montar_grafo
from fraus.indicadores import FAIXAS_NPS
from fraus.modelos import Conversa, Mensagem

BASE = datetime(2026, 8, 19, 10, 0, 0, tzinfo=timezone.utc)


def _conversa(identificador="c1", canal="whatsapp", falas=(("cliente", "demora demais"),)):
    mensagens = [
        Mensagem(autor=autor, texto=texto, enviada_em=BASE + timedelta(minutes=i))
        for i, (autor, texto) in enumerate(falas)
    ]
    return Conversa(id=identificador, canal=canal, iniciada_em=BASE, mensagens=mensagens)


def _nos_por_tipo(grafo, tipo):
    return [no for no in grafo["nos"] if no["tipo"] == tipo]


def _no(grafo, identificador):
    return next(no for no in grafo["nos"] if no["id"] == identificador)


def test_conversa_vira_no_ligado_a_categoria_canal_e_desfecho():
    grafo = montar_grafo([(_conversa(), 30.0)], FAIXAS_NPS)

    assert _no(grafo, "conversa:c1")["categoria"] == "detrator"
    ligacoes = {
        (aresta["de"], aresta["para"])
        for aresta in grafo["arestas"]
    }
    assert ("conversa:c1", "categoria:detrator") in ligacoes
    assert ("conversa:c1", "canal:whatsapp") in ligacoes
    # Ultima fala e do cliente e ninguem respondeu.
    assert ("conversa:c1", "desfecho:sem_resposta") in ligacoes


def test_sem_sinal_nao_vira_zero_em_lugar_nenhum():
    """A invariante central do projeto, agora em forma de no.

    Conversa sem fala do cliente tem `score: None`. Se ela aparecesse com
    score 0, o grafo diria visualmente que o pior atendimento do conjunto foi
    justamente aquele sobre o qual nao se sabe nada.
    """
    conversa = _conversa(falas=(("bot", "ola, posso ajudar?"),))
    grafo = montar_grafo([(conversa, None)], FAIXAS_NPS)

    no = _no(grafo, "conversa:c1")
    assert no["score"] is None
    assert no["nota"] is None
    assert no["categoria"] is None
    assert no["sem_sinal"] is True
    # Sem categoria nao ha aresta de categoria -- inventar uma seria escolher
    # uma faixa para quem nao tem nota.
    assert not _nos_por_tipo(grafo, "categoria")
    assert grafo["meta"]["sem_sinal"] == 1


def test_grau_conta_as_arestas_do_no():
    grafo = montar_grafo([(_conversa(), 95.0)], FAIXAS_NPS)
    assert _no(grafo, "categoria:promotor")["grau"] == 1
    # 3 arestas de dominio (categoria, canal, desfecho) + 2 de lexico: a fala
    # "demora demais" tem dois termos de conteudo, cada um vira uma aresta
    # "ativou" ligada a esta mesma conversa (Task 3 ligou a camada lexico).
    assert _no(grafo, "conversa:c1")["grau"] == 5


def test_nenhuma_aresta_orfa():
    """Aresta apontando para no inexistente quebra a simulacao no cliente."""
    registros = [(_conversa("c1"), 30.0), (_conversa("c2", canal="discord"), 95.0)]
    grafo = montar_grafo(registros, FAIXAS_NPS)

    existentes = {no["id"] for no in grafo["nos"]}
    for aresta in grafo["arestas"]:
        assert aresta["de"] in existentes
        assert aresta["para"] in existentes


def test_camada_desligada_nao_emite_nada():
    """So a camada dominio desligada -- o no `conversa` continua existindo.

    Com Task 3, `_camada_lexico` tambem cria o no `conversa` (mesmo tipo/chave
    da camada dominio, deduplicado por `_Montagem`): uma aresta precisa das
    duas pontas, e a conversa e a ponte entre as camadas. Por isso o teste
    agora verifica a AUSENCIA dos nos exclusivos de dominio (categoria, canal,
    desfecho), nao a ausencia do no conversa.
    """
    grafo = montar_grafo([(_conversa(), 30.0)], FAIXAS_NPS, camadas=frozenset({"lexico"}))
    assert not _nos_por_tipo(grafo, "categoria")
    assert not _nos_por_tipo(grafo, "canal")
    assert not _nos_por_tipo(grafo, "desfecho")
    assert grafo["meta"]["camadas"] == ["lexico"]


def test_recorte_vazio_devolve_grafo_vazio_e_nao_erro():
    grafo = montar_grafo([], FAIXAS_NPS)
    assert grafo["nos"] == []
    assert grafo["arestas"] == []
    assert grafo["meta"]["conversas"] == 0


def test_termo_do_cliente_vira_no_ligado_a_conversa():
    conversa = _conversa(falas=(("cliente", "demora demais, demora"),))
    grafo = montar_grafo([(conversa, 30.0)], FAIXAS_NPS)

    aresta = next(a for a in grafo["arestas"] if a["para"] == "termo:demora")
    assert aresta["de"] == "conversa:c1"
    assert aresta["tipo"] == "ativou"
    assert aresta["peso"] == 2  # a palavra aparece duas vezes na fala


def test_fala_do_bot_nao_entra_no_lexico():
    """O texto do bot e roteiro, nao vocabulario do cliente.

    Mesma regra do `lexico_por_classe`: contar o roteiro faria o termo mais
    frequente do grafo ser sempre a saudacao automatica.
    """
    conversa = _conversa(falas=(
        ("bot", "protocolo aberto com sucesso"),
        ("cliente", "obrigado"),
    ))
    grafo = montar_grafo([(conversa, 95.0)], FAIXAS_NPS)

    rotulos = {no["rotulo"] for no in _nos_por_tipo(grafo, "termo")}
    assert "protocolo" not in rotulos
    assert "obrigado" in rotulos


def test_emoji_do_cliente_vira_no():
    conversa = _conversa(falas=(("cliente", "que raiva 😡"),))
    grafo = montar_grafo([(conversa, 20.0)], FAIXAS_NPS)
    assert _no(grafo, "emoji:😡")["camada"] == "lexico"


def test_teto_corta_por_frequencia_e_declara_o_corte():
    """Truncar calado afirmaria que aquilo e tudo o que o sistema sabe."""
    fala = " ".join(f"palavra{i}" for i in range(10)) + " campeao campeao campeao"
    grafo = montar_grafo(
        [(_conversa(falas=(("cliente", fala),)), 30.0)],
        FAIXAS_NPS,
        teto_termos=2,
    )

    assert grafo["meta"]["termos_totais"] == 11
    assert grafo["meta"]["termos_exibidos"] == 2
    assert grafo["meta"]["truncado"] is True
    # O corte e por frequencia: o termo repetido sobrevive.
    assert "termo:campeao" in {no["id"] for no in grafo["nos"]}
    assert len(_nos_por_tipo(grafo, "termo")) == 2


def test_sem_truncar_o_meta_diz_que_nao_truncou():
    grafo = montar_grafo([(_conversa(), 30.0)], FAIXAS_NPS)
    assert grafo["meta"]["truncado"] is False
    assert grafo["meta"]["termos_exibidos"] == grafo["meta"]["termos_totais"]


def test_camada_lexico_desligada_nao_emite_termo():
    grafo = montar_grafo([(_conversa(), 30.0)], FAIXAS_NPS, camadas=frozenset({"dominio"}))
    assert not _nos_por_tipo(grafo, "termo")


def test_no_conversa_tem_schema_completo_so_com_lexico_ligado():
    """O no `conversa` e a ponte entre camadas -- schema variavel quebra a ponte.

    Antes do conserto, `_camada_lexico` criava o no `conversa` sem
    score/nota/categoria/sem_sinal quando a camada dominio nao rodava
    primeiro. A invariante "ausencia nao e zero" precisa valer em toda
    combinacao de camadas, nao so na combinacao padrao.
    """
    conversa = _conversa(falas=(("bot", "ola, posso ajudar?"),))
    grafo = montar_grafo([(conversa, None)], FAIXAS_NPS, camadas=frozenset({"lexico"}))

    no = _no(grafo, "conversa:c1")
    assert no["score"] is None
    assert no["nota"] is None
    assert no["categoria"] is None
    assert no["sem_sinal"] is True


def test_emoji_repetido_vira_uma_aresta_agregada():
    """Emoji 3x na fala e UMA aresta de peso 3, nao 3 arestas de peso 1.

    O grau do no e o raio dele na tela: multiplicar arestas por ocorrencia
    infla o desenho sem acrescentar informacao (mesma regra do termo).
    """
    conversa = _conversa(falas=(("cliente", "😡 muito 😡 ruim 😡"),))
    grafo = montar_grafo([(conversa, 20.0)], FAIXAS_NPS)

    arestas_emoji = [a for a in grafo["arestas"] if a["para"] == "emoji:😡"]
    assert len(arestas_emoji) == 1
    assert arestas_emoji[0]["peso"] == 3
