"""Conversa em que o cliente so disse "ok, obrigado" nao tem sinal de satisfacao.

A mesma formula fecha atendimento bom e ruim. Medido em 15/09/2026
(`docs/cartao-do-modelo.md`): "valeu" sozinho saia score 93,2, PROMOTOR, e
"ok, obrigado" neutro -- o texto de gratidao lido como satisfacao, e a emocao
lendo "ok, obrigado" como alegria 0,98. Decisao: e ausencia de sinal, e ausencia
de sinal e `score: None` (invariante 2), nunca um numero.
"""

from datetime import datetime, timedelta, timezone

import pytest

from fraus.cortesia import e_so_cortesia
from fraus.modelos import Conversa, Mensagem
from fraus.motor import Motor
from fraus.resumo import desfecho

T = datetime(2026, 9, 15, 10, tzinfo=timezone.utc)


def _conversa(*falas_cliente, escalou=False):
    mensagens = [Mensagem(autor="bot", texto="posso ajudar em algo mais?", enviada_em=T)]
    for i, texto in enumerate(falas_cliente, start=1):
        mensagens.append(Mensagem(autor="cliente", texto=texto, enviada_em=T + timedelta(seconds=10 * i)))
    return Conversa(id="c", canal="csv", iniciada_em=T, mensagens=mensagens, escalou_para_humano=escalou)


@pytest.mark.parametrize("texto", ["ok, obrigado", "Valeu!", "OBRIGADA", "tá bom então", "ok", "muito obrigado!!"])
def test_formulas_de_cortesia(texto):
    assert e_so_cortesia(texto)


@pytest.mark.parametrize("texto", ["valeu, resolveu na hora", "ok mas nao funcionou", "obrigado por nada", "👍"])
def test_fala_com_conteudo_nao_e_cortesia(texto):
    assert not e_so_cortesia(texto)


def test_conversa_so_de_cortesia_nao_tem_sinal():
    assert _conversa("ok, obrigado", "valeu").tem_sinal_cliente is False
    assert _conversa("ok, obrigado", "valeu").tem_fala_cliente is True


def test_uma_fala_com_conteudo_basta_para_ter_sinal():
    assert _conversa("ok, obrigado", "mas o boleto nao chegou").tem_sinal_cliente is True


class _NuncaChamado:
    def prever_mensagens(self, textos):  # pragma: no cover - a guarda e nao chegar aqui
        raise AssertionError("modelo nao deveria rodar sem sinal")


def test_motor_devolve_none_e_nao_roda_modelo():
    motor = Motor(_NuncaChamado(), object(), _NuncaChamado(), _NuncaChamado())
    assert motor.pontuar_conversa(_conversa("valeu")) is None


def test_desfecho_operacional_nao_muda_por_cortesia():
    """Desfecho e sobre a OPERACAO (escalou? ficou sem resposta?), nao sobre a
    nota. Cliente que so agradeceu e depois foi escalado continua escalado."""
    assert desfecho(_conversa("valeu", escalou=True)) == "escalada"


def test_so_cortesia_e_ausencia_e_nao_evidencia_fraca():
    from fraus.evidencia import evidencia_fraca, motivos_de_evidencia_fraca

    conversa = _conversa("ok, obrigado")
    assert evidencia_fraca(conversa) is None
    assert motivos_de_evidencia_fraca(conversa) == []
