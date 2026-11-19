"""A empresa ficticia da banca: deterministica, legivel pelo driver, identificada."""

import csv
import io

from fraus.ingest.csv_driver import carregar_linhas
from scripts.gerar_empresa_ficticia import ESPERA_DO_BOT, gerar


def test_duas_execucoes_geram_os_mesmos_bytes():
    assert gerar() == gerar()


def test_o_driver_le_156_atendimentos_sem_rejeitar_linha():
    resultado = carregar_linhas(io.StringIO(gerar()))
    assert resultado.rejeitadas == []
    assert len(resultado.conversas) == 156
    assert all(c.id.startswith("sintetica-lumen-") for c in resultado.conversas)


def test_todo_horario_tem_fuso():
    linhas = list(csv.DictReader(io.StringIO(gerar())))
    assert all(linha["enviada_em"].endswith("-03:00") for linha in linhas)


def test_os_casos_fixos_tem_a_propriedade_que_o_roteiro_usa():
    conversas = {c.id: c for c in carregar_linhas(io.StringIO(gerar())).conversas}
    assert not conversas["sintetica-lumen-cortesia"].tem_sinal_cliente
    assert not conversas["sintetica-lumen-sem-cliente"].mensagens_cliente
    assert len(conversas["sintetica-lumen-replay"].mensagens_cliente) == 14
    espera = conversas["sintetica-lumen-espera"].mensagens
    assert (espera[1].enviada_em - espera[0].enviada_em).total_seconds() == 420


def test_faixas_de_espera_se_sobrepoem_entre_tons():
    """Faixa disjunta por classe entrega o rotulo pelo relogio (invariante 10)."""
    inicio = max(de for de, _ in ESPERA_DO_BOT.values())
    fim = min(ate for _, ate in ESPERA_DO_BOT.values())
    assert inicio < fim
