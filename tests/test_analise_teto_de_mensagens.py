"""O teto que limita o que de fato custa: mensagens de cliente por analise.

POR QUE ELE EXISTE. Os outros dois tetos da rota medem grandezas que nao
governam o tempo -- bytes do arquivo e numero de conversas. Um xlsx de 125 kB
dentro dos dois levou 314 SEGUNDOS medidos (10 conversas, 600 mensagens, 2964
palavras de cliente a ~106 ms cada, porque a oclusao roda uma passada de
BERTimbau por palavra). O proxy da dashboard desiste aos 60 s, e a tela
anunciava "API nao respondeu" sobre uma API viva e trabalhando.

O QUE ESTES TESTES PROTEGEM, em ordem de importancia:

1. o corte e por CONVERSA INTEIRA. Cortar mensagens no meio caberia no mesmo
   orcamento e produziria um score calculado sobre meia conversa, exibido com
   a mesma cara de um score completo -- numero errado apresentado como certo;
2. o corte e RELATADO. Silenciar faria o operador achar que analisou o arquivo
   inteiro;
3. um atendimento sozinho acima do teto vira 400 que NOMEIA os dois numeros, e
   nao um 502 por tempo esgotado que culpa a rede por uma decisao de produto.
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from fraus.api.main import criar_app
from fraus.api.rotas.analise import (TETO_MENSAGENS_CLIENTE_ANALISE,
                                     cabem_no_orcamento)
from fraus.db import Banco
from fraus.modelos import Conversa, Mensagem
from tests.test_api import MotorFalso

INICIO = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)


def conversa_com(identificador: str, mensagens_de_cliente: int) -> Conversa:
    """Uma conversa com N falas de cliente, alternadas com o bot."""
    mensagens = []
    for indice in range(mensagens_de_cliente * 2):
        do_cliente = indice % 2 == 0
        mensagens.append(
            Mensagem(
                autor="cliente" if do_cliente else "bot",
                texto="demorou demais e ninguem resolveu" if do_cliente else "um momento",
                enviada_em=INICIO + timedelta(minutes=indice),
            )
        )
    return Conversa(
        id=identificador, canal="whatsapp", iniciada_em=INICIO, mensagens=mensagens
    )


def csv_de(conversas: list[Conversa]) -> bytes:
    linhas = ["conversa_id,canal,autor,texto,enviada_em,escalou_para_humano"]
    for conversa in conversas:
        for mensagem in conversa.mensagens:
            linhas.append(
                f"{conversa.id},{conversa.canal},{mensagem.autor},{mensagem.texto},"
                f"{mensagem.enviada_em.isoformat()},false"
            )
    return "\n".join(linhas).encode("utf-8")


@pytest.fixture
def cliente(tmp_path):
    banco = Banco(tmp_path / "fraus.db")
    banco.migrar()
    return TestClient(
        criar_app(banco=banco, motor=MotorFalso(), raiz_importacao=tmp_path)
    )


# ---- o corte em si -----------------------------------------------------


def test_conversa_nunca_e_cortada_pela_metade():
    """A garantia central: cada conversa escolhida entra INTEIRA.

    Se o corte fosse por mensagem, a soma bateria exatamente no teto -- e e
    justamente esse "exatamente" que denunciaria uma conversa partida ao meio.
    """
    conversas = [conversa_com(f"c{i}", 15) for i in range(5)]
    escolhidas, total = cabem_no_orcamento(conversas)

    assert total <= TETO_MENSAGENS_CLIENTE_ANALISE
    for conversa in escolhidas:
        assert len(conversa.mensagens_cliente) == 15, "conversa entrou partida"
    # 15+15 = 30 cabe; 45 estouraria. Duas, e nao "duas e dois tercos".
    assert len(escolhidas) == 2
    assert total == 30


def test_para_antes_de_estourar_e_nao_depois():
    conversas = [conversa_com("a", 30), conversa_com("b", 30)]
    escolhidas, total = cabem_no_orcamento(conversas)
    assert len(escolhidas) == 1 and total == 30


def test_arquivo_pequeno_passa_inteiro():
    """O teto nao pode atrapalhar o caso comum -- uma conversa de tamanho normal."""
    conversas = [conversa_com("a", 5), conversa_com("b", 6)]
    escolhidas, total = cabem_no_orcamento(conversas)
    assert len(escolhidas) == 2 and total == 11


def test_primeira_conversa_entra_mesmo_estourando():
    """Ela entra para a ROTA poder recusar com o numero na mao.

    Devolver lista vazia aqui apagaria a informacao de QUANTO estourou, e a
    recusa viraria um "arquivo grande demais" que nao diz o que cortar.
    """
    escolhidas, total = cabem_no_orcamento([conversa_com("gigante", 300)])
    assert len(escolhidas) == 1 and total == 300


# ---- o que a rota faz com isso -----------------------------------------


def test_arquivo_grande_corta_conversas_e_RELATA(cliente):
    conversas = [conversa_com(f"c{i}", 12) for i in range(6)]  # 72 no total
    resposta = cliente.post(
        "/analisar/arquivo",
        files={"arquivo": ("lote.csv", csv_de(conversas), "text/csv")},
    )
    assert resposta.status_code == 200
    corpo = resposta.json()

    assert corpo["conversas_no_arquivo"] == 6
    assert corpo["conversas_analisadas"] == 3  # 12*3 = 36 cabe, 48 nao
    assert corpo["mensagens_cliente_analisadas"] == 36
    assert corpo["teto_mensagens_cliente"] == TETO_MENSAGENS_CLIENTE_ANALISE
    # O corte APARECE: sem isto o operador acha que viu o arquivo inteiro.
    assert corpo["conversas_analisadas"] < corpo["conversas_no_arquivo"]
    assert len(corpo["analises"]) == 3


def test_um_atendimento_grande_demais_e_400_que_diz_os_numeros(cliente):
    resposta = cliente.post(
        "/analisar/arquivo",
        files={"arquivo": ("grande.csv", csv_de([conversa_com("g", 120)]), "text/csv")},
    )
    assert resposta.status_code == 400
    detalhe = resposta.json()["detail"]
    # OS DOIS numeros: quanto veio e quanto cabe. Sem eles a recusa nao diz o
    # que fazer a seguir.
    assert "120" in detalhe
    assert str(TETO_MENSAGENS_CLIENTE_ANALISE) in detalhe
    assert "importacao" in detalhe.lower()


def test_conversa_no_limite_exato_passa(cliente):
    """Fronteira: 40 e o teto, entao 40 CABE -- `>` e nao `>=` na recusa."""
    resposta = cliente.post(
        "/analisar/arquivo",
        files={
            "arquivo": (
                "limite.csv",
                csv_de([conversa_com("no-limite", TETO_MENSAGENS_CLIENTE_ANALISE)]),
                "text/csv",
            )
        },
    )
    assert resposta.status_code == 200
    assert resposta.json()["mensagens_cliente_analisadas"] == TETO_MENSAGENS_CLIENTE_ANALISE
