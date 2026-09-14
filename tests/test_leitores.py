"""Testes dos leitores: bytes de qualquer formato -> tabela.

O leitor nao sabe o que e conversa -- so transforma arquivo em colunas e
linhas. Quem da sentido a elas e o mapeador.
"""

import json

from fraus.ingest.arquivos import extrair
from fraus.ingest.leitores import (
    decodificar,
    detectar_delimitador,
    tabela_de_json,
    tabela_de_whatsapp,
)


def test_delimitador_ponto_e_virgula_do_excel_brasileiro():
    texto = "data;autor;texto\n14/05/2026;cliente;oi, tudo bem?\n14/05/2026;bot;ola, sim\n"
    assert detectar_delimitador(texto) == ";"


def test_delimitador_tab():
    assert detectar_delimitador("a\tb\tc\n1\t2\t3\n") == "\t"


def test_virgula_dentro_do_texto_nao_engana_o_delimitador():
    texto = 'autor,texto\ncliente,"oi, tudo bem, e voce?"\nbot,"sim, obrigado"\n'
    assert detectar_delimitador(texto) == ","


def test_decodifica_utf8_e_cai_para_cp1252_relatando():
    assert decodificar("ação".encode("utf-8")) == ("ação", "utf-8")
    texto, codificacao = decodificar("ação “aspas”".encode("cp1252"))
    assert texto == "ação “aspas”"
    assert codificacao == "cp1252"


def test_json_aninhado_acha_a_lista_de_mensagens_e_herda_o_id_da_conversa():
    dados = {
        "conversas": [
            {"id": "c1", "mensagens": [
                {"autor": {"tipo": "cliente"}, "texto": "oi", "em": "2026-05-14T10:00:00Z"},
                {"autor": {"tipo": "bot"}, "texto": "ola", "em": "2026-05-14T10:00:05Z"},
            ]},
            {"id": "c2", "mensagens": [
                {"autor": {"tipo": "cliente"}, "texto": "tchau", "em": "2026-05-14T11:00:00Z"},
            ]},
        ]
    }
    colunas, linhas = tabela_de_json(json.dumps(dados))
    assert len(linhas) == 3
    assert "autor.tipo" in colunas
    assert "conversas.id" in colunas
    assert linhas[2][colunas.index("conversas.id")] == "c2"


def test_jsonl_uma_mensagem_por_linha():
    texto = '{"a": "cliente", "t": "oi"}\n{"a": "bot", "t": "ola"}\n'
    colunas, linhas = tabela_de_json(texto)
    assert colunas == ["a", "t"]
    assert len(linhas) == 2


WHATSAPP = (
    "14/05/2026 10:00 - Maria: oi, meu pedido nao chegou\n"
    "14/05/2026 10:04 - Loja: ola! vou verificar\n"
    "continuacao da mensagem da loja\n"
    "[14/05/2026, 10:05:30] Maria: obrigada\n"
)


def test_whatsapp_txt_vira_tabela_e_linha_solta_continua_a_anterior():
    tabela = tabela_de_whatsapp(WHATSAPP)
    assert tabela is not None
    colunas, linhas = tabela
    assert len(linhas) == 3
    assert "continuacao" in linhas[1][colunas.index("mensagem")]


def test_texto_que_nao_e_whatsapp_devolve_none():
    assert tabela_de_whatsapp("Cliente: oi\nBot: ola\n") is None


# ---------------------------------------------------------------------------
# ponta a ponta pelo `extrair`


def test_csv_desconhecido_com_ponto_e_virgula_entra_sem_adaptador():
    csv = (
        "Protocolo;Remetente;Conteúdo da mensagem;Data/Hora\n"
        "P1;Cliente;minha internet caiu de novo;14/05/2026 10:00\n"
        "P1;Atendente;vou abrir um chamado;14/05/2026 10:07\n"
        "P1;Cliente;ok obrigado;25/05/2026 10:08\n"
    ).encode("cp1252")
    extracao = extrair("export.csv", csv)
    assert len(extracao.conversas) == 1
    assert extracao.tem_tempo is True
    assert "inferid" in extracao.formato
    assert [m.autor for m in extracao.conversas[0].mensagens] == ["cliente", "humano", "cliente"]


def test_json_entra_pelo_extrair():
    dados = [
        {"ticket": "t1", "from": "customer", "message": "nao consigo logar", "timestamp": "2026-05-14T10:00:00Z"},
        {"ticket": "t1", "from": "agent", "message": "vou resetar sua senha", "timestamp": "2026-05-14T10:03:00Z"},
    ]
    extracao = extrair("tickets.json", json.dumps(dados).encode())
    assert len(extracao.conversas) == 1
    assert extracao.tem_tempo is True


def test_whatsapp_entra_pelo_extrair_com_tempo():
    extracao = extrair("Conversa do WhatsApp com Maria.txt", WHATSAPP.encode())
    assert extracao.tem_tempo is True
    autores = [m.autor for m in extracao.conversas[0].mensagens]
    assert autores == ["cliente", "humano", "cliente"]


def test_txt_em_prosa_continua_sendo_transcricao():
    extracao = extrair("conversa.txt", b"Cliente: oi\nBot: ola, como posso ajudar?\n")
    assert extracao.tem_tempo is False
    assert len(extracao.conversas[0].mensagens) == 2
