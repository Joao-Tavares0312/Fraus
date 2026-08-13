"""API do Dolos.

Score e categoria SAO SEMPRE derivados no servidor: campos vindos do corpo da
requisicao que se pareçam com veredito sao ignorados por construcao -- o modelo
de entrada so aceita `caminho`.

O objeto `app` de nivel de modulo (consumido por `uvicorn dolos.api.main:app`)
e construido com dependencias REAIS -- Banco em disco e Motor com
ClassificadorTexto/Fusor carregados do disco -- e deve falhar alto no import
se o modelo ou o fusor nao existirem (ModeloAusenteError e equivalente do
fusor propagam sem fallback: servir predicao sem modelo carregado e pior do
que estar fora do ar).

`app` e resolvido de forma preguicosa via `__getattr__` de modulo (PEP 562):
so e construido quando algo de fato acessa o atributo `app` (como o uvicorn
faz ao importar `dolos.api.main:app`). O import puro do modulo -- o que os
testes fazem ao importar `criar_app` -- nunca dispara essa construcao, porque
`app` nao existe como atributo normal do modulo.
"""

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from dolos.db import Banco
from dolos.fusor import Fusor, montar_features
from dolos.indicadores import (calcular_csat, calcular_nps, categoria_nps,
                               containment_rate, nota_0_10)
from dolos.ingest.csv_driver import carregar_csv
from dolos.sinais.texto import ClassificadorTexto

CAMINHO_MODELO_TEXTO = Path(os.environ.get("DOLOS_CAMINHO_MODELO_TEXTO", "modelos/bertimbau-satisfacao"))
CAMINHO_FUSOR = Path(os.environ.get("DOLOS_CAMINHO_FUSOR", "modelos/fusor.joblib"))
CAMINHO_BANCO = Path(os.environ.get("DOLOS_CAMINHO_BANCO", "dolos.db"))


class PedidoImportacao(BaseModel):
    caminho: str  # unico campo aceito: veredito nunca vem do cliente


class Motor:
    """Amarra classificador de texto e fusor num unico ponto de pontuacao."""

    def __init__(self, classificador: ClassificadorTexto, fusor: Fusor) -> None:
        self._classificador = classificador
        self._fusor = fusor

    def pontuar_conversa(self, conversa) -> float | None:
        if not conversa.tem_sinal_cliente:
            return None  # ausencia de dado nao e insatisfacao
        return self._fusor.pontuar(montar_features(conversa, self._classificador))


def criar_app(banco: Banco, motor) -> FastAPI:
    app = FastAPI(title="Dolos", version="0.1.0")

    @app.get("/saude")
    def saude() -> dict:
        return {"status": "ok"}

    @app.post("/conversas/importar")
    def importar(pedido: PedidoImportacao) -> dict:
        caminho = Path(pedido.caminho)
        if not caminho.is_file():
            raise HTTPException(status_code=400, detail=f"arquivo nao encontrado: {caminho}")

        resultado = carregar_csv(caminho)
        for conversa in resultado.conversas:
            score = motor.pontuar_conversa(conversa)
            categoria = categoria_nps(score) if score is not None else None
            banco.salvar(conversa, score, categoria)

        return {"importadas": len(resultado.conversas), "rejeitadas": len(resultado.rejeitadas)}

    @app.get("/conversas")
    def listar() -> list[dict]:
        return banco.listar()

    @app.get("/conversas/{conversa_id}")
    def detalhar(conversa_id: str) -> dict:
        achado = banco.buscar(conversa_id)
        if achado is None:
            raise HTTPException(status_code=404, detail="conversa nao encontrada")
        conversa, score, categoria = achado
        return {
            **conversa.model_dump(mode="json"),
            "score": score,
            "categoria": categoria,
            "nota": nota_0_10(score) if score is not None else None,
        }

    @app.get("/indicadores")
    def indicadores() -> dict:
        registros = banco.todas()
        conversas = [conversa for conversa, _ in registros]
        scores = [score for _, score in registros if score is not None]
        return {
            "nps": calcular_nps(scores),
            "csat": calcular_csat(scores),
            "containment_rate": containment_rate(conversas),
            "total_conversas": len(conversas),
            "sem_sinal": len(conversas) - len(scores),
        }

    return app


def criar_app_padrao() -> FastAPI:
    """Monta o app com dependencias reais. Falha alto se modelo/fusor faltarem."""
    banco = Banco(CAMINHO_BANCO)
    banco.migrar()
    classificador = ClassificadorTexto(CAMINHO_MODELO_TEXTO)  # propaga ModeloAusenteError
    fusor = Fusor.carregar(CAMINHO_FUSOR)  # propaga FileNotFoundError se o .joblib faltar
    motor = Motor(classificador, fusor)
    return criar_app(banco=banco, motor=motor)


def __getattr__(nome: str):
    """PEP 562: resolve `app` sob demanda, so quando algo acessa o atributo.

    Mantem o import puro do modulo barato (o que os testes fazem ao importar
    `criar_app`) e ainda assim expoe `app` para `uvicorn dolos.api.main:app`,
    que acessa o atributo de verdade -- disparando a construcao real e
    deixando ModeloAusenteError/erro do fusor propagarem.
    """
    if nome == "app":
        return criar_app_padrao()
    raise AttributeError(f"modulo {__name__!r} nao tem atributo {nome!r}")
