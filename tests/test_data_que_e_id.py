"""Numero de dez digitos nao e horario so por ter dez digitos.

Em producao, 02/10/2026: a unica conversa do banco estava datada de 19/04/2243.
O arquivo trazia o id do chat do Telegram (8624457065) e nenhuma coluna de
data; o mapeador leu o id como segundos desde 1970. Pior que a data: todas as
falas ficaram no mesmo instante, a latencia saiu zero e a conversa recebeu NOTA
-- o numero melhor do que a verdade que `transcricao.py` recusa.
"""

from datetime import datetime, timedelta, timezone

from fraus.ingest import mapeador
from fraus.ingest.arquivos import extrair

SEM_DATA = (
    "chat_id;autor;texto\n"
    "8624457065;cliente;oi preciso de ajuda\n"
    "8624457065;bot;claro, em que posso ajudar\n"
)


def _epoch(instante: datetime) -> int:
    return int(instante.timestamp())


def test_id_do_chat_nao_vira_coluna_de_horario():
    extracao = extrair("telegram.csv", SEM_DATA.encode())
    assert "enviada_em" not in extracao.mapeamento["papeis"]
    assert extracao.tem_tempo is False


def test_telefone_tambem_nao():
    csv = SEM_DATA.replace("chat_id", "telefone").replace("8624457065", "3599887766")
    assert extrair("contatos.csv", csv.encode()).tem_tempo is False


def test_epoch_plausivel_continua_sendo_horario():
    ontem = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(days=1)
    csv = (
        "ts;autor;texto\n"
        f"{_epoch(ontem)};cliente;oi preciso de ajuda\n"
        f"{_epoch(ontem) + 42};bot;claro, em que posso ajudar\n"
    )
    extracao = extrair("log.csv", csv.encode())
    assert extracao.tem_tempo is True
    (conversa,) = extracao.conversas
    assert conversa.iniciada_em == ontem
    assert conversa.encerrada_em == ontem + timedelta(seconds=42)


def test_epoch_em_milissegundos_plausivel_tambem():
    ontem = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(days=1)
    datas, _ = mapeador.interpretar_datas([f"{_epoch(ontem)}000"], ["c"], None)
    assert datas == [ontem]


def test_epoch_no_futuro_ou_antes_de_2000_nao_e_data():
    futuro = _epoch(datetime.now(timezone.utc) + timedelta(days=30))
    datas, _ = mapeador.interpretar_datas(
        [str(futuro), "8624457065", "0946684799"], ["c", "c", "c"], None)
    assert datas == [None, None, None]


def test_id_confirmado_como_data_rejeita_as_linhas_em_vez_de_inventar_o_ano():
    """Quem confirma a coluna errada recebe "data ilegivel", nao uma conversa de 2243."""
    import pytest
    from fraus.ingest.arquivos import ArquivoIlegivelError, OpcoesDeLeitura

    opcoes = OpcoesDeLeitura(forcado={"texto": "texto", "autor": "autor", "enviada_em": "chat_id"})
    with pytest.raises(ArquivoIlegivelError, match="data ilegível"):
        extrair("telegram.csv", SEM_DATA.encode(), opcoes)
