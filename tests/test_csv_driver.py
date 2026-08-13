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
