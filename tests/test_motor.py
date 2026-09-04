"""Testes do Motor, com classificadores dubles e um Fusor treinado de verdade.

Nao usa a fixture `cliente` de `tests/test_api.py`: o `MotorFalso` de la e um
duble de ROTA (testa a mecanica HTTP), nao devolve as mesmas chaves que o
`Motor` real -- `sinais_fora_do_score` nunca chega la porque o duble nao a
inclui. Este arquivo testa o `Motor` de verdade, com cabecas trocadas por
dublês deterministicos, para o comportamento do CODIGO de producao ser
coberto e nao so a rota.
"""

from datetime import datetime, timezone

from fraus.fusor import NOMES_FEATURES, Fusor
from fraus.modelos import Conversa, Mensagem
from fraus.motor import Motor
from fraus.sinais.emocao import NOMES_EMOCOES


class _TextoDuble:
    def prever_mensagens(self, textos):
        return [[0.2, 0.3, 0.5] for _ in textos]


class _EmocaoDuble:
    def prever_mensagens(self, textos):
        uniforme = 1.0 / len(NOMES_EMOCOES)
        return [[uniforme] * len(NOMES_EMOCOES) for _ in textos]


class _IroniaDuble:
    def prever_mensagens(self, textos):
        return [[0.1, 0.9] for _ in textos]


def _fusor_treinado() -> Fusor:
    base = {nome: 0.0 for nome in NOMES_FEATURES}
    exemplos, rotulos = [], []
    for _ in range(5):
        exemplos.append({**base, "texto_prob_satisfeito_media": 0.9})
        rotulos.append(2)
        exemplos.append({**base, "texto_prob_insatisfeito_media": 0.9})
        rotulos.append(0)
    fusor = Fusor()
    fusor.treinar(exemplos, rotulos)
    return fusor


def _conversa_com(texto: str) -> Conversa:
    base = datetime(2026, 9, 4, 10, 0, 0, tzinfo=timezone.utc)
    return Conversa(
        id="c1",
        canal="csv",
        iniciada_em=base,
        mensagens=[Mensagem(autor="cliente", texto=texto, enviada_em=base)],
    )


def _motor() -> Motor:
    return Motor(_TextoDuble(), _fusor_treinado(), _EmocaoDuble(), _IroniaDuble())


def test_atribuir_conversa_marca_ironia_como_sinal_fora_do_score():
    """A ironia continua carregada e por mensagem, so nao pontua mais.

    `sinais_fora_do_score` existe exatamente para "sinais que vieram mas nao
    entram no score". Esvaziou entre 21/08/2026 e 03/09/2026, quando a ironia
    entrava no vetor; volta a ter `["prob_ironia"]` desde 04/09/2026 -- ver o
    comentario de `NOMES_FEATURES` em `fraus/fusor.py`.
    """
    atribuicao = _motor().atribuir_conversa(_conversa_com("otimo atendimento"))
    assert atribuicao["sinais_fora_do_score"] == ["prob_ironia"]


def test_atribuir_conversa_ainda_le_a_ironia_por_mensagem():
    """A cabeca nao sumiu -- so parou de pontuar. `prob_ironia` continua vindo."""
    atribuicao = _motor().atribuir_conversa(_conversa_com("otimo atendimento"))
    mensagem = atribuicao["mensagens"][0]
    assert mensagem["prob_ironia"] == 0.9


def test_atribuir_conversa_contribuicoes_nao_tem_chave_de_ironia():
    """`contribuicoes` segue exatamente `NOMES_FEATURES` (38, sem ironia)."""
    atribuicao = _motor().atribuir_conversa(_conversa_com("otimo atendimento"))
    assert set(atribuicao["contribuicoes"]) == set(NOMES_FEATURES)
    assert "ironia_prob_media" not in atribuicao["contribuicoes"]
    assert "ironia_prob_max" not in atribuicao["contribuicoes"]


def test_pontuar_conversa_nao_precisa_do_classificador_de_ironia_para_o_vetor():
    """`montar_features`, chamado por dentro, nao usa `self._ironia` -- so o
    Motor continua exigindo-a no construtor (invariante 7)."""
    score = _motor().pontuar_conversa(_conversa_com("otimo atendimento"))
    assert score is not None
    assert 0.0 <= score <= 100.0
