import pytest
from pathlib import Path

from fraus.ingest.csv_driver import carregar_csv

CABECALHO = "conversa_id,canal,autor,texto,enviada_em,escalou_para_humano\n"


def _escrever(tmp_path: Path, linhas: str) -> Path:
    caminho = tmp_path / "conversas.csv"
    caminho.write_text(CABECALHO + linhas, encoding="utf-8")
    return caminho


def test_agrupa_mensagens_por_conversa(tmp_path):
    caminho = _escrever(tmp_path, (
        "c1,csv,cliente,oi,2026-08-13T10:00:00+00:00,false\n"
        "c1,csv,bot,ola,2026-08-13T10:00:07+00:00,false\n"
        "c2,csv,cliente,socorro,2026-08-13T11:00:00+00:00,true\n"
    ))
    resultado = carregar_csv(caminho)

    assert len(resultado.conversas) == 2
    c1 = next(c for c in resultado.conversas if c.id == "c1")
    assert len(c1.mensagens) == 2
    assert c1.iniciada_em.second == 0
    assert c1.encerrada_em.second == 7
    assert c1.escalou_para_humano is False

    c2 = next(c for c in resultado.conversas if c.id == "c2")
    assert c2.escalou_para_humano is True


def test_mensagens_saem_ordenadas_por_timestamp(tmp_path):
    caminho = _escrever(tmp_path, (
        "c1,csv,bot,segunda,2026-08-13T10:00:07+00:00,false\n"
        "c1,csv,cliente,primeira,2026-08-13T10:00:00+00:00,false\n"
    ))
    resultado = carregar_csv(caminho)
    assert [m.texto for m in resultado.conversas[0].mensagens] == ["primeira", "segunda"]


def test_linha_malformada_e_rejeitada_sem_derrubar_o_lote(tmp_path):
    caminho = _escrever(tmp_path, (
        "c1,csv,cliente,oi,2026-08-13T10:00:00+00:00,false\n"
        "c2,csv,cliente,quebrada,data-invalida,false\n"
        "c3,csv,gerente,autor-errado,2026-08-13T10:00:00+00:00,false\n"
    ))
    resultado = carregar_csv(caminho)

    assert {c.id for c in resultado.conversas} == {"c1"}
    assert [r.numero_linha for r in resultado.rejeitadas] == [3, 4]
    assert all(r.motivo for r in resultado.rejeitadas)


def test_timestamp_sem_offset_e_rejeitado(tmp_path):
    caminho = _escrever(tmp_path, "c1,csv,cliente,oi,2026-08-13T10:00:00,false\n")
    resultado = carregar_csv(caminho)
    assert resultado.conversas == []
    assert len(resultado.rejeitadas) == 1


def test_coluna_ausente_levanta_keyerror(tmp_path):
    """Coluna estruturalmente ausente deve propagar KeyError, nao rejeitar silenciosamente linhas."""
    caminho = tmp_path / "conversas.csv"
    # Cabeçalho sem a coluna 'enviada_em' (usa 'timestamp' em vez)
    caminho.write_text(
        "conversa_id,canal,autor,texto,timestamp,escalou_para_humano\n"
        "c1,csv,cliente,oi,2026-08-13T10:00:00+00:00,false\n",
        encoding="utf-8"
    )
    # Deve levantar KeyError, nao devolver rejeitadas
    try:
        carregar_csv(caminho)
        assert False, "Esperava KeyError para coluna ausente"
    except KeyError:
        pass  # Comportamento esperado


# --- linha CURTA: o TypeError que virava 500 --------------------------------
#
# `csv.DictReader` devolve None para a coluna que a linha nao alcancou, e
# `datetime.fromisoformat(None)` levanta TypeError -- que NAO estava no except.
# Ele escapava tambem das bordas HTTP (rotas/conversas.py e rotas/analise.py so
# traduzem KeyError), entao um CSV com uma linha truncada virava 500 na tela de
# upload -- contradizendo o docstring deste modulo: "uma linha malformada nunca
# derruba o lote inteiro".
#
# E DIFERENTE do teste acima: la falta a coluna no CABECALHO (defeito do
# arquivo, causa unica, KeyError de proposito); aqui o cabecalho esta correto e
# so UMA linha acabou cedo.


def test_linha_truncada_e_rejeitada_sem_derrubar_o_lote(tmp_path):
    caminho = _escrever(tmp_path, (
        "c1,webchat,cliente,oi,2026-05-14T10:00:00+00:00,false\n"
        "c1,webchat,cliente\n"
        "c1,webchat,bot,ola,2026-05-14T10:00:20+00:00,false\n"
    ))
    resultado = carregar_csv(caminho)

    assert [linha.numero_linha for linha in resultado.rejeitadas] == [3]
    assert len(resultado.conversas) == 1
    assert len(resultado.conversas[0].mensagens) == 2


def test_o_motivo_da_rejeicao_nomeia_a_coluna_que_faltou(tmp_path):
    """`str(TypeError)` cru diria "fromisoformat: argument must be str", que
    nao ajuda ninguem a consertar a planilha."""
    caminho = _escrever(tmp_path, "c1,webchat,cliente,oi\n")
    motivo = carregar_csv(caminho).rejeitadas[0].motivo
    assert "enviada_em" in motivo and "linha 2" in motivo


def test_linha_curta_na_ULTIMA_coluna_tambem_e_isolada(tmp_path):
    """`escalou_para_humano` e lida FORA do try, no `.strip()` -- o mesmo
    TypeError, num lugar que o except original nem alcancava."""
    caminho = _escrever(tmp_path, (
        "c1,webchat,cliente,oi,2026-05-14T10:00:00+00:00\n"
        "c1,webchat,bot,ola,2026-05-14T10:00:20+00:00,false\n"
    ))
    resultado = carregar_csv(caminho)
    assert [linha.numero_linha for linha in resultado.rejeitadas] == [2]
    assert len(resultado.conversas) == 1
