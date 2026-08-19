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
    assert _no(grafo, "conversa:c1")["grau"] == 3


def test_nenhuma_aresta_orfa():
    """Aresta apontando para no inexistente quebra a simulacao no cliente."""
    registros = [(_conversa("c1"), 30.0), (_conversa("c2", canal="discord"), 95.0)]
    grafo = montar_grafo(registros, FAIXAS_NPS)

    existentes = {no["id"] for no in grafo["nos"]}
    for aresta in grafo["arestas"]:
        assert aresta["de"] in existentes
        assert aresta["para"] in existentes


def test_camada_desligada_nao_emite_nada():
    grafo = montar_grafo([(_conversa(), 30.0)], FAIXAS_NPS, camadas=frozenset({"lexico"}))
    assert not _nos_por_tipo(grafo, "conversa")
    assert grafo["meta"]["camadas"] == ["lexico"]


def test_recorte_vazio_devolve_grafo_vazio_e_nao_erro():
    grafo = montar_grafo([], FAIXAS_NPS)
    assert grafo["nos"] == []
    assert grafo["arestas"] == []
    assert grafo["meta"]["conversas"] == 0
