"""Uma passada de cada BERTimbau por pergunta, nao tres ou quatro.

`atribuir_conversa` classificava a fala do cliente e depois `montar_features`
classificava os MESMOS textos de novo; `analisar_conversa` ainda chamava
`pontuar_conversa`, uma terceira vez. O resultado nao muda -- o lote e o mesmo
-- entao repetir era so CPU jogada fora.
"""

import threading
from datetime import datetime, timedelta, timezone

from fraus.fusor import NOMES_FEATURES
from fraus.modelos import Conversa, Mensagem
from fraus.motor import Motor


class ClassificadorContado:
    def __init__(self, classes):
        self.classes = classes
        self.lotes = []

    def prever_mensagens(self, textos):
        self.lotes.append(list(textos))
        return [[1.0 / self.classes] * self.classes for _ in textos]


class FusorFalso:
    def pontuar(self, features):
        return 42.0

    def contribuicoes(self, features):
        return {nome: 0.0 for nome in NOMES_FEATURES}

    def importancias(self):
        return {}


def _conversa():
    t = datetime(2026, 8, 13, 10, tzinfo=timezone.utc)
    return Conversa(id="c", canal="csv", iniciada_em=t, mensagens=[
        Mensagem(autor="cliente", texto="demorou demais", enviada_em=t),
        Mensagem(autor="bot", texto="desculpe", enviada_em=t + timedelta(seconds=5)),
        Mensagem(autor="cliente", texto="ok obrigado", enviada_em=t + timedelta(seconds=40)),
    ])


def _motor():
    texto, emocao, ironia = (ClassificadorContado(3), ClassificadorContado(7),
                             ClassificadorContado(2))
    return Motor(texto, FusorFalso(), emocao, ironia), texto, emocao, ironia


def test_atribuir_roda_cada_cabeca_uma_vez():
    motor, texto, emocao, ironia = _motor()
    motor.atribuir_conversa(_conversa())
    assert len(texto.lotes) == 1
    assert len(emocao.lotes) == 1
    assert len(ironia.lotes) == 1


def test_atribuir_multitarefa_roda_o_encoder_uma_vez():
    class MultitarefaFalsa:
        def __init__(self):
            self.lotes = []

        def prever_cabecas(self, textos):
            self.lotes.append(list(textos))
            return {
                "satisfacao": [[0.2, 0.3, 0.5] for _ in textos],
                "emocao": [[1 / 7] * 7 for _ in textos],
                "ironia": [[0.8, 0.2] for _ in textos],
            }

    class Cabeca:
        def __init__(self, multitarefa, nome):
            self.multitarefa = multitarefa
            self.nome = nome

        def prever_mensagens(self, textos):
            raise AssertionError("o Motor deve usar a passagem multitarefa")

    multitarefa = MultitarefaFalsa()
    motor = Motor(
        Cabeca(multitarefa, "satisfacao"),
        FusorFalso(),
        Cabeca(multitarefa, "emocao"),
        Cabeca(multitarefa, "ironia"),
    )

    resultado = motor.atribuir_conversa(_conversa())

    assert multitarefa.lotes == [["demorou demais", "ok obrigado"]]
    assert resultado["mensagens"][0]["prob_satisfeito"] == 0.5
    assert resultado["mensagens"][0]["prob_ironia"] == 0.2


def test_simulador_multitarefa_roda_o_encoder_uma_vez():
    class MultitarefaFalsa:
        def __init__(self):
            self.chamadas = 0

        def prever_cabecas(self, textos):
            self.chamadas += 1
            return {
                "satisfacao": [[0.2, 0.3, 0.5]],
                "emocao": [[1 / 7] * 7],
                "ironia": [[0.8, 0.2]],
            }

    class Cabeca:
        def __init__(self, multitarefa):
            self.multitarefa = multitarefa

        def prever_mensagens(self, textos):
            raise AssertionError("nao deve executar uma cabeca isolada")

    multitarefa = MultitarefaFalsa()
    cabeca = Cabeca(multitarefa)
    resultado = Motor(cabeca, FusorFalso(), cabeca, cabeca).simular_texto("teste")

    assert multitarefa.chamadas == 1
    assert resultado["prob_satisfeito"] == 0.5
    assert resultado["prob_ironia"] == 0.2


def test_analisar_nao_repontua_a_conversa():
    motor, texto, emocao, _ = _motor()
    resultado = motor.analisar_conversa(_conversa())
    assert resultado["score"] == 42.0
    lotes_da_fala = [l for l in texto.lotes if l == ["demorou demais", "ok obrigado"]]
    assert len(lotes_da_fala) == 1
    assert len(emocao.lotes) == 1


def test_cache_nao_atravessa_chamadas():
    """Duas perguntas sao duas passadas: nada de copia envelhecendo no Motor."""
    motor, texto, _, _ = _motor()
    motor.atribuir_conversa(_conversa())
    motor.atribuir_conversa(_conversa())
    assert len(texto.lotes) == 2


def test_inferencias_simultaneas_respeitam_o_teto(monkeypatch):
    """Threads do FastAPI x threads do torch disputando os nucleos: o Motor
    deixa entrar no modelo no maximo `FRAUS_INFERENCIAS_SIMULTANEAS` por vez."""
    monkeypatch.setenv("FRAUS_INFERENCIAS_SIMULTANEAS", "1")
    ativos, pico, trava = [0], [0], threading.Lock()

    class Lento(ClassificadorContado):
        def prever_mensagens(self, textos):
            with trava:
                ativos[0] += 1
                pico[0] = max(pico[0], ativos[0])
            threading.Event().wait(0.02)
            with trava:
                ativos[0] -= 1
            return super().prever_mensagens(textos)

    motor = Motor(Lento(3), FusorFalso(), Lento(7), Lento(2))
    threads = [threading.Thread(target=motor.atribuir_conversa, args=(_conversa(),))
               for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert pico[0] == 1
