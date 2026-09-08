"""A contestacao chega na leitura, derivada, sem mexer em nenhum agregado.

A marca e DERIVADA NA LEITURA, como a categoria: nao ha coluna nova no banco e
nada e recalculado pelo modelo. Os dois ingredientes ja estavam ali -- o
`score` gravado e a `latencia_mediana_s`, que `resumir` deriva dos timestamps a
cada leitura (invariante 5). E por isso que a marca vale RETROATIVAMENTE para o
que ja esta no banco, inclusive as conversas da demonstracao.

O QUE ESTES TESTES MAIS PROTEGEM nao e a presenca da marca: e a AUSENCIA de
efeito colateral. NPS, CSAT e contencao nao podem mudar por causa dela. No dia
em que alguem "melhorar" a contestacao tirando o atendimento do agregado, o
indicador esvazia em silencio -- e a primeira pergunta que a banca faz e
"quantos atendimentos sumiram?".

Ver `docs/superpowers/specs/2026-09-08-abstencao-por-contestacao-design.md`.
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.contestacao import MOTIVO
from fraus.db import Banco
from fraus.modelos import Conversa, Mensagem
from tests.test_api import MotorFalso

INICIO = datetime(2026, 9, 8, 10, 0, tzinfo=timezone.utc)

# A frase canonica do projeto, com o relogio que ela descreve.
TRES_HORAS = timedelta(hours=3)
DOZE_SEGUNDOS = timedelta(seconds=12)


def _conversa(conversa_id: str, espera: timedelta) -> Conversa:
    """Cliente elogia, o bot responde depois de `espera`."""
    return Conversa(
        id=conversa_id,
        canal="whatsapp",
        iniciada_em=INICIO,
        mensagens=[
            Mensagem(
                autor="cliente",
                texto="que atendimento maravilhoso",
                enviada_em=INICIO,
            ),
            Mensagem(
                autor="bot",
                texto="que bom que gostou",
                enviada_em=INICIO + espera,
            ),
        ],
    )


@pytest.fixture
def banco(tmp_path):
    banco = Banco(tmp_path / "fraus.db")
    banco.migrar()
    return banco


@pytest.fixture
def cliente(banco, tmp_path):
    return TestClient(
        criar_app(banco=banco, motor=MotorFalso(), raiz_importacao=tmp_path)
    )


def _gravar(banco, conversa_id, espera, score):
    banco.salvar(_conversa(conversa_id, espera), score, "promotor")


# ---- a marca aparece ----------------------------------------------------


def test_a_lista_traz_a_contestacao_do_elogio_contra_espera(cliente, banco):
    """O caso em si. Este e o teste que impede a regressao."""
    _gravar(banco, "contestada", TRES_HORAS, 99.93)

    linha = cliente.get("/conversas").json()[0]
    assert linha["contestacao"]["motivo"] == MOTIVO


def test_o_detalhe_traz_a_mesma_contestacao_da_lista(cliente, banco):
    """A lista e o detalhe nao podem derivar a marca por caminhos diferentes --
    seria a divergencia que a nota derivada no servidor ja existe para evitar,
    repetida na coluna do lado."""
    _gravar(banco, "contestada", TRES_HORAS, 99.93)

    da_lista = cliente.get("/conversas").json()[0]["contestacao"]
    do_detalhe = cliente.get("/conversas/contestada").json()["contestacao"]
    assert da_lista == do_detalhe


def test_a_marca_leva_os_numeros_que_a_tela_escreve(cliente, banco):
    """A frase da tela ("elogio saturado contra espera de 3h") sai destes
    campos. Mandar so um booleano obrigaria o TypeScript a ter uma copia da
    regra -- que e a invariante 3 quebrada pela porta dos fundos."""
    _gravar(banco, "contestada", TRES_HORAS, 99.93)

    marca = cliente.get("/conversas/contestada").json()["contestacao"]
    assert marca["score"] == 99.93
    assert marca["latencia_mediana_s"] == TRES_HORAS.total_seconds()
    assert marca["limiar_score"] == 95.0
    assert marca["limiar_s"] == 180.0


# ---- e quase sempre ausente ---------------------------------------------


def test_elogio_rapido_nao_vem_contestado(cliente, banco):
    _gravar(banco, "rapida", DOZE_SEGUNDOS, 99.93)

    assert cliente.get("/conversas").json()[0]["contestacao"] is None
    assert cliente.get("/conversas/rapida").json()["contestacao"] is None


def test_conversa_sem_score_nao_vem_contestada(cliente, banco):
    """`score: None` e ausencia de dado, nunca insatisfacao e nunca
    contestacao (invariante 2)."""
    banco.salvar(_conversa("sem-sinal", TRES_HORAS), None, None)

    assert cliente.get("/conversas").json()[0]["contestacao"] is None


# ---- o que NAO pode mudar ----------------------------------------------


def test_a_contestacao_nao_mexe_em_score_nota_nem_categoria(cliente, banco):
    """Ela MARCA, nao corrige. O numero contestado continua sendo o numero."""
    _gravar(banco, "contestada", TRES_HORAS, 99.93)

    linha = cliente.get("/conversas").json()[0]
    assert linha["score"] == 99.93
    assert linha["nota"] == 10
    assert linha["categoria"] == "promotor"


def test_o_atendimento_contestado_continua_contando_no_NPS(cliente, banco):
    """A decisao central deste desenho, e a mais facil de reverter sem querer.
    Tirar do agregado seria mais honesto no caso isolado e mais perigoso no
    conjunto: um limiar mal calibrado esvazia o indicador em silencio.

    Duas conversas, as duas promotoras, uma delas contestada -> NPS 100 e as
    duas contadas. Se alguem passar a excluir a contestada, o total cai para 1
    e este teste fala.
    """
    _gravar(banco, "contestada", TRES_HORAS, 99.93)
    _gravar(banco, "limpa", DOZE_SEGUNDOS, 99.0)

    indicadores = cliente.get("/indicadores").json()
    assert indicadores["total_conversas"] == 2
    assert indicadores["nps"] == 100.0
