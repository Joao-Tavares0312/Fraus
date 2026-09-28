"""Contrato operacional do pool Postgres usado no serverless."""

from contextlib import contextmanager

import pytest

from fraus.db import Banco


class PoolFalso:
    instancias = []

    def __init__(self, url, **opcoes):
        self.url = url
        self.opcoes = opcoes
        self.fechado = False
        self.__class__.instancias.append(self)

    @contextmanager
    def connection(self):
        class Conexao:
            def commit(self):
                pass

            def rollback(self):
                pass

        yield Conexao()

    def close(self):
        self.fechado = True


def test_pool_serverless_aceita_minimo_maximo_e_timeout(monkeypatch):
    monkeypatch.setenv("FRAUS_POSTGRES_MIN_CONEXOES", "0")
    monkeypatch.setenv("FRAUS_POSTGRES_MAX_CONEXOES", "2")
    monkeypatch.setenv("FRAUS_POSTGRES_TIMEOUT_S", "7.5")
    monkeypatch.setattr("psycopg_pool.ConnectionPool", PoolFalso)
    PoolFalso.instancias.clear()

    banco = Banco("postgresql://usuario:segredo@localhost/fraus")
    pool = banco._obter_pool()

    assert pool.opcoes["min_size"] == 0
    assert pool.opcoes["max_size"] == 2
    assert pool.opcoes["timeout"] == 7.5
    assert pool.opcoes["kwargs"]["prepare_threshold"] is None


@pytest.mark.parametrize(
    ("nome", "valor", "trecho"),
    [
        ("FRAUS_POSTGRES_MIN_CONEXOES", "-1", "entre 0"),
        ("FRAUS_POSTGRES_MAX_CONEXOES", "0", "entre 1"),
        ("FRAUS_POSTGRES_TIMEOUT_S", "zero", "numero"),
    ],
)
def test_configuracao_invalida_do_pool_falha_com_mensagem(monkeypatch, nome, valor, trecho):
    monkeypatch.setenv(nome, valor)
    banco = Banco("postgresql://localhost/fraus")
    with pytest.raises(RuntimeError, match=trecho):
        banco._obter_pool()


def test_minimo_nao_pode_superar_maximo(monkeypatch):
    monkeypatch.setenv("FRAUS_POSTGRES_MIN_CONEXOES", "3")
    monkeypatch.setenv("FRAUS_POSTGRES_MAX_CONEXOES", "2")
    banco = Banco("postgresql://localhost/fraus")
    with pytest.raises(RuntimeError, match="nao pode superar"):
        banco._obter_pool()


def test_aquisicao_registra_contagem_espera_e_falha(monkeypatch):
    monkeypatch.setattr("psycopg_pool.ConnectionPool", PoolFalso)
    PoolFalso.instancias.clear()
    instantes = iter((10.0, 10.025, 20.0, 20.010))
    monkeypatch.setattr("fraus.db.perf_counter", lambda: next(instantes))
    banco = Banco("postgresql://localhost/fraus")

    conexao = banco._conectar()
    conexao.__exit__(None, None, None)
    metricas = banco.metricas_do_pool()

    assert metricas["aquisicoes"] == 1
    assert metricas["falhas"] == 0
    assert metricas["espera_total_ms"] == pytest.approx(25.0)
    assert metricas["espera_ultima_ms"] == pytest.approx(25.0)
    assert metricas["espera_maxima_ms"] == pytest.approx(25.0)
