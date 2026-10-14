"""Deterioracao: onde a estimativa por prefixo virou detratora PARA NAO VOLTAR,
numa conversa encerrada. Retrospectivo; e o teste de nao-vazamento que segura
o "sem ver o futuro"."""

from datetime import datetime, timedelta, timezone

from fraus.deterioracao import (MOTIVO_NAO_TERMINOU, MOTIVO_SEM_SINAL, ROTULO_DETERIORACAO,
                                deterioracao, indice_de_virada)
from fraus.indicadores import FAIXAS_NPS
from fraus.modelos import Conversa, Mensagem
from fraus.motor import Motor
from tests.test_motor import _EmocaoDuble, _IroniaDuble, _fusor_treinado

T0 = datetime(2026, 10, 1, 10, tzinfo=timezone.utc)


class _TextoQueLe:
    """Dubla o texto lendo-o: o `_TextoDuble` de test_motor ignora o texto e o
    teste de nao-vazamento passaria no vazio."""

    def prever_mensagens(self, textos):
        return [[0.9, 0.05, 0.05] if "pessimo" in t else [0.05, 0.05, 0.9] for t in textos]


def _motor():
    return Motor(_TextoQueLe(), _fusor_treinado(), _EmocaoDuble(), _IroniaDuble())


abaixo = lambda s: s < 65


def conv(*falas, encerrada=None):
    return Conversa(id="c", canal="chat", iniciada_em=T0, encerrada_em=encerrada, mensagens=[
        Mensagem(autor=a, texto=t, enviada_em=T0 + timedelta(minutes=k)) for k, (a, t) in enumerate(falas)])


def test_virada_e_a_ultima_descida_definitiva():
    assert indice_de_virada([90, 40, 80, 50, 30], abaixo) == 3


def test_none_nao_quebra_a_sequencia():
    assert indice_de_virada([None, 40, None, 30], abaixo) == 1


def test_termina_acima_nao_tem_virada():
    assert indice_de_virada([40, 30, 80], abaixo) is None


def test_lead_time_em_falas_e_segundos():
    c = conv(("cliente", "a"), ("bot", "b"), ("cliente", "c"), ("bot", "d"), ("cliente", "e"))
    d = deterioracao([90.0, 90.0, 40.0, 40.0, 30.0], c, FAIXAS_NPS)
    assert d["indice_virada"] == 2 and d["falas_ate_o_fim"] == 2
    assert d["segundos_ate_o_fim"] == 120.0 and d["motivo"] is None
    assert d["rotulo"] == ROTULO_DETERIORACAO


def test_encerrada_em_conta_como_fim():
    c = conv(("cliente", "a"), ("bot", "b"), encerrada=T0 + timedelta(minutes=10))
    assert deterioracao([30.0, 30.0], c, FAIXAS_NPS)["segundos_ate_o_fim"] == 600.0


def test_sem_score_e_motivo_e_nao_zero():
    d = deterioracao([None, None], conv(("bot", "a"), ("bot", "b")), FAIXAS_NPS)
    assert d["indice_virada"] is None and d["falas_ate_o_fim"] is None
    assert d["motivo"] == MOTIVO_SEM_SINAL


def test_nao_terminou_detratora():
    d = deterioracao([30.0, 90.0], conv(("cliente", "a"), ("cliente", "b")), FAIXAS_NPS)
    assert d["indice_virada"] is None and d["motivo"] == MOTIVO_NAO_TERMINOU


def test_faixa_vigente_por_parametro():
    # score 70 -> nota 7: neutro na fabrica, detrator numa faixa 0-7.
    faixas = {"detrator": (0, 7), "neutro": (8, 8), "promotor": (9, 10)}
    c = conv(("cliente", "a"))
    assert deterioracao([70.0], c, FAIXAS_NPS)["indice_virada"] is None
    assert deterioracao([70.0], c, faixas)["indice_virada"] == 0


def test_score_do_prefixo_nao_ve_mensagem_futura():
    """Alterar a mensagem j nao muda nenhum score de prefixo k < j."""
    motor = _motor()
    c = conv(("cliente", "otimo atendimento"), ("bot", "posso ajudar"),
             ("cliente", "ainda nao resolveu"), ("bot", "vou verificar"),
             ("cliente", "obrigado"))
    base = motor.scores_do_replay(c)
    mudou_algo = False
    for j in range(1, len(c.mensagens)):
        alterada = c.model_copy(deep=True)
        original = alterada.mensagens[j]
        alterada.mensagens[j] = Mensagem(autor=original.autor,
                                         texto="pessimo horrivel nunca mais volto",
                                         enviada_em=original.enviada_em + timedelta(seconds=30))
        novos = motor.scores_do_replay(alterada)
        assert novos[:j] == base[:j], j
        mudou_algo |= novos[j:] != base[j:]
    assert mudou_algo, "o teste passaria no vazio: nenhuma alteracao mexeu em score algum"
