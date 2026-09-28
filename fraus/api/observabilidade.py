"""Tempos operacionais por requisicao, sem payloads nem credenciais.

O contexto acompanha a execucao sincrona das rotas FastAPI nas worker threads.
Banco e motor apenas somam duracoes; este middleware e o unico lugar que
publica ``Server-Timing`` e escreve uma linha JSON estruturada.
"""

from contextvars import ContextVar
import json
import logging
from time import perf_counter

from fastapi import FastAPI

_metricas: ContextVar[dict[str, float] | None] = ContextVar("metricas_fraus", default=None)
_logger = logging.getLogger("fraus.requisicao")


def somar_tempo(nome: str, duracao_ms: float) -> None:
    atual = _metricas.get()
    if atual is not None:
        atual[nome] = atual.get(nome, 0.0) + max(0.0, duracao_ms)


def medir(nome: str, operacao):
    inicio = perf_counter()
    try:
        return operacao()
    finally:
        somar_tempo(nome, (perf_counter() - inicio) * 1000)


class _Observabilidade:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        metricas: dict[str, float] = {}
        token = _metricas.set(metricas)
        inicio = perf_counter()
        status = 500

        async def send_medido(mensagem):
            nonlocal status
            if mensagem["type"] == "http.response.start":
                status = mensagem["status"]
                total = (perf_counter() - inicio) * 1000
                partes = [f'total;dur={total:.1f}']
                for nome in ("espera_pool", "consulta_db", "carga_modelo", "inferencia"):
                    if nome in metricas:
                        partes.append(f'{nome};dur={metricas[nome]:.1f}')
                cabecalhos = list(mensagem.get("headers") or [])
                cabecalhos.append((b"server-timing", ", ".join(partes).encode("ascii")))
                mensagem = {**mensagem, "headers": cabecalhos}
            await send(mensagem)

        try:
            await self.app(scope, receive, send_medido)
        finally:
            total = (perf_counter() - inicio) * 1000
            evento = {
                "evento": "requisicao_http",
                "metodo": scope.get("method"),
                # A rota, sem query string: filtros podem conter dado operacional.
                "caminho": scope.get("path"),
                "status": status,
                "duracao_ms": round(total, 1),
                "consulta_db_ms": round(metricas.get("consulta_db", 0.0), 1),
                "espera_pool_ms": round(metricas.get("espera_pool", 0.0), 1),
                "carga_modelo_ms": round(metricas.get("carga_modelo", 0.0), 1),
                "inferencia_ms": round(metricas.get("inferencia", 0.0), 1),
                "cold_start": metricas.get("carga_modelo", 0.0) > 0,
            }
            _logger.info(json.dumps(evento, ensure_ascii=True, separators=(",", ":")))
            _metricas.reset(token)


def registrar_observabilidade(app: FastAPI) -> None:
    app.add_middleware(_Observabilidade)
