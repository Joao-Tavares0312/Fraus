"""Motivo de rejeicao nao carrega o valor recebido (auditoria de 13/10/2026).

O motivo e gravado em `importacoes` e lido em /integracoes/importacoes: a
armadilha 10 do handoff (o texto do erro embute o `input_value`) por outro
caminho. O motivo diz ONDE e O QUE, nunca o valor.
"""

import csv
import io

from fraus.ingest.csv_driver import carregar_linhas
from fraus.ingest.totalk import COLUNAS, converter

PII = ("529.982.247-25", "fulano@exemplo.com", "98888-7777")


def _csv(cabecalho, *linhas) -> list[str]:
    saida = io.StringIO()
    escritor = csv.writer(saida)
    escritor.writerow(cabecalho)
    escritor.writerows(linhas)
    return saida.getvalue().splitlines(keepends=True)


def test_csv_canonico_nao_grava_valor_da_data_invalida_nem_da_validacao():
    cabecalho = ["conversa_id", "canal", "autor", "texto", "enviada_em", "escalou_para_humano"]
    resultado = carregar_linhas(_csv(
        cabecalho,
        ["c1", "web", "cliente", "oi", "529.982.247-25 fulano@exemplo.com", "false"],
        ["c2", "web", "Maria 11 98888-7777", "oi", "2026-09-15T10:00:00-03:00", "false"],
    ))
    motivos = " ".join(r.motivo for r in resultado.rejeitadas)
    assert len(resultado.rejeitadas) == 2
    assert "enviada_em" in motivos and "autor" in motivos
    assert not any(valor in motivos for valor in PII)


def test_totalk_nao_grava_quem_enviou_nem_a_data_crua():
    url = "https://app.totalk/x?id=abc-123"
    linhas = _csv(
        COLUNAS,
        ["Conta", "09/15/2026 10:00:00", "fulano@exemplo.com 98888-7777", "oi", url],
        ["Conta", "529.982.247-25", "De: Cliente Para: Conta", "oi", url],
    )
    motivos = " ".join(i.motivo for i in converter(linhas).ignoradas)
    assert "Quem enviou" in motivos and "data" in motivos
    assert not any(valor in motivos for valor in PII)
