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


def _xlsx(linhas):
    import io

    from openpyxl import Workbook

    pasta = Workbook()
    aba = pasta.active
    for linha in linhas:
        aba.append(linha)
    saida = io.BytesIO()
    pasta.save(saida)
    return saida.getvalue()


def test_id_de_chat_plausivel_como_epoch_perde_para_a_coluna_de_data():
    # Export do TARS (16/10/2026): "Chat ID" do Telegram ao lado de "Data e
    # hora" com datetime de celula. Um id de dez digitos DENTRO da janela de
    # epoch empatava com a data verdadeira -- e quem ganhava o desempate
    # decidia se a conversa tinha horario ou virava "data ilegivel".
    agora = datetime(2026, 9, 23, 12, 2, 44)
    cabecalho = ["ID", "Instância ID", "Instância", "Canal", "Chat ID", "Papel",
                 "Conteúdo", "Data e hora", "Latência (ms)", "Provedor", "Modelo", "Sucesso"]
    linhas = [cabecalho]
    for i, (papel, texto) in enumerate([
        ("user", "Tu faz o L?"), ("assistant", "Não, sou um assistente de suporte"),
        ("user", "O que é wascer"), ("assistant", "A Wascer é a plataforma de tracking"),
    ]):
        linhas.append([str(42 + i), "inst_x", "TARS", "telegram", "1712345678", papel,
                       texto, agora + timedelta(seconds=30 * i), None, None, None, True])
    extracao = extrair("tars.xlsx", _xlsx(linhas))
    papeis = extracao.mapeamento["papeis"]
    assert papeis["enviada_em"]["coluna"] == "Data e hora"
    assert papeis["conversa_id"]["coluna"] == "Chat ID"
    assert extracao.tem_tempo is True
    assert len(extracao.conversas[0].mensagens) == 4


def test_oito_digitos_nao_e_data_compacta():
    # `datetime.fromisoformat("20240115")` aceita desde o Python 3.11: um id
    # numerico de oito digitos virava data.
    datas, _ = mapeador.interpretar_datas(["20240115", "20240116"], ["c", "c"], None)
    assert datas == [None, None]


def test_perfil_salvo_errado_nao_estraga_a_leitura():
    # Producao, 19/10/2026: um perfil salvo dizia que a data era a coluna
    # "Chat ID". Perfil vence a heuristica, e o arquivo inteiro voltava como
    # "data ilegivel" -- mesmo a heuristica sozinha lendo o export certo.
    from fraus.ingest.arquivos import OpcoesDeLeitura

    agora = datetime(2026, 9, 23, 12, 2, 44)
    cabecalho = ["Chat ID", "Papel", "Conteúdo", "Data e hora"]
    linhas = [cabecalho] + [
        ["8624457065", papel, texto, agora + timedelta(seconds=30 * i)]
        for i, (papel, texto) in enumerate([("user", "oi tudo bem"), ("assistant", "olá, como posso ajudar"),
                                            ("user", "quero saber dos planos"), ("assistant", "temos três planos")])
    ]
    perfil_errado = {"id": 7, "nome": "tars antigo", "ordem_data": None, "papeis": {
        "texto": "Conteúdo", "autor": "Papel", "enviada_em": "Chat ID", "conversa_id": None, "canal": None}}
    extracao = extrair("tars.xlsx", _xlsx(linhas), OpcoesDeLeitura(perfil_para=lambda _a: perfil_errado))
    assert extracao.tem_tempo is True
    assert len(extracao.conversas[0].mensagens) == 4
    assert extracao.mapeamento["papeis"]["enviada_em"]["coluna"] == "Data e hora"
    assert extracao.perfil is None
    assert any("tars antigo" in aviso for aviso in extracao.avisos)
