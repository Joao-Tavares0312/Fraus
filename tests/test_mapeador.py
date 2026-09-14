"""Testes do mapeador: tabela de estrutura desconhecida -> conversas.

O mapeador existe para que um export novo nao exija um adaptador novo. Os
testes cobrem o que ele INFERE (qual coluna e qual papel, a ordem da data,
quem e o cliente) e, com o mesmo peso, o que ele RELATA: inferencia calada e
exatamente a armadilha da Totalk (MM/DD lido como DD/MM) repetida em escala.
"""

from datetime import timedelta, timezone

import pytest

from fraus.ingest.mapeador import (
    MapeamentoInsuficienteError,
    converter,
    interpretar_datas,
    mapear,
)


def _tabela(texto: str) -> tuple[list[str], list[list[str]]]:
    linhas = [linha.split("|") for linha in texto.strip().splitlines()]
    return linhas[0], linhas[1:]


ZENDESK = """
ticket|sender|body|created_at
T-1|customer|meu pedido nao chegou ainda|2026-05-14 10:00:00
T-1|agent|vou verificar para voce agora|2026-05-14 10:02:00
T-1|customer|obrigado, fico no aguardo|2026-05-14 10:03:00
T-2|customer|quero cancelar a assinatura|2026-05-15 09:00:00
T-2|bot|posso ajudar com o cancelamento|2026-05-15 09:00:05
"""


# ---------------------------------------------------------------------------
# papeis das colunas


def test_colunas_em_ingles_sao_reconhecidas_pelo_nome_e_pelo_conteudo():
    colunas, linhas = _tabela(ZENDESK)
    mapa = mapear(colunas, linhas)
    assert mapa.coluna("conversa_id") == "ticket"
    assert mapa.coluna("autor") == "sender"
    assert mapa.coluna("texto") == "body"
    assert mapa.coluna("enviada_em") == "created_at"
    assert mapa.papeis["texto"].confianca >= 0.8


def test_nome_de_coluna_inutil_ainda_mapeia_pelo_conteudo():
    colunas, linhas = _tabela(ZENDESK.replace("ticket|sender|body|created_at", "a|b|c|d"))
    mapa = mapear(colunas, linhas)
    assert mapa.coluna("texto") == "c"
    assert mapa.coluna("enviada_em") == "d"
    assert mapa.coluna("autor") == "b"


def test_duas_colunas_nunca_disputam_o_mesmo_papel():
    colunas, linhas = _tabela(ZENDESK)
    mapa = mapear(colunas, linhas)
    usadas = [p.coluna for p in mapa.papeis.values()]
    assert len(usadas) == len(set(usadas))


def test_sem_coluna_de_texto_a_recusa_diz_o_que_achou():
    colunas, linhas = _tabela("id|valor\n1|10\n2|20\n")
    with pytest.raises(MapeamentoInsuficienteError) as erro:
        converter(colunas, linhas, "CSV")
    mensagem = str(erro.value)
    assert "texto" in mensagem
    assert "id" in mensagem and "valor" in mensagem


# ---------------------------------------------------------------------------
# datas


def test_campo_maior_que_12_no_primeiro_lugar_decide_dia_primeiro():
    datas, relato = interpretar_datas(["03/05/2026 10:00", "25/05/2026 10:00"])
    assert datas[1].day == 25 and datas[0].month == 5
    assert relato.ordem == "dia/mes"
    assert relato.ambigua is False


def test_campo_maior_que_12_no_segundo_lugar_decide_mes_primeiro():
    # A armadilha da Totalk, agora descoberta pelo dado e nao por adaptador.
    datas, relato = interpretar_datas(["05/03/2026 10:00:00", "05/22/2026 10:00:00"])
    assert datas[1].month == 5 and datas[1].day == 22
    assert relato.ordem == "mes/dia"


def test_data_ambigua_desempata_pela_ordem_das_mensagens():
    # Lidas como mes/dia sao dias seguidos; como dia/mes, saltam meses para tras.
    valores = ["01/02/2026 10:00", "01/03/2026 10:00", "01/04/2026 10:00", "01/05/2026 10:00"]
    grupos = ["c1"] * 4
    _, relato = interpretar_datas(valores, grupos)
    assert relato.ambigua is True
    assert relato.ordem in ("dia/mes", "mes/dia")


def test_data_ambigua_sem_desempate_e_relatada_como_suposicao():
    _, relato = interpretar_datas(["01/02/2026 10:00"])
    assert relato.ambigua is True
    assert any("ambígua" in aviso for aviso in relato.avisos)


def test_data_sem_fuso_ganha_o_padrao_e_avisa():
    datas, relato = interpretar_datas(["2026-05-14 10:00:00"])
    assert datas[0].tzinfo is not None
    assert datas[0].utcoffset() == timedelta(hours=-3)
    assert any("fuso" in aviso.lower() for aviso in relato.avisos)


def test_data_com_fuso_declarado_e_respeitada():
    datas, relato = interpretar_datas(["2026-05-14T10:00:00Z"])
    assert datas[0].utcoffset() == timedelta(0)
    assert not any("fuso" in aviso.lower() for aviso in relato.avisos)


def test_epoch_em_segundos_e_milissegundos():
    datas, _ = interpretar_datas(["1778752800", "1778752800000"])
    assert datas[0] == datas[1]
    assert datas[0].tzinfo == timezone.utc


def test_valor_que_nao_e_data_vira_none_e_nao_zero():
    datas, _ = interpretar_datas(["2026-05-14 10:00", "ontem"])
    assert datas[1] is None


# ---------------------------------------------------------------------------
# conversao


def test_converte_e_agrupa_por_conversa_com_tempo():
    colunas, linhas = _tabela(ZENDESK)
    extracao = converter(colunas, linhas, "CSV")
    assert len(extracao.conversas) == 2
    assert extracao.tem_tempo is True
    t1 = next(c for c in extracao.conversas if c.id == "T-1")
    assert [m.autor for m in t1.mensagens] == ["cliente", "humano", "cliente"]
    assert t1.escalou_para_humano is True
    assert any("inferi" in aviso.lower() for aviso in extracao.avisos)


def test_sem_coluna_de_data_nao_ha_nota():
    colunas, linhas = _tabela("quem|fala\ncliente|nao funciona nada aqui\nbot|sinto muito pelo problema\n")
    extracao = converter(colunas, linhas, "CSV")
    assert extracao.tem_tempo is False
    assert len(extracao.conversas) == 1


def test_autores_por_nome_de_pessoa_quem_abre_a_conversa_e_o_cliente():
    tabela = """
    data|nome|mensagem
    2026-05-14 10:00|Maria Souza|oi, meu boleto veio errado
    2026-05-14 10:05|Loja Exemplo|ola Maria, vou conferir
    2026-05-14 10:06|Maria Souza|obrigada
    """
    colunas, linhas = _tabela("\n".join(l.strip() for l in tabela.strip().splitlines()))
    extracao = converter(colunas, linhas, "CSV")
    autores = [m.autor for m in extracao.conversas[0].mensagens]
    assert autores == ["cliente", "humano", "cliente"]
    assert any("Maria Souza" in aviso for aviso in extracao.avisos)


def test_linha_com_data_invalida_e_rejeitada_sem_derrubar_o_lote():
    colunas, linhas = _tabela(ZENDESK + "T-2|customer|e ai?|amanha\n")
    extracao = converter(colunas, linhas, "CSV")
    assert len(extracao.rejeitadas) == 1
    assert "data" in extracao.rejeitadas[0]["motivo"]


def test_pii_e_censurada_na_entrada():
    colunas, linhas = _tabela(
        "sender|body|created_at\ncustomer|meu cpf e 529.982.247-25|2026-05-14 10:00:00\n"
    )
    extracao = converter(colunas, linhas, "CSV")
    assert "529.982.247-25" not in extracao.conversas[0].mensagens[0].texto
